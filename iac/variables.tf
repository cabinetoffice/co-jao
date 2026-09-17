# variables.tf - JAO Data Engine Infrastructure Variables

# =============================================================================
# CORE SETTINGS
# =============================================================================

variable "aws_region" {
  description = "The AWS region to deploy resources"
  type        = string
  default     = "eu-west-2"
}

variable "app_name" {
  description = "Name of the application"
  type        = string
  default     = "jao"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "data_engine_image_tag" {
  description = "Docker image tag for data engine (Python 3.12)"
  type        = string
  default     = "data-engine-latest"
}

variable "skills_worker_image_tag" {
  description = "Docker image tag for skills worker (Python 3.10)"
  type        = string
  default     = "skills-worker-latest"
}

# =============================================================================
# VPC CONFIGURATION
# =============================================================================

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "List of availability zones to use"
  type        = list(string)
  default     = ["eu-west-2a", "eu-west-2b"]
}

variable "private_subnet_cidrs" {
  description = "CIDR blocks for private subnets"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24"]
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for public subnets"
  type        = list(string)
  default     = ["10.0.101.0/24", "10.0.102.0/24"]
}

# =============================================================================
# VPC ENDPOINTS
# =============================================================================

variable "create_vpc_endpoints" {
  description = "Whether to create VPC endpoints"
  type        = bool
  default     = true
}

variable "create_ecr_dkr_endpoint" {
  description = "Whether to create ECR Docker Registry VPC endpoint"
  type        = bool
  default     = false
}

variable "create_ecr_api_endpoint" {
  description = "Whether to create ECR API VPC endpoint"
  type        = bool
  default     = true
}

variable "create_s3_endpoint" {
  description = "Whether to create S3 Gateway VPC endpoint"
  type        = bool
  default     = true
}

variable "create_logs_endpoint" {
  description = "Whether to create CloudWatch Logs VPC endpoint"
  type        = bool
  default     = true
}

variable "existing_ecr_dkr_endpoint_id" {
  description = "ID of existing ECR Docker Registry VPC endpoint (if any)"
  type        = string
  default     = ""
}

variable "existing_ecr_api_endpoint_id" {
  description = "ID of existing ECR API VPC endpoint (if any)"
  type        = string
  default     = ""
}

variable "existing_s3_endpoint_id" {
  description = "ID of existing S3 Gateway VPC endpoint (if any)"
  type        = string
  default     = ""
}

variable "existing_logs_endpoint_id" {
  description = "ID of existing CloudWatch Logs VPC endpoint (if any)"
  type        = string
  default     = ""
}

# =============================================================================
# DATA ENGINE TASK (Python 3.12)
# =============================================================================

variable "data_engine_cpu" {
  description = "CPU units for data engine task (256, 512, 1024, 2048, 4096)"
  type        = number
  default     = 1024
}

variable "data_engine_memory" {
  description = "Memory for data engine task in MB"
  type        = number
  default     = 4096
}

variable "data_engine_schedule_expression" {
  description = "Schedule expression for the data engine task (cron or rate)"
  type        = string
  default     = "cron(0 2 ? * SUN *)" # Every Sunday at 2 AM UTC
}

# =============================================================================
# SKILLS WORKER TASK (Python 3.10)
# =============================================================================

variable "skills_worker_cpu" {
  description = "CPU units for skills worker task"
  type        = number
  default     = 512
}

variable "skills_worker_memory" {
  description = "Memory for skills worker task in MB"
  type        = number
  default     = 2048
}

variable "enable_skills_worker_schedule" {
  description = "Whether to create a separate EventBridge schedule for skills worker"
  type        = bool
  default     = false
}

variable "skills_worker_schedule_expression" {
  description = "Schedule expression for the skills worker task (if enabled)"
  type        = string
  default     = "cron(0 3 ? * SUN *)" # Every Sunday at 3 AM UTC
}

# =============================================================================
# SCHEDULE CONTROL
# =============================================================================

variable "schedule_enabled" {
  description = "Whether the EventBridge schedules are enabled"
  type        = bool
  default     = true
}

# =============================================================================
# DATABASE CONFIGURATION
# =============================================================================

variable "db_password" {
  description = "Password for the database"
  type        = string
  sensitive   = true
}

variable "performance_insights_enabled" {
  description = "Whether to enable Performance Insights for the database"
  type        = bool
  default     = null
}

variable "enable_enhanced_monitoring" {
  description = "Whether to enable enhanced monitoring for RDS resources"
  type        = bool
  default     = false
}

variable "allowed_cidr_blocks" {
  description = "List of CIDR blocks allowed to access the Aurora database"
  type        = list(string)
  default     = []
}

# =============================================================================
# DJANGO / APPLICATION CONFIGURATION
# =============================================================================

variable "django_secret_key" {
  description = "Django secret key"
  type        = string
  sensitive   = true
}

variable "oleeo_url" {
  description = "Oleeo MSSQL database URL"
  type        = string
  default     = "mssql://user:password@host:port/dbname"
  sensitive   = true
}

variable "ingest_batch_size" {
  description = "Batch size for data ingestion"
  type        = number
  default     = 200
}

variable "vacancy_embed_limit" {
  description = "Maximum number of vacancies to embed"
  type        = number
  default     = 70000
}

variable "embedder_model" {
  description = "Model to use for embeddings"
  type        = string
  default     = "bedrock/amazon.titan-embed-text-v2:0"
}

# =============================================================================
# S3 CONFIGURATION
# =============================================================================

variable "initialization_bucket" {
  description = "S3 bucket name where initialization scripts will be stored"
  type        = string
  default     = ""
}

# =============================================================================
# BASTION HOST (Optional)
# =============================================================================

variable "enable_bastion_host" {
  description = "Enable bastion host for database access"
  type        = bool
  default     = false
}

variable "ssh_public_key" {
  description = "SSH public key for bastion host access"
  type        = string
  default     = ""
}

# =============================================================================
# SAGEMAKER (Optional)
# =============================================================================

variable "enable_sagemaker_environment" {
  description = "Enable the SageMaker data science environment with Aurora read replica"
  type        = bool
  default     = false
}

variable "sagemaker_db_username" {
  description = "Database username for SageMaker read-only access"
  type        = string
  default     = "sagemaker_readonly"
}

variable "sagemaker_db_password" {
  description = "Database password for SageMaker read-only access"
  type        = string
  sensitive   = true
  default     = ""
}
