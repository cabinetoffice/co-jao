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

# Create S3 bucket for initialization scripts
module "initialization_bucket" {
  source      = "./modules/s3_bucket"
  bucket_name = var.initialization_bucket != "" ? var.initialization_bucket : "${var.app_name}-${var.environment}-initialization"

  enable_versioning = true
  enable_encryption = true
  force_destroy     = var.environment != "prod"

  # Skip creation if the bucket already exists and is imported
  create_bucket = !var.skip_s3_bucket_creation

  lifecycle_rules = [
    {
      id     = "expire-old-scripts"
      status = "Enabled"
      expiration = {
        days = var.environment == "prod" ? 365 : 90
      }
    }
  ]

  tags = local.common_tags
}

# ECR Repository for Backend API Docker image
resource "aws_ecr_repository" "app" {
  count                = var.skip_ecr_creation ? 0 : 1
  name                 = "${var.app_name}-${var.environment}"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = local.common_tags
}

# This import block is only needed when the repository already exists
# and you're importing it into Terraform state for the first time
# import {
#   to = aws_ecr_repository.app
#   id = "${var.app_name}-${var.environment}"
# }

# ECR Repository for Frontend Docker image
resource "aws_ecr_repository" "frontend" {
  count                = var.skip_ecr_creation ? 0 : 1
  name                 = "${var.app_name}-frontend-${var.environment}"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = local.common_tags
}

# This import block is only needed when the repository already exists
# and you're importing it into Terraform state for the first time
# import {
#   to = aws_ecr_repository.frontend
#   id = "${var.app_name}-frontend-${var.environment}"
# }

# Define common tags for all resources
locals {
  common_tags = {
    Project     = var.app_name
    Environment = var.environment
    ManagedBy   = "terraform"
  }
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
  single_nat_gateway = var.environment == "dev" ? true : false

  # Skip VPC creation if it already exists
  skip_vpc_creation = var.skip_vpc_creation
  existing_vpc_id   = var.existing_vpc_id

  tags = local.common_tags
}

# ECS Cluster and Service
module "ecs" {
  source = "./modules/ecs"

  name_prefix        = var.app_name
  environment        = var.environment
  ecr_repository_url = var.skip_ecr_creation ? "${var.aws_account_id}.dkr.ecr.${var.aws_region}.amazonaws.com/${var.app_name}-${var.environment}" : aws_ecr_repository.app[0].repository_url
  container_port     = var.container_port
  vpc_id             = module.vpc.vpc_id
  private_subnet_ids = module.vpc.private_subnet_ids
  public_subnet_ids  = module.vpc.public_subnet_ids
  cpu                = var.task_cpu
  memory             = var.task_memory
  desired_count      = var.desired_count
  container_name     = var.app_name

  # Skip resource creation if resources already exist
  skip_cloudwatch_creation         = var.skip_cloudwatch_creation
  skip_iam_role_creation           = var.skip_iam_role_creation
  existing_task_execution_role_arn = var.existing_task_execution_role_arn

  # Use existing log group if specified
  existing_log_group_name = var.existing_backend_log_group

  # Environment variables for the API service
  environment_variables = merge(var.environment_variables, {
    # Database environment variables
    DB_HOST     = module.vectordb.cluster_endpoint
    DB_PORT     = "5432"
    DB_NAME     = module.vectordb.database_name
    DB_USER     = module.vectordb.master_username
    DB_PASSWORD = "dummy-placeholder" # Will be overridden by secrets manager

    # Django environment variables
    ENV                    = "dev" # Required for settings module selection
    DJANGO_SETTINGS_MODULE = "jao_backend.settings.dev"
    DJANGO_SECRET_KEY      = "dummy-placeholder-secret-key" # Will be overridden in production
    DJANGO_DEBUG           = var.environment == "prod" ? "False" : "True"
    API_STAGE_NAME         = var.environment
    DJANGO_ALLOWED_HOSTS   = "*"

    # Database URL for Django (required by jao_backend settings)
    JAO_BACKEND_DATABASE_URL       = "postgresql://${module.vectordb.master_username}:dummy-placeholder@${module.vectordb.cluster_endpoint}:5432/${module.vectordb.database_name}"
    DATABASE_URL                   = "postgresql://${module.vectordb.master_username}:dummy-placeholder@${module.vectordb.cluster_endpoint}:5432/${module.vectordb.database_name}" # Will be built from DB_* vars in entrypoint
    JAO_BACKEND_OLEEO_DATABASE_URL = "mssqlms://user.namey:password@co-grid-database.eu-west-2:1433/DART_Dev"
    # Celery configuration
    CELERY_BROKER_URL     = "redis://localhost:6379/0" # Update this with your actual Redis endpoint
    CELERY_RESULT_BACKEND = "redis://localhost:6379/0" # Update this with your actual Redis endpoint

    # LiteLLM integration
    JAO_BACKEND_LITELLM_API_BASE          = "http://127.0.0.1:11434/api/embed" # Default for dev environment
    JAO_BACKEND_LITELLM_CUSTOM_PROVIDER   = "ollama"                           # Default for dev environment
    JAO_EMBEDDER_SUMMARY_RESPONSIBILITIES = "ollama/nomic-embed-text:latest"

    # API rate limiting and monitoring config
    ENABLE_RATE_LIMITING = "true"
    MAX_REQUESTS_PER_MIN = var.environment == "prod" ? "1000" : "2000"
    ENABLE_API_METRICS   = "true"
  })
  health_check_path      = "/health"
  internal_lb            = var.environment != "prod"
  logs_retention_in_days = var.environment == "prod" ? 90 : 30

  # Enable enhanced monitoring and tracing for the API backend
  enable_enhanced_monitoring = true
  enable_xray_tracing        = var.environment == "prod" ? true : false
  enable_circuit_breaker     = true

  tags = local.common_tags
}

# API Gateway with enhanced third-party API features
module "api_gateway" {
  source = "./modules/api_gateway"

  name_prefix            = var.app_name
  environment            = var.environment
  vpc_id                 = module.vpc.vpc_id
  vpc_link_subnets       = module.vpc.private_subnet_ids
  load_balancer_arn      = module.ecs.nlb_arn
  integration_uri        = module.ecs.lb_listener_arn
  load_balancer_dns_name = module.ecs.load_balancer_dns_name
  stage_name             = var.environment
  logs_retention_in_days = var.environment == "prod" ? 90 : 30

  # CloudWatch logs are always created by this module

  # Enhanced API features for third-party consumers
  enable_api_keys            = true
  enable_detailed_metrics    = true
  api_throttling_rate_limit  = var.environment == "prod" ? 200 : 500
  api_throttling_burst_limit = var.environment == "prod" ? 300 : 1000

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

  # Usage plans with different throttling settings
  # usage_plans = [
  #   {
  #     name        = "frontend-plan"
  #     description = "Usage plan for internal frontend"
  #     quota = {
  #       limit  = 1000000
  #       period = "MONTH"
  #     }
  #     throttle = {
  #       rate_limit  = 100
  #       burst_limit = 200
  #     }
  #     api_key_names = ["internal-frontend"]
  #   },
  #   {
  #     name        = "partner-plan"
  #     description = "Usage plan for partner API consumers"
  #     quota = {
  #       limit  = 500000
  #       period = "MONTH"
  #     }
  #     throttle = {
  #       rate_limit  = 50
  #       burst_limit = 50
  #     }
  #     api_key_names = ["partner-api-consumer"]
  #   }
  # ]

  # Route-specific throttling for critical endpoints
  # route_specific_throttling = {
  #   "GET /api/todos" = {
  #     rate_limit  = 30
  #     burst_limit = 60
  #   },
  #   "POST /api/todos" = {
  #     rate_limit  = 15
  #     burst_limit = 30
  #   }s
  # }

  # Define API routes
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

# Security group for database access
resource "aws_security_group" "db_access" {
  name        = "${var.app_name}-${var.environment}-db-access"
  description = "Security group for database access"
  vpc_id      = module.vpc.vpc_id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = local.common_tags

  depends_on = [module.vpc]
}

# Database Module - Aurora PostgreSQL with pgvector
module "vectordb" {
  source = "./modules/aurora_pgvector"

  app_name    = var.app_name
  environment = var.environment

  # Network configuration
  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnet_ids

  # Allow access from dedicated security group (we'll add ECS SG to this later)
  allowed_security_groups = [aws_security_group.db_access.id]

  # Database configuration
  database_name   = "${replace(var.app_name, "-", "")}${var.environment}db"
  master_username = "dbadmin"
  # master_password = var.skip_secret_creation ? "TemporaryPassword123!" : null

  # Use PostgreSQL 15.4
  engine_version = "15.10"

  # Serverless v2 configuration (provisioned with auto-scaling)
  use_serverless = false
  instance_count = 1
  # Enhanced capacity for API workloads with high throughput
  min_capacity = var.environment == "prod" ? 1.0 : 0.5 # Higher baseline for production
  max_capacity = var.environment == "prod" ? 8.0 : 2.0 # Higher ceiling for production

  # Development settings
  apply_immediately       = true
  skip_final_snapshot     = var.environment != "prod"
  deletion_protection     = var.environment == "prod"
  backup_retention_period = var.environment == "prod" ? 30 : 7 # Increased retention for production

  # Enhanced Monitoring for API database
  performance_insights_enabled = var.performance_insights_enabled != null ? var.performance_insights_enabled : true
  enhanced_monitoring_interval = var.enable_enhanced_monitoring ? (var.environment == "prod" ? 60 : 30) : 0 # Add basic monitoring even in dev

  # Initialize the database with the Django todo list schema
  init_script        = "${path.module}/sql/init_pgvector.sql"
  init_script_bucket = module.initialization_bucket.bucket_id
  prevent_destroy    = false


  # Additional parameters needed for Django compatibility and API optimization
  additional_parameters = [
    {
      name  = "client_encoding"
      value = "UTF8"
    },
    {
      name  = "max_connections"
      value = "200" # Increased for API traffic
    },
    {
      name  = "shared_buffers"
      value = "262144" # 256MB in kilobytes, optimized for API workloads
    },
    {
      name  = "pgaudit.log"
      value = "none" # Disable audit logging to avoid rds.* parameter conflicts
    }
  ]

  tags = local.common_tags
}

# Frontend Module
module "frontend" {
  source = "./modules/frontend"

  name_prefix        = var.app_name
  environment        = var.environment
  ecr_repository_url = var.skip_ecr_creation ? "${var.aws_account_id}.dkr.ecr.${var.aws_region}.amazonaws.com/${var.app_name}-frontend-${var.environment}" : aws_ecr_repository.frontend[0].repository_url
  container_port     = 8000
  vpc_id             = module.vpc.vpc_id
  private_subnet_ids = module.vpc.private_subnet_ids
  public_subnet_ids  = module.vpc.public_subnet_ids
  cpu                = var.task_cpu
  memory             = var.task_memory
  desired_count      = var.desired_count

  # Skip resource creation if resources already exist
  skip_cloudwatch_creation    = var.skip_cloudwatch_creation
  skip_iam_role_creation      = var.skip_iam_role_creation
  existing_execution_role_arn = var.existing_frontend_execution_role_arn
  existing_task_role_arn      = var.existing_frontend_task_role_arn

  # Use existing log group if specified
  existing_log_group_name = var.existing_frontend_log_group

  # Environment variables for the frontend service
  environment_variables = {
    DJANGO_SECRET_KEY = "dummy-placeholder-secret-key" # Will be overridden in production
    DJANGO_DEBUG      = var.environment == "prod" ? "False" : "True"
    # Connect to backend via API Gateway with API key for better monitoring and control
    BACKEND_URL            = module.api_gateway.api_gateway_url
    BACKEND_API_KEY        = "dummy-placeholder-api-key" # Will be replaced with actual frontend API key
    DJANGO_SETTINGS_MODULE = "frontend.settings"
    PORT                   = "8000"
    # Required JAO Backend URL for frontend to communicate with backend services
    JAO_BACKEND_URL = module.api_gateway.api_gateway_url
    # Add timeout setting for backend requests
    JAO_BACKEND_TIMEOUT = "15"
    # Add HTTP/2 setting for backend requests
    JAO_BACKEND_ENABLE_HTTP2 = "true"
    # Session configuration
    SESSION_COOKIE_SECURE = var.environment == "prod" ? "true" : "false"
    # Set environment for Django settings selection
    ENV = var.environment
  }
  health_check_path      = "/health"
  internal_lb            = false # Frontend LB is public-facing
  logs_retention_in_days = var.environment == "prod" ? 90 : 30

  tags = local.common_tags
}

# Outputs are defined in outputs.tf

# Add ECS security group to DB access security group after ECS is created
# This breaks the circular dependency while still allowing ECS tasks to access the database
resource "aws_security_group_rule" "allow_ecs_to_db" {
  type                     = "ingress"
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  security_group_id        = aws_security_group.db_access.id
  source_security_group_id = module.ecs.security_group_id
  description              = "Allow ECS tasks to access database"
}
