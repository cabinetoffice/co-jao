variable "bucket_name" {
  description = "Name of the S3 bucket to create"
  type        = string
}

# create_bucket variable removed for simplification

variable "force_destroy" {
  description = "Boolean that indicates all objects should be deleted from the bucket when the bucket is destroyed"
  type        = bool
  default     = false
}

variable "tags" {
  description = "A map of tags to assign to the bucket"
  type        = map(string)
  default     = {}
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

variable "lifecycle_rules" {
  description = "List of maps containing lifecycle rules configuration"
  type        = list(object({
    id     = string
    status = string
    expiration = optional(object({
      days = number
    }))
  }))
  default = []
}