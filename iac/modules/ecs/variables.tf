# ECS module - variables.tf
variable "name_prefix" {
  description = "Prefix to use for all resource names"
  type        = string
}

variable "environment" {
  description = "Environment name (e.g. dev, staging, prod)"
  type        = string
}

variable "ecr_repository_url" {
  description = "URL of the ECR repository"
  type        = string
}

variable "container_port" {
  description = "Port exposed by the docker container"
  type        = number
}

variable "vpc_id" {
  description = "ID of the VPC"
  type        = string
}

variable "private_subnet_ids" {
  description = "IDs of the private subnets"
  type        = list(string)
}

variable "public_subnet_ids" {
  description = "IDs of the public subnets (required for public-facing load balancers)"
  type        = list(string)
  default     = null
}

variable "cpu" {
  description = "CPU units for the ECS task"
  type        = number
  default     = 256
}

variable "memory" {
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
  default     = {}
}

variable "tags" {
  description = "Additional tags for all resources"
  type        = map(string)
  default     = {}
}

variable "container_name" {
  description = "Name of the container"
  type        = string
  default     = "app"
}

variable "health_check_path" {
  description = "Path for the health check"
  type        = string
  default     = "/health"
}

variable "deployment_maximum_percent" {
  description = "Maximum percent of tasks that can be running during a deployment"
  type        = number
  default     = 200
}

variable "deployment_minimum_healthy_percent" {
  description = "Minimum percent of tasks that must remain healthy during a deployment"
  type        = number
  default     = 100
}

variable "internal_lb" {
  description = "Whether the load balancer should be internal"
  type        = bool
  default     = true
}

variable "lb_deletion_protection" {
  description = "Whether the load balancer should have deletion protection enabled"
  type        = bool
  default     = false
}

variable "logs_retention_in_days" {
  description = "Number of days to retain logs in CloudWatch"
  type        = number
  default     = 30
}

# Enhanced API Support Variables
variable "enable_enhanced_monitoring" {
  description = "Whether to enable enhanced monitoring for the API"
  type        = bool
  default     = false
}

variable "enable_xray_tracing" {
  description = "Whether to enable AWS X-Ray tracing for the API"
  type        = bool
  default     = false
}

variable "enable_circuit_breaker" {
  description = "Whether to enable deployment circuit breaker with rollback"
  type        = bool
  default     = true
}

variable "enable_service_discovery" {
  description = "Whether to enable AWS Cloud Map service discovery"
  type        = bool
  default     = false
}

variable "service_discovery_namespace" {
  description = "AWS Cloud Map namespace for service discovery"
  type        = string
  default     = ""
}

variable "enable_lb_access_logs" {
  description = "Whether to enable ALB access logs"
  type        = bool
  default     = false
}

variable "lb_access_logs_bucket" {
  description = "S3 bucket for ALB access logs"
  type        = string
  default     = ""
}

variable "enable_cross_zone_load_balancing" {
  description = "Whether to enable cross-zone load balancing for the ALB"
  type        = bool
  default     = true
}

variable "auto_scaling_target_cpu_utilization" {
  description = "Target CPU utilization percentage for auto scaling"
  type        = number
  default     = 70
}

variable "auto_scaling_max_capacity" {
  description = "Maximum number of tasks for auto scaling"
  type        = number
  default     = 10
}

variable "auto_scaling_min_capacity" {
  description = "Minimum number of tasks for auto scaling"
  type        = number
  default     = 2
}

variable "api_rate_limiting" {
  description = "Whether to enable API rate limiting at the container level"
  type        = bool
  default     = false
}

variable "api_rate_limit_request_per_second" {
  description = "Number of API requests allowed per second"
  type        = number
  default     = 100
}

variable "enable_container_insights" {
  description = "Whether to enable container insights for the ECS cluster"
  type        = bool
  default     = true
}

variable "enhanced_metrics_collection_interval" {
  description = "Collection interval for enhanced metrics in seconds"
  type        = number
  default     = 60
}

variable "existing_log_group_name" {
  description = "Name of existing CloudWatch log group to use if skip_cloudwatch_creation is true"
  type        = string
  default     = ""
}

# Skip resource creation variables
variable "skip_cloudwatch_creation" {
  description = "Skip creation of CloudWatch log groups if they already exist"
  type        = bool
  default     = false
}

variable "skip_iam_role_creation" {
  description = "Skip creation of IAM roles if they already exist"
  type        = bool
  default     = false
}

variable "existing_task_execution_role_arn" {
  description = "ARN of existing task execution role to use if skip_iam_role_creation is true"
  type        = string
  default     = ""
}