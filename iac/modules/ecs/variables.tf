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
  description = "Whether the NLB should be internal"
  type        = bool
  default     = true
}

variable "admin_lb_internet_facing" {
  description = "Whether the admin ALB should be internet-facing (independent of NLB)"
  type        = bool
  default     = false
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

# Api Service Configuration
variable "api_command" {
  description = "Command to run for web service"
  type        = list(string)
  default     = ["poetry", "run", "hypercorn", "src.asgi:application", "--bind", "0.0.0.0:8000"]
}

variable "api_cpu" {
  description = "CPU units for web service (1024 = 1 vCPU)"
  type        = number
  default     = 512
}

variable "api_memory" {
  description = "Memory in MB for web service"
  type        = number
  default     = 1024
}

variable "api_desired_count" {
  description = "Number of web service instances"
  type        = number
  default     = 2
}

# Celery Configuration
variable "enable_celery_services" {
  description = "Enable Celery worker and beat services"
  type        = bool
  default     = false
}

variable "admin_allowed_cidrs" {
  description = "List of CIDR blocks allowed to access admin interface"
  type        = list(string)
  default     = null
}

# Celery Worker Configuration
variable "celery_worker_command" {
  description = "Command to run Celery worker"
  type        = list(string)
  default     = ["poetry", "run", "celery", "-A", "jao_backend.common.celery", "worker", "--loglevel=INFO", "--concurrency=4"]
}

variable "celery_worker_health_check" {
  description = "Health check command for Celery worker"
  type        = list(string)
  default     = ["CMD-SHELL", "poetry run celery -A jao_backend.common.celery inspect ping --timeout=10"]
}

variable "celery_worker_concurrency" {
  description = "Number of concurrent worker processes"
  type        = number
  default     = 4
}

variable "worker_cpu" {
  description = "CPU units for worker service (1024 = 1 vCPU)"
  type        = number
  default     = 1024
}

variable "worker_memory" {
  description = "Memory in MB for worker service"
  type        = number
  default     = 2048
}

variable "worker_desired_count" {
  description = "Number of worker service instances"
  type        = number
  default     = 2
}

# Celery Beat Configuration
variable "celery_beat_command" {
  description = "Command to run Celery beat"
  type        = list(string)
  default     = ["poetry", "run", "celery", "-A", "jao_backend.common.celery", "beat", "--loglevel=INFO"]
}

variable "celery_beat_health_check" {
  description = "Health check command for Celery beat"
  type        = list(string)
  default     = ["CMD-SHELL", "poetry run celery -A jao_backend.common.celery inspect ping || exit 1"]
}

variable "beat_cpu" {
  description = "CPU units for beat service (1024 = 1 vCPU)"
  type        = number
  default     = 256
}

variable "beat_memory" {
  description = "Memory in MB for beat service"
  type        = number
  default     = 512
}

variable "enable_worker_autoscaling" {
  description = "Enable auto scaling for worker"
  default     = false
}

variable "worker_min_capacity" {
  description = "Minimum capacity for worker service"
  type        = number
  default     = 1
}

variable "worker_max_capacity" {
  description = "Maximum capacity for worker service"
  type        = number
  default     = 10
}

variable "worker_cpu_target_value" {
  description = "CPU target for worker service"
  type        = number
  default     = 40
}

variable "additional_security_group_ids" {
  description = "Additional security group IDs to attach to ECS tasks"
  type        = list(string)
  default     = []
}
