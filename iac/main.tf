# main.tf
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 4.0"
    }
  }
  required_version = ">= 1.0"
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
      api_rate_limit         = 200
      api_burst_limit        = 300
      max_requests_per_min   = "1000"
      enable_xray_tracing    = true
      django_debug           = "False"
      session_cookie_secure  = "true"
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
      api_rate_limit         = 500
      api_burst_limit        = 1000
      max_requests_per_min   = "2000"
      enable_xray_tracing    = false
      django_debug           = "True"
      session_cookie_secure  = "false"
      monitoring_interval    = 30
    }
  }

  # Current environment config
  current_env = local.env_config[var.environment == "prod" ? "prod" : "dev"]

  # ECR repository URLs
  backend_ecr_url  = "${aws_ecr_repository.app.repository_url}:${var.image_tag}"
  frontend_ecr_url = "${aws_ecr_repository.frontend.repository_url}:${var.image_tag}"
}

# Create S3 bucket for initialization scripts
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

# ECR Repository for Backend API Docker image
resource "aws_ecr_repository" "app" {
  name                 = "${var.app_name}-${var.environment}"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = local.common_tags
}

# ECR Repository for Frontend Docker image
resource "aws_ecr_repository" "frontend" {
  name                 = "${var.app_name}-frontend-${var.environment}"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = local.common_tags
}


# VPC configuration
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

# ECS Cluster and Service
module "ecs" {
  source = "./modules/ecs"

  name_prefix        = var.app_name
  environment        = var.environment
  ecr_repository_url = local.backend_ecr_url
  container_port     = var.container_port
  vpc_id             = module.vpc.vpc_id
  private_subnet_ids = module.vpc.private_subnet_ids
  public_subnet_ids  = module.vpc.public_subnet_ids
  cpu                = var.task_cpu
  memory             = var.task_memory
  desired_count      = var.desired_count
  container_name     = var.app_name
  additional_security_group_ids = [
    aws_security_group.redis_client.id,
    aws_security_group.db_access.id,
    aws_security_group.oleeo.id
  ]

  # Environment variables for the API service
  environment_variables = merge(var.environment_variables, {
    # Database environment variables
    DB_HOST     = module.vectordb.cluster_endpoint
    DB_PORT     = "5432"
    DB_NAME     = module.vectordb.database_name
    DB_USER     = module.vectordb.master_username
    DB_PASSWORD = "secrettpassword"

    # Django environment variables
    ENV                    = "dev" # Required for settings module selection
    DJANGO_SETTINGS_MODULE = "jao_backend.settings.dev"
    JAO_BACKEND_SECRET_KEY = "8e5c0e0f457aeec89329be09" # Will be overridden in production
    DJANGO_DEBUG           = local.current_env.django_debug
    API_STAGE_NAME         = var.environment
    DJANGO_ALLOWED_HOSTS   = "*"
    DEPLOYMENT_TYPE        = "aws"

    # Database URL for Django (required by jao_backend settings)
    JAO_BACKEND_DATABASE_URL       = "postgresql://${module.vectordb.master_username}:secrettpassword@${module.vectordb.cluster_endpoint}:5432/${module.vectordb.database_name}"
    JAO_BACKEND_OLEEO_DATABASE_URL = var.oleeo_url
    JAO_BACKEND_ENABLE_OLEEO       = 1
    JAO_BACKEND_SUPERUSER_USERNAME = var.jao_backend_superuser_username
    JAO_BACKEND_SUPERUSER_PASSWORD = var.jao_backend_superuser_password
    JAO_BACKEND_SUPERUSER_EMAIL    = var.jao_backend_superuser_email
    # Celery configuration
    CELERY_BROKER_URL     = module.celery_redis.celery_broker_url
    CELERY_RESULT_BACKEND = module.celery_redis.celery_result_backend

    # LiteLLM integration
    JAO_BACKEND_LITELLM_API_BASE          = "http://127.0.0.1:11434/api/embed" # Default for dev environment
    JAO_BACKEND_LITELLM_CUSTOM_PROVIDER   = "ollama"                           # Default for dev environment
    JAO_EMBEDDER_SUMMARY_RESPONSIBILITIES = "ollama/nomic-embed-text:latest"

    # API rate limiting and monitoring config
    ENABLE_RATE_LIMITING = "true"
    MAX_REQUESTS_PER_MIN = local.current_env.max_requests_per_min
    ENABLE_API_METRICS   = "true"

    # Django admin URL configuration - use standard admin URL
    DJANGO_ADMIN_URL = "django-admin/"
  })

  health_check_path        = "/health"
  internal_lb              = true
  admin_lb_internet_facing = true
  logs_retention_in_days   = local.current_env.log_retention_days

  # Enable enhanced monitoring and tracing for the API backend
  enable_enhanced_monitoring = true
  enable_xray_tracing        = local.current_env.enable_xray_tracing
  enable_circuit_breaker     = true

  # Enable Celery services
  enable_celery_services = var.enable_celery_services

  # Admin IP whitelisting
  admin_allowed_cidrs = var.admin_allowed_cidrs

  tags = local.common_tags
}

# Frontend Module
module "frontend" {
  source = "./modules/frontend"

  name_prefix        = var.app_name
  environment        = var.environment
  ecr_repository_url = local.frontend_ecr_url
  container_port     = 8000
  vpc_id             = module.vpc.vpc_id
  private_subnet_ids = module.vpc.private_subnet_ids
  public_subnet_ids  = module.vpc.public_subnet_ids
  cpu                = var.task_cpu
  memory             = var.task_memory
  desired_count      = var.desired_count

  # Environment variables for the frontend service
  environment_variables = {
    DJANGO_DEBUG             = local.current_env.django_debug
    DJANGO_SETTINGS_MODULE   = "jao_web.settings.dev"
    PORT                     = "8000"
    JAO_BACKEND_URL          = module.api_gateway.api_gateway_url
    JAO_BACKEND_TIMEOUT      = "15"
    JAO_BACKEND_ENABLE_HTTP2 = "true"
    SESSION_COOKIE_SECURE    = local.current_env.session_cookie_secure
    ENV                      = var.environment
    DJANGO_ALLOWED_HOSTS     = "*"
  }
  health_check_path      = "/health"
  internal_lb            = false
  logs_retention_in_days = local.current_env.log_retention_days

  tags = local.common_tags
}

# API Gateway with enhanced third-party API features
module "api_gateway" {
  source = "./modules/api_gateway"

  name_prefix                = var.app_name
  environment                = var.environment
  vpc_id                     = module.vpc.vpc_id
  load_balancer_arn          = module.ecs.load_balancer_arn
  load_balancer_dns_name     = module.ecs.load_balancer_dns_name
  stage_name                 = var.environment
  logs_retention_in_days     = local.current_env.log_retention_days
  enable_api_keys            = true
  enable_detailed_metrics    = true
  api_throttling_rate_limit  = local.current_env.api_rate_limit
  api_throttling_burst_limit = local.current_env.api_burst_limit

  # API keys for third-party consumers
  api_keys = [
    {
      name        = "internal-frontend"
      description = "API key for internal frontend application"
      enabled     = true
    },
    {
      name        = "partner-api-consumer"
      description = "API key for partner applications"
      enabled     = true
    },
    {
      name        = "public-api-consumer"
      description = "API key for public API consumers"
      enabled     = true
    }
  ]
  routes = [
    {
      route_key = "ANY /{proxy+}"
      methods   = ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]
      path      = "/{proxy+}"
    },
    {
      route_key = "GET /health"
      methods   = ["GET"]
      path      = "/health"
    }
  ]

  tags = local.common_tags
}


# Database Module - Aurora PostgreSQL with pgvector
module "vectordb" {
  source = "./modules/aurora_pgvector"

  app_name    = var.app_name
  environment = var.environment

  # Network configuration
  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnet_ids

  allowed_security_groups = [aws_security_group.db_access.id]

  # Enable data science read replica if SageMaker is enabled
  create_data_science_replica = var.enable_sagemaker_environment
  data_science_instance_class = var.environment == "prod" ? "db.r6g.xlarge" : "db.serverless"

  # Database configuration
  database_name   = "${replace(var.app_name, "-", "")}${var.environment}db"
  master_username = "dbadmin"
  # master_password = var.skip_secret_creation ? "TemporaryPassword123!" : null
  engine_version = "15.10"

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

# Security group rule to allow SageMaker to connect to Aurora
# Created here to avoid circular dependency
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

module "celery_redis" {
  source = "./modules/elasticache"

  replication_group_id = "jao-celery-cache"
  node_type            = "cache.t3.small"
  subnet_group_name    = aws_elasticache_subnet_group.main.name
  security_group_ids   = [aws_security_group.redis_client.id]

  tags = {
    Environment = "production"
    Application = "celery"
  }
}

resource "aws_security_group" "redis_client" {
  name_prefix = "${var.app_name}-${var.environment}-redis-client-"
  vpc_id      = module.vpc.vpc_id
  description = "Security group for services that need Redis access"

  egress {
    from_port       = 6380
    to_port         = 6380
    protocol        = "tcp"
    security_groups = [aws_security_group.redis.id]
    description     = "Allow Redis connections"
  }

  tags = merge(local.common_tags, {
    Name = "${var.app_name}-${var.environment}-redis-client-sg"
  })
}


# Security group for Redis
resource "aws_security_group" "redis" {
  name_prefix = "redis-celery-"
  vpc_id      = module.vpc.vpc_id

  ingress {
    from_port   = 6380
    to_port     = 6380
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
  }

  tags = {
    Name = "redis-celery-sg"
  }
}

resource "aws_security_group" "celery_workers" {
  name_prefix = "celery-workers-"
  vpc_id      = module.vpc.vpc_id

  egress {
    from_port       = 6380
    to_port         = 6380
    protocol        = "tcp"
    security_groups = [aws_security_group.redis.id]
    description     = "Allow outbound Redis connections"
  }

  tags = {
    Name = "celery-workers-sg"
  }
}

# Subnet group
resource "aws_elasticache_subnet_group" "main" {
  name       = "celery-redis-subnet-group"
  subnet_ids = module.vpc.private_subnet_ids
}

resource "aws_security_group" "oleeo" {

  name_prefix = "oleeo-"
  vpc_id      = module.vpc.vpc_id

  egress {
    from_port   = 1433
    to_port     = 1433
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow outbound MSSQL connection to database VPC"
  }

  tags = {
    Name = "oleeo-sg"
  }
}

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
