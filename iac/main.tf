# main.tf - JAO Data Engine Infrastructure (Minimal)
#
# This infrastructure supports a batch data processing engine that runs weekly.
# It does NOT include: API Gateway, Frontend, Celery/Redis, always-on ECS services.
#
# Components:
# - VPC with private/public subnets
# - Aurora PostgreSQL with pgvector
# - Single ECS cluster with two task definitions:
#   - Data Engine (Python 3.12) - main pipeline
#   - Skills Worker (Python 3.10) - skills extraction
# - S3 buckets for initialization and data science
# - Optional: SageMaker notebook, Bastion host

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 4.0"
    }
  }
  required_version = ">= 1.0"

  # Remote state: S3 for storage + DynamoDB for locking. The bucket and table must be
  # created before `terraform init -migrate-state` (they can't be bootstrapped by the
  # config that depends on them) - see the one-time CLI commands in the deploy notes.
  backend "s3" {
    bucket         = "jao-co-tfstate"
    key            = "jao/dev/terraform.tfstate"
    region         = "eu-west-2"
    dynamodb_table = "jao-terraform-locks"
    encrypt        = true
  }
}

provider "aws" {
  region = var.aws_region
}

locals {
  common_tags = {
    Project     = var.app_name
    Environment = var.environment
    ManagedBy   = "terraform"
  }

  # Environment-specific configurations
  env_config = {
    prod = {
      force_destroy_buckets  = false
      single_nat_gateway     = false
      s3_lifecycle_days      = 365
      log_retention_days     = 90
      db_min_capacity        = 1.0
      db_max_capacity        = 8.0
      db_backup_retention    = 30
      db_skip_final_snapshot = false
      db_deletion_protection = true
      monitoring_interval    = 60
    }
    dev = {
      force_destroy_buckets  = true
      single_nat_gateway     = true
      s3_lifecycle_days      = 90
      log_retention_days     = 30
      db_min_capacity        = 0.5
      db_max_capacity        = 2.0
      db_backup_retention    = 7
      db_skip_final_snapshot = true
      db_deletion_protection = false
      monitoring_interval    = 30
    }
  }

  # Current environment config
  current_env = local.env_config[var.environment == "prod" ? "prod" : "dev"]

  # ECR image URLs (same repo, different tags)
  data_engine_ecr_url   = "${aws_ecr_repository.main.repository_url}:${var.data_engine_image_tag}"
  skills_worker_ecr_url = "${aws_ecr_repository.main.repository_url}:${var.skills_worker_image_tag}"
}

# =============================================================================
# S3 BUCKETS
# =============================================================================

# S3 bucket for initialization scripts
module "initialization_bucket" {
  source      = "./modules/s3_bucket"
  bucket_name = coalesce(var.initialization_bucket, "${var.app_name}-${var.environment}-initialization")

  enable_versioning = true
  enable_encryption = true
  force_destroy     = local.current_env.force_destroy_buckets

  lifecycle_rules = [
    {
      id     = "expire-old-scripts"
      status = "Enabled"
      expiration = {
        days = local.current_env.s3_lifecycle_days
      }
    }
  ]

  tags = local.common_tags
}

# =============================================================================
# ECR REPOSITORY (Single repo, multiple image tags)
# =============================================================================

# ECR Repository for all Docker images
# - data-engine tag: Python 3.12 main pipeline
# - skills-worker tag: Python 3.10 skills extraction
resource "aws_ecr_repository" "main" {
  name                 = "${var.app_name}-${var.environment}"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = local.common_tags
}

# Keep the existing repo (and its images) from the old address
moved {
  from = aws_ecr_repository.app
  to   = aws_ecr_repository.main
}

resource "aws_ecr_lifecycle_policy" "main" {
  repository = aws_ecr_repository.main.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep last 10 images per tag prefix"
        selection = {
          tagStatus     = "tagged"
          tagPrefixList = ["data-engine", "skills-worker"]
          countType     = "imageCountMoreThan"
          countNumber   = 10
        }
        action = {
          type = "expire"
        }
      },
      {
        rulePriority = 2
        description  = "Keep last 5 untagged images"
        selection = {
          tagStatus   = "untagged"
          countType   = "imageCountMoreThan"
          countNumber = 5
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}

# =============================================================================
# VPC
# =============================================================================

module "vpc" {
  source = "./modules/vpc"

  name_prefix          = var.app_name
  environment          = var.environment
  vpc_cidr             = var.vpc_cidr
  azs                  = var.availability_zones
  private_subnet_cidrs = var.private_subnet_cidrs
  public_subnet_cidrs  = var.public_subnet_cidrs

  enable_nat_gateway = true
  single_nat_gateway = local.current_env.single_nat_gateway

  # VPC Endpoints configuration
  create_vpc_endpoints         = var.create_vpc_endpoints
  create_ecr_dkr_endpoint      = var.create_ecr_dkr_endpoint
  create_ecr_api_endpoint      = var.create_ecr_api_endpoint
  create_s3_endpoint           = var.create_s3_endpoint
  create_logs_endpoint         = var.create_logs_endpoint
  existing_ecr_dkr_endpoint_id = var.existing_ecr_dkr_endpoint_id
  existing_ecr_api_endpoint_id = var.existing_ecr_api_endpoint_id
  existing_s3_endpoint_id      = var.existing_s3_endpoint_id
  existing_logs_endpoint_id    = var.existing_logs_endpoint_id

  tags = local.common_tags
}

# =============================================================================
# AURORA POSTGRESQL DATABASE
# =============================================================================

# Database Module - Aurora PostgreSQL with pgvector
module "vectordb" {
  source = "./modules/aurora_pgvector"

  app_name    = var.app_name
  environment = var.environment

  # Network configuration
  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnet_ids

  allowed_security_groups = [aws_security_group.db_access.id]
  allowed_cidr_blocks     = var.allowed_cidr_blocks
  # Enable data science read replica if SageMaker is enabled
  create_data_science_replica = var.enable_sagemaker_environment
  data_science_instance_class = var.environment == "prod" ? "db.r6g.xlarge" : "db.serverless"

  # Database configuration
  database_name   = "${replace(var.app_name, "-", "")}${var.environment}db"
  master_username = "dbadmin"
  master_password = var.db_password
  engine_version  = "15.17" # match the live cluster's auto-upgraded minor version to avoid a spurious downgrade/ModifyDBCluster

  use_serverless = false
  instance_count = 1
  min_capacity   = local.current_env.db_min_capacity
  max_capacity   = local.current_env.db_max_capacity

  # Development settings
  apply_immediately       = true
  skip_final_snapshot     = local.current_env.db_skip_final_snapshot
  deletion_protection     = local.current_env.db_deletion_protection
  backup_retention_period = local.current_env.db_backup_retention

  performance_insights_enabled = var.performance_insights_enabled != null ? var.performance_insights_enabled : true
  enhanced_monitoring_interval = var.enable_enhanced_monitoring ? local.current_env.monitoring_interval : 0

  init_script        = "${path.module}/sql/init_pgvector.sql"
  init_script_bucket = module.initialization_bucket.bucket_id
  prevent_destroy    = false

  additional_parameters = [
    {
      name  = "client_encoding"
      value = "UTF8"
    },
    {
      name  = "max_connections"
      value = "200"
    },
    {
      name  = "shared_buffers"
      value = "262144"
    },
    {
      name  = "pgaudit.log"
      value = "none"
    }
  ]

  tags = local.common_tags
}

# Security group for database access from ECS tasks
resource "aws_security_group" "db_access" {
  name        = "${var.app_name}-${var.environment}-db-access"
  description = "Security group for ECS tasks to access database"
  vpc_id      = module.vpc.vpc_id

  # Allow outbound connections to Aurora database
  egress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [module.vectordb.security_group_id]
    description     = "PostgreSQL database access to Aurora"
  }

  # DNS resolution
  egress {
    from_port   = 53
    to_port     = 53
    protocol    = "udp"
    cidr_blocks = [module.vpc.vpc_cidr_block]
    description = "DNS resolution"
  }

  # HTTPS for AWS services (RDS monitoring, CloudWatch, etc.)
  egress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTPS for AWS services"
  }

  tags = local.common_tags

  depends_on = [module.vpc]
}

# Security group for Oleeo MSSQL access
resource "aws_security_group" "oleeo" {
  name_prefix = "${var.app_name}-${var.environment}-oleeo-"
  vpc_id      = module.vpc.vpc_id

  egress {
    from_port   = 1433
    to_port     = 1433
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow outbound MSSQL connection to Oleeo database"
  }

  tags = merge(local.common_tags, {
    Name = "${var.app_name}-${var.environment}-oleeo-sg"
  })
}

# =============================================================================
# ECS SCHEDULED TASKS (Single Cluster, Two Task Definitions)
# =============================================================================

module "scheduled_tasks" {
  source = "./modules/scheduled_task"

  name_prefix = var.app_name
  environment = var.environment

  vpc_id             = module.vpc.vpc_id
  private_subnet_ids = module.vpc.private_subnet_ids

  security_group_ids = [
    aws_security_group.db_access.id,
    aws_security_group.oleeo.id,
    "sg-0b888695cb98d3884"
  ]

  # Data Engine Task (Python 3.12)
  data_engine_image_url           = local.data_engine_ecr_url
  data_engine_cpu                 = var.data_engine_cpu
  data_engine_memory              = var.data_engine_memory
  data_engine_command             = ["python", "manage.py", "run_weekly_pipeline"]
  data_engine_schedule_expression = var.data_engine_schedule_expression

  # Data engine environment variables
  environment_variables = {
    # Database environment variables
    DB_HOST     = module.vectordb.cluster_endpoint
    DB_PORT     = "5432"
    DB_NAME     = module.vectordb.database_name
    DB_USER     = module.vectordb.master_username
    DB_PASSWORD = var.db_password

    # Django environment variables
    ENV                    = var.environment
    DJANGO_SETTINGS_MODULE = "jao_backend.settings.${var.environment}"
    JAO_BACKEND_SECRET_KEY = var.django_secret_key
    DEPLOYMENT_TYPE        = "aws"

    # Database URL for Django
    JAO_BACKEND_DATABASE_URL       = "postgresql://${module.vectordb.master_username}:${var.db_password}@${module.vectordb.cluster_endpoint}:5432/${module.vectordb.database_name}"
    JAO_BACKEND_OLEEO_DATABASE_URL = var.oleeo_url
    JAO_BACKEND_ENABLE_OLEEO       = "1"

    # Data processing settings
    JAO_BACKEND_INGEST_DEFAULT_BATCH_SIZE = tostring(var.ingest_batch_size)
    JAO_BACKEND_VACANCY_EMBED_LIMIT       = tostring(var.vacancy_embed_limit)
    JAO_EMBEDDER_SUMMARY_RESPONSIBILITIES = var.embedder_model
  }

  # Skills Worker Task (Python 3.10)
  skills_worker_image_url           = local.skills_worker_ecr_url
  skills_worker_cpu                 = var.skills_worker_cpu
  skills_worker_memory              = var.skills_worker_memory
  skills_worker_command             = ["python", "skills_extraction.py"]
  enable_skills_worker_schedule     = var.enable_skills_worker_schedule
  skills_worker_schedule_expression = var.skills_worker_schedule_expression

  # Skills worker environment variables
  skills_worker_environment_variables = {
    # Database connection for storing results
    DB_HOST     = module.vectordb.cluster_endpoint
    DB_PORT     = "5432"
    DB_NAME     = module.vectordb.database_name
    DB_USER     = module.vectordb.master_username
    DB_PASSWORD = var.db_password
  }

  schedule_enabled       = var.schedule_enabled
  logs_retention_in_days = local.current_env.log_retention_days

  tags = local.common_tags
}

# =============================================================================
# BASTION HOST (Optional)
# =============================================================================

module "bastion" {
  count  = var.enable_bastion_host ? 1 : 0
  source = "./modules/bastion"

  name_prefix     = var.app_name
  vpc_cidr_blocks = [module.vpc.vpc_cidr_block]

  vpc_id              = module.vpc.vpc_id
  public_subnet_id    = module.vpc.public_subnet_ids[0]
  allowed_cidr_blocks = var.allowed_cidr_blocks
  ssh_public_key      = var.ssh_public_key
  aurora_endpoint     = module.vectordb.cluster_endpoint

  tags = local.common_tags
}

# Allow bastion to connect to Aurora
resource "aws_security_group_rule" "bastion_to_aurora" {
  count = var.enable_bastion_host ? 1 : 0

  type                     = "ingress"
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  source_security_group_id = module.bastion[0].bastion_security_group_id
  security_group_id        = module.vectordb.security_group_id
  description              = "Allow bastion host to connect to Aurora PostgreSQL"
}

# =============================================================================
# SAGEMAKER (Optional)
# =============================================================================

# S3 Bucket for Data Science Work
module "data_science_bucket" {
  count  = var.enable_sagemaker_environment ? 1 : 0
  source = "./modules/s3_bucket"

  bucket_name       = "${var.app_name}-${var.environment}-data-science"
  enable_versioning = true
  enable_encryption = true
  force_destroy     = local.current_env.force_destroy_buckets

  lifecycle_rules = [
    {
      id     = "expire-old-data"
      status = "Enabled"
      expiration = {
        days = 90
      }
    }
  ]

  tags = merge(local.common_tags, {
    Purpose = "data-science"
  })
}

# SageMaker Notebook Instance
module "sagemaker" {
  count  = var.enable_sagemaker_environment ? 1 : 0
  source = "./modules/sagemaker"

  app_name    = var.app_name
  environment = var.environment

  # Network Configuration
  vpc_id                 = module.vpc.vpc_id
  vpc_cidr_block         = var.vpc_cidr
  subnet_id              = module.vpc.private_subnet_ids[0]
  direct_internet_access = var.environment == "dev" ? "Enabled" : "Disabled"

  # Aurora Database Connection
  aurora_endpoint = coalesce(
    module.vectordb.data_science_replica_endpoint,
    module.vectordb.reader_endpoint
  )
  aurora_port       = module.vectordb.port
  database_name     = module.vectordb.database_name
  database_username = var.sagemaker_db_username
  database_password = var.sagemaker_db_password

  # S3 Configuration
  data_bucket_name = module.data_science_bucket[0].bucket_id
  data_bucket_arn  = module.data_science_bucket[0].bucket_arn

  # Notebook Configuration
  notebook_instance_type  = var.environment == "prod" ? "ml.t3.xlarge" : "ml.t3.medium"
  volume_size             = var.environment == "prod" ? 50 : 20
  auto_shutdown_idle_time = var.environment == "prod" ? 60 : 120

  # Monitoring
  enable_monitoring  = true
  log_retention_days = local.current_env.log_retention_days

  tags = merge(local.common_tags, {
    Team = "data-science"
  })

  depends_on = [module.vectordb]
}

resource "aws_security_group_rule" "sagemaker_to_aurora" {
  count = var.enable_sagemaker_environment ? 1 : 0

  type                     = "ingress"
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  source_security_group_id = module.sagemaker[0].security_group_id
  security_group_id        = module.vectordb.security_group_id
  description              = "Allow SageMaker notebook to connect to Aurora PostgreSQL"
}
