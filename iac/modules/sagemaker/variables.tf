# variables.tf - SageMaker Notebook Instance Module Variables

variable "app_name" {
  description = "Name of the application"
  type        = string
}

variable "environment" {
  description = "Environment name (e.g., dev, staging, prod)"
  type        = string
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod."
  }
}

# Network Configuration
variable "vpc_id" {
  description = "VPC ID where SageMaker notebook will be deployed"
  type        = string
}

variable "vpc_cidr_block" {
  description = "CIDR block of the VPC for security group rules"
  type        = string
  default     = null
}

variable "subnet_id" {
  description = "Subnet ID for the SageMaker notebook instance"
  type        = string
}

variable "direct_internet_access" {
  description = "Whether to enable direct internet access for the notebook instance"
  type        = string
  default     = "Disabled"
  validation {
    condition     = contains(["Enabled", "Disabled"], var.direct_internet_access)
    error_message = "Direct internet access must be 'Enabled' or 'Disabled'."
  }
}

# Aurora Database Configuration
variable "aurora_endpoint" {
  description = "Endpoint of the Aurora database (reader endpoint for read replica)"
  type        = string
}

variable "aurora_port" {
  description = "Port number for Aurora PostgreSQL database"
  type        = number
  default     = 5432
}

variable "database_name" {
  description = "Name of the database to connect to"
  type        = string
}

variable "database_username" {
  description = "Username for database connection"
  type        = string
  sensitive   = true
}

variable "database_password" {
  description = "Password for database connection"
  type        = string
  sensitive   = true
}

# S3 Configuration
variable "data_bucket_name" {
  description = "Name of the S3 bucket for data science work"
  type        = string
}

variable "data_bucket_arn" {
  description = "ARN of the S3 bucket for data science work"
  type        = string
}

# SageMaker Notebook Configuration
variable "notebook_instance_type" {
  description = "Instance type for the SageMaker notebook"
  type        = string
  default     = "ml.t3.medium"
  validation {
    condition     = can(regex("^ml\\.", var.notebook_instance_type))
    error_message = "Notebook instance type must start with 'ml.'"
  }
}

variable "volume_size" {
  description = "Size of the EBS volume attached to the notebook instance in GB"
  type        = number
  default     = 20
  validation {
    condition     = var.volume_size >= 5 && var.volume_size <= 16384
    error_message = "Volume size must be between 5 and 16384 GB."
  }
}

variable "root_access" {
  description = "Whether root access is enabled or disabled for the notebook instance"
  type        = string
  default     = "Enabled"
  validation {
    condition     = contains(["Enabled", "Disabled"], var.root_access)
    error_message = "Root access must be 'Enabled' or 'Disabled'."
  }
}

variable "platform_identifier" {
  description = "Platform identifier for the notebook instance (null to let AWS choose)"
  type        = string
  default     = null
}

# Code Repository Configuration
variable "default_code_repository" {
  description = "URL of the default Git repository to associate with the notebook instance"
  type        = string
  default     = null
}

variable "additional_code_repositories" {
  description = "List of additional Git repository URLs to associate with the notebook instance"
  type        = list(string)
  default     = []
}

# Security Configuration
variable "kms_key_id" {
  description = "KMS key ID to use for encrypting the notebook instance storage"
  type        = string
  default     = null
}

# Auto-stop Configuration
variable "auto_shutdown_idle_time" {
  description = "Time in minutes to wait before auto-shutting down idle notebooks (0 to disable)"
  type        = number
  default     = 120
  validation {
    condition     = var.auto_shutdown_idle_time >= 0
    error_message = "Auto shutdown idle time must be non-negative."
  }
}

# Monitoring Configuration
variable "enable_monitoring" {
  description = "Enable CloudWatch monitoring for SageMaker resources"
  type        = bool
  default     = true
}

variable "log_retention_days" {
  description = "Number of days to retain CloudWatch logs"
  type        = number
  default     = 30
  validation {
    condition = contains([
      1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1827, 3653
    ], var.log_retention_days)
    error_message = "Log retention days must be a valid CloudWatch retention period."
  }
}

variable "alarm_actions" {
  description = "List of ARNs to notify when CloudWatch alarms trigger"
  type        = list(string)
  default     = []
}

# Tags
variable "tags" {
  description = "Additional tags to apply to all resources"
  type        = map(string)
  default     = {}
}

# Lifecycle Configuration
variable "enable_lifecycle_config" {
  description = "Enable lifecycle configuration for auto-stop and startup scripts"
  type        = bool
  default     = false
}

# Instance Metadata Service Configuration
variable "instance_metadata_service_version" {
  description = "Version of the instance metadata service to use"
  type        = string
  default     = "2"
  validation {
    condition     = contains(["1", "2"], var.instance_metadata_service_version)
    error_message = "Instance metadata service version must be '1' or '2'."
  }
}

# Lifecycle Configuration
variable "lifecycle_config_on_start" {
  description = "Custom on-start lifecycle configuration script (base64 encoded)"
  type        = string
  default     = null
}

variable "lifecycle_config_on_create" {
  description = "Custom on-create lifecycle configuration script (base64 encoded)"
  type        = string
  default     = null
}
