variable "name_prefix" {
  description = "Prefix for naming resources"
  type        = string
}

variable "environment" {
  description = "Environment name (dev, stage, prod)"
  type        = string
}

variable "ecr_repository_url" {
  description = "ECR repository URL for the frontend container image"
  type        = string
}

variable "container_port" {
  description = "Port exposed by the frontend container"
  type        = number
  default     = 8000
}

variable "vpc_id" {
  description = "ID of the VPC to deploy resources"
  type        = string
}

variable "private_subnet_ids" {
  description = "List of private subnet IDs for the ECS tasks"
  type        = list(string)
}

variable "public_subnet_ids" {
  description = "List of public subnet IDs for the load balancer if public"
  type        = list(string)
}

variable "cpu" {
  description = "CPU units for the frontend ECS task"
  type        = number
  default     = 256
}

variable "memory" {
  description = "Memory for the frontend ECS task"
  type        = number
  default     = 512
}

variable "desired_count" {
  description = "Number of frontend ECS tasks to run"
  type        = number
  default     = 2
}

variable "min_capacity" {
  description = "Minimum number of frontend tasks for auto scaling"
  type        = number
  default     = 1
}

variable "max_capacity" {
  description = "Maximum number of frontend tasks for auto scaling"
  type        = number
  default     = 4
}

variable "environment_variables" {
  description = "Environment variables for the frontend container"
  type        = map(string)
  default     = {}
}

variable "health_check_path" {
  description = "Path for the frontend health check"
  type        = string
  default     = "/health"
}

variable "internal_lb" {
  description = "Whether the load balancer should be internal"
  type        = bool
  default     = false
}

variable "logs_retention_in_days" {
  description = "Number of days to retain CloudWatch logs"
  type        = number
  default     = 30
}

variable "tags" {
  description = "Additional tags for resources"
  type        = map(string)
  default     = {}
}

# Skip resource creation variables


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
