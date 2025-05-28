# Aurora PostgreSQL with pgvector module variables
# variables.tf

variable "app_name" {
  description = "Name of the application"
  type        = string
}

variable "environment" {
  description = "Environment (e.g., dev, stage, prod)"
  type        = string
}

variable "name_prefix" {
  description = "Prefix for resource names. If not provided, will use '{app_name}-{environment}'"
  type        = string
  default     = null
}

variable "vpc_id" {
  description = "VPC ID where the Aurora cluster will be deployed"
  type        = string
}

variable "subnet_ids" {
  description = "List of subnet IDs where the Aurora cluster will be deployed"
  type        = list(string)
}

variable "allowed_security_groups" {
  description = "List of security group IDs that are allowed to access the Aurora cluster"
  type        = list(string)
  default     = []
}

variable "allowed_cidr_blocks" {
  description = "List of CIDR blocks that are allowed to access the Aurora cluster"
  type        = list(string)
  default     = []
}

variable "port" {
  description = "Port on which the Aurora cluster accepts connections"
  type        = number
  default     = 5432
}

variable "database_name" {
  description = "Name of the default database to create"
  type        = string
}

variable "master_username" {
  description = "Username for the master DB user"
  type        = string
  default     = "postgres"
}

# variable "master_password" {
#   description = "Password for the master DB user. If not provided, a random one will be generated and stored in Secrets Manager"
#   type        = string
#   default     = true
#   sensitive   = true
# }

variable "engine_version" {
  description = "Version of Aurora PostgreSQL to use. For pgvector support, use 13.9 or higher"
  type        = string
  default     = "15.10"
}

variable "instance_count" {
  description = "Number of Aurora instances to create (only applicable for provisioned clusters)"
  type        = number
  default     = 1
}

variable "use_serverless" {
  description = "Whether to use Aurora Serverless v1 (true) or Provisioned with Serverless v2 scaling (false)"
  type        = bool
  default     = false
}

variable "min_capacity" {
  description = "Minimum capacity for the Aurora cluster. For serverless, this is in ACUs. For provisioned, this is in RPUs"
  type        = number
  default     = 0.5
}

variable "max_capacity" {
  description = "Maximum capacity for the Aurora cluster. For serverless, this is in ACUs. For provisioned, this is in RPUs"
  type        = number
  default     = 4
}

variable "auto_pause" {
  description = "Whether to auto-pause the Aurora Serverless cluster after seconds_until_auto_pause"
  type        = bool
  default     = true
}

variable "seconds_until_auto_pause" {
  description = "Seconds of no activity before an Aurora Serverless cluster is paused"
  type        = number
  default     = 300
}

variable "apply_immediately" {
  description = "Whether to apply changes immediately or during the next maintenance window"
  type        = bool
  default     = false
}

variable "backup_retention_period" {
  description = "Number of days to retain backups"
  type        = number
  default     = 7
}

variable "preferred_backup_window" {
  description = "Daily time range during which automated backups are created"
  type        = string
  default     = "02:00-03:00"
}

variable "skip_final_snapshot" {
  description = "Whether to skip the final snapshot when destroying the cluster"
  type        = bool
  default     = false
}

variable "deletion_protection" {
  description = "Whether to enable deletion protection for the Aurora cluster"
  type        = bool
  default     = true
}

variable "enable_iam_auth" {
  description = "Whether to enable IAM database authentication"
  type        = bool
  default     = false
}

variable "storage_encrypted" {
  description = "Whether to encrypt the Aurora cluster storage"
  type        = bool
  default     = true
}

variable "kms_key_id" {
  description = "ARN of the KMS key to use for encryption. If not provided, the default RDS KMS key will be used"
  type        = string
  default     = null
}

variable "snapshot_identifier" {
  description = "Identifier of the snapshot to restore from"
  type        = string
  default     = null
}

variable "performance_insights_enabled" {
  description = "Whether to enable Performance Insights"
  type        = bool
  default     = true
}

variable "performance_insights_retention_period" {
  description = "Number of days to retain Performance Insights data (7 for free tier, 731 for long term)"
  type        = number
  default     = 7
}

variable "enhanced_monitoring_interval" {
  description = "Interval in seconds for enhanced monitoring (0 to disable, 1, 5, 10, 15, 30, 60)"
  type        = number
  default     = 0
}

variable "log_min_duration" {
  description = "Minimum execution time in milliseconds for logging queries. Set to -1 to disable"
  type        = number
  default     = 5000
}

variable "additional_parameters" {
  description = "Additional parameters for the DB parameter group"
  type = list(object({
    name         = string
    value        = string
    apply_method = optional(string, "pending-reboot")
  }))
  default = []
}

variable "create_cloudwatch_alarms" {
  description = "Whether to create CloudWatch alarms for the Aurora cluster"
  type        = bool
  default     = false
}

variable "cloudwatch_alarm_actions" {
  description = "List of ARNs to notify when the CloudWatch alarm changes state (e.g., SNS topics)"
  type        = list(string)
  default     = []
}

variable "cloudwatch_ok_actions" {
  description = "List of ARNs to notify when the CloudWatch alarm returns to OK state"
  type        = list(string)
  default     = []
}

variable "create_route53_record" {
  description = "Whether to create a Route53 record for the Aurora cluster"
  type        = bool
  default     = false
}

variable "route53_zone_id" {
  description = "ID of the Route53 hosted zone where the record will be created"
  type        = string
  default     = null
}

variable "route53_record_name" {
  description = "Name of the Route53 record. If not provided, will use the name_prefix"
  type        = string
  default     = null
}

variable "init_script" {
  description = "Path to a template file containing SQL commands to run after instance creation"
  type        = string
  default     = null
}

variable "init_script_bucket" {
  description = "S3 bucket where the init script will be stored"
  type        = string
  default     = null
}

variable "prevent_destroy" {
  description = "Whether to prevent destruction of the Aurora cluster"
  type        = bool
  default     = false
}

variable "tags" {
  description = "A map of tags to add to all resources"
  type        = map(string)
  default     = {}
}
