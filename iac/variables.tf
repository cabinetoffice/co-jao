# variables.tf
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

variable "container_port" {
  description = "Port exposed by the docker container"
  type        = number
  default     = 8000
}

variable "task_cpu" {
  description = "CPU units for the ECS task"
  type        = number
  default     = 128
}

variable "task_memory" {
  description = "Memory for the ECS task"
  type        = number
  default     = 256
}

variable "desired_count" {
  description = "Number of ECS tasks to run"
  type        = number
  default     = 2
}

variable "environment_variables" {
  description = "Environment variables for the container"
  type        = map(string)
  default = {
    LOG_LEVEL = "DEBUG"
  }
}

variable "initialization_bucket" {
  description = "S3 bucket name where initialization scripts will be stored (if empty, a bucket will be created with a default name)"
  type        = string
  default     = ""
}

# skip_ecr_creation variable removed for simplification

variable "performance_insights_enabled" {
  description = "Whether to enable Performance Insights for the database"
  type        = bool
  default     = null
}

variable "enable_enhanced_monitoring" {
  description = "Whether to enable enhanced monitoring for the ECS and RDS resources"
  type        = bool
  default     = false
}

variable "create_cloudwatch_alarms" {
  description = "Whether to create CloudWatch alarms for resources"
  type        = bool
  default     = false
}

variable "enable_xray_tracing" {
  description = "Whether to enable AWS X-Ray tracing"
  type        = bool
  default     = false
}

variable "enable_api_keys" {
  description = "Whether to enable API keys for the API Gateway"
  type        = bool
  default     = true
}

variable "enable_detailed_metrics" {
  description = "Whether to enable detailed metrics for API Gateway"
  type        = bool
  default     = true
}

variable "lb_deletion_protection" {
  description = "Whether to enable deletion protection for load balancers"
  type        = bool
  default     = false
}

variable "deletion_protection" {
  description = "Whether to enable deletion protection for database resources"
  type        = bool
  default     = false
}

variable "enable_lb_access_logs" {
  description = "Whether to enable access logs for load balancers"
  type        = bool
  default     = false
}

variable "internal_lb" {
  description = "Whether load balancers should be internal only"
  type        = bool
  default     = true
}

variable "init_script" {
  description = "Path to initialization script for the database (set to null to skip)"
  type        = string
  default     = null
}

variable "aws_account_id" {
  description = "AWS Account ID for ECR repository URLs when skipping creation"
  type        = string
  default     = ""
}

# skip_* variables removed for simplification

# Enhanced API support variables
variable "enable_api_monitoring" {
  description = "Whether to enable enhanced API monitoring"
  type        = bool
  default     = true
}

variable "enable_api_tracing" {
  description = "Whether to enable AWS X-Ray tracing for the API"
  type        = bool
  default     = false
}

variable "api_rate_limit_default" {
  description = "Default API rate limit (requests per second)"
  type        = number
  default     = 100
}

variable "api_burst_limit_default" {
  description = "Default API burst limit"
  type        = number
  default     = 200
}

variable "enable_third_party_access" {
  description = "Whether to enable API key authentication for third-party access"
  type        = bool
  default     = false
}

variable "api_log_level" {
  description = "Log level for API (DEBUG, INFO, WARNING, ERROR)"
  type        = string
  default     = "DEBUG"
}

variable "enable_api_dashboard" {
  description = "Whether to create a CloudWatch dashboard for API metrics"
  type        = bool
  default     = true
}

variable "lb_access_logs_bucket" {
  description = "S3 bucket for load balancer access logs"
  type        = string
  default     = ""
}

# Skip resource creation variables
# skip_* and existing_* variables removed for simplification

variable "image_tag" {
  description = "Docker image tag to use for ECS containers"
  type        = string
  default     = "latest"
}

# VPC Endpoints Configuration
variable "create_vpc_endpoints" {
  description = "Whether to create VPC endpoints"
  type        = bool
  default     = true
}

variable "create_ecr_dkr_endpoint" {
  description = "Whether to create ECR Docker Registry VPC endpoint"
  type        = bool
  default     = false # Set to false to avoid conflict with existing endpoint
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

variable "jao_backend_superuser_password" {
  description = "Password for the JAO backend superuser"
  type        = string
  default     = ""
}

variable "jao_backend_superuser_username" {
  description = "Username for the JAO backend superuser"
  type        = string
  default     = ""
}

variable "jao_backend_superuser_email" {
  description = "Email for the JAO backend superuser"
  type        = string
  default     = ""
}
