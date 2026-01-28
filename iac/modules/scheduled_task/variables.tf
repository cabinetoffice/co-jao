# modules/scheduled_task/variables.tf

variable "name_prefix" {
  description = "Prefix for resource names"
  type        = string
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
}

variable "vpc_id" {
  description = "ID of the VPC"
  type        = string
}

variable "private_subnet_ids" {
  description = "IDs of private subnets for the tasks"
  type        = list(string)
}

variable "security_group_ids" {
  description = "Additional security group IDs to attach to tasks"
  type        = list(string)
  default     = []
}

# =============================================================================
# DATA ENGINE TASK (Python 3.12)
# =============================================================================

variable "data_engine_image_url" {
  description = "ECR URL for the data engine image (Python 3.12)"
  type        = string
}

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

variable "data_engine_command" {
  description = "Command to run in the data engine container"
  type        = list(string)
  default     = ["python", "manage.py", "run_weekly_pipeline"]
}

variable "data_engine_schedule_expression" {
  description = "Schedule expression for the data engine task (cron or rate)"
  type        = string
  default     = "cron(0 2 ? * SUN *)"  # Every Sunday at 2 AM UTC
}

variable "environment_variables" {
  description = "Environment variables for the data engine container"
  type        = map(string)
  default     = {}
}

# =============================================================================
# SKILLS WORKER TASK (Python 3.10)
# =============================================================================

variable "skills_worker_image_url" {
  description = "ECR URL for the skills worker image (Python 3.10)"
  type        = string
}

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

variable "skills_worker_command" {
  description = "Command to run in the skills worker container"
  type        = list(string)
  default     = ["python", "skills_extraction.py"]
}

variable "skills_worker_environment_variables" {
  description = "Environment variables for the skills worker container"
  type        = map(string)
  default     = {}
}

variable "enable_skills_worker_schedule" {
  description = "Whether to create a separate schedule for skills worker"
  type        = bool
  default     = false
}

variable "skills_worker_schedule_expression" {
  description = "Schedule expression for the skills worker task (if enabled)"
  type        = string
  default     = "cron(0 3 ? * SUN *)"  # Every Sunday at 3 AM UTC (after data engine)
}

# =============================================================================
# COMMON SETTINGS
# =============================================================================

variable "schedule_enabled" {
  description = "Whether the schedules are enabled"
  type        = bool
  default     = true
}

variable "logs_retention_in_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 30
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}
