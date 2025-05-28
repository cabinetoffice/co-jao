# variables.tf
variable "aws_region" {
  description = "The AWS region to deploy resources"
  type        = string
  default     = "eu-west-2"
}

variable "app_name" {
  description = "Name of the application"
  type        = string
  default     = "python-api"
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
  default     = 5000
}

variable "task_cpu" {
  description = "CPU units for the ECS task"
  type        = number
  default     = 256
}

variable "task_memory" {
  description = "Memory for the ECS task"
  type        = number
  default     = 512
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
    LOG_LEVEL = "INFO"
  }
}

variable "initialization_bucket" {
  description = "S3 bucket name where initialization scripts will be stored (if empty, a bucket will be created with a default name)"
  type        = string
  default     = ""
}

variable "skip_ecr_creation" {
  description = "Whether to skip creating ECR repositories (useful when repositories already exist)"
  type        = bool
  default     = false
}

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

variable "skip_frontend_role_creation" {
  description = "Whether to skip creating IAM roles for the frontend service"
  type        = bool
  default     = false
}

variable "skip_backend_role_creation" {
  description = "Whether to skip creating IAM roles for the backend service"
  type        = bool
  default     = false
}

variable "skip_cloudwatch_logs_creation" {
  description = "Whether to skip creating CloudWatch log groups"
  type        = bool
  default     = false
}

variable "skip_s3_bucket_creation" {
  description = "Whether to skip creating the S3 bucket"
  type        = bool
  default     = true
}

variable "skip_param_group_creation" {
  description = "Whether to skip creating the RDS parameter group"
  type        = bool
  default     = false
}

variable "skip_secret_creation" {
  description = "Whether to skip creating the Secrets Manager secret"
  type        = bool
  default     = false
}

variable "skip_policy_creation" {
  description = "Whether to skip creating IAM policies"
  type        = bool
  default     = false
}

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
  default     = "INFO"
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
variable "skip_vpc_creation" {
  description = "Whether to skip creating the VPC (useful when VPC already exists)"
  type        = bool
  default     = false
}

variable "existing_vpc_id" {
  description = "ID of existing VPC to use if skip_vpc_creation is true"
  type        = string
  default     = ""
}

variable "skip_cloudwatch_creation" {
  description = "Whether to skip creating CloudWatch log groups"
  type        = bool
  default     = false
}

variable "existing_backend_log_group" {
  description = "Name of existing backend CloudWatch log group to use if skip_cloudwatch_creation is true"
  type        = string
  default     = ""
}

variable "existing_frontend_log_group" {
  description = "Name of existing frontend CloudWatch log group to use if skip_cloudwatch_creation is true"
  type        = string
  default     = ""
}

variable "skip_iam_role_creation" {
  description = "Whether to skip creating IAM roles"
  type        = bool
  default     = false
}

variable "existing_task_execution_role_arn" {
  description = "ARN of existing task execution role to use for ECS if skip_iam_role_creation is true"
  type        = string
  default     = ""
}

variable "existing_frontend_execution_role_arn" {
  description = "ARN of existing execution role to use for frontend if skip_iam_role_creation is true"
  type        = string
  default     = ""
}

variable "existing_frontend_task_role_arn" {
  description = "ARN of existing task role to use for frontend if skip_iam_role_creation is true"
  type        = string
  default     = ""
}
