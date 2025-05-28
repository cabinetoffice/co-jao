# variables.tf for S3 bucket module

variable "bucket_name" {
  description = "Name of the S3 bucket to create"
  type        = string
}

variable "force_destroy" {
  description = "Boolean that indicates all objects should be deleted from the bucket when the bucket is destroyed"
  type        = bool
  default     = false
}

# prevent_destroy is now set directly in the lifecycle block
# and cannot use variables per Terraform constraints

variable "tags" {
  description = "A map of tags to assign to the bucket"
  type        = map(string)
  default     = {}
}

variable "block_public_acls" {
  description = "Whether Amazon S3 should block public ACLs for this bucket"
  type        = bool
  default     = true
}

variable "block_public_policy" {
  description = "Whether Amazon S3 should block public bucket policies for this bucket"
  type        = bool
  default     = true
}

variable "ignore_public_acls" {
  description = "Whether Amazon S3 should ignore public ACLs for this bucket"
  type        = bool
  default     = true
}

variable "restrict_public_buckets" {
  description = "Whether Amazon S3 should restrict public bucket policies for this bucket"
  type        = bool
  default     = true
}

variable "enable_versioning" {
  description = "Enable versioning on the bucket"
  type        = bool
  default     = false
}

variable "enable_encryption" {
  description = "Enable server-side encryption for the bucket"
  type        = bool
  default     = true
}

variable "kms_key_id" {
  description = "ARN of the KMS key to use for encryption. If not specified, AES256 encryption will be used"
  type        = string
  default     = null
}

variable "lifecycle_rules" {
  description = "List of maps containing lifecycle rules configuration"
  type        = any
  default     = []
}

variable "cors_rules" {
  description = "List of maps containing CORS rules configuration"
  type        = any
  default     = []
}

variable "bucket_policy" {
  description = "A bucket policy as a JSON formatted string"
  type        = string
  default     = null
}

variable "acl" {
  description = "The canned ACL to apply to the bucket"
  type        = string
  default     = null
}

variable "enable_access_logging" {
  description = "Enable access logging for the bucket"
  type        = bool
  default     = false
}

variable "access_log_target_bucket" {
  description = "The name of the bucket to deliver access logs to"
  type        = string
  default     = null
}

variable "access_log_target_prefix" {
  description = "The prefix to use for all log object keys"
  type        = string
  default     = "logs/"
}

variable "website_configuration" {
  description = "Map containing static web-site hosting configuration"
  type        = any
  default     = null
}

variable "create_bucket" {
  description = "Controls if S3 bucket should be created"
  type        = bool
  default     = false
}
