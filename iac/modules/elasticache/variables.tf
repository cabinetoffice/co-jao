variable "replication_group_id" {
  description = "The cluster identifier"
  type        = string
}

variable "node_type" {
  description = "The compute and memory capacity of the nodes"
  type        = string
  default     = "cache.t3.micro"
}

variable "num_cache_nodes" {
  description = "The initial number of cache nodes"
  type        = number
  default     = 1
}

variable "engine_version" {
  description = "Version number of the cache engine"
  type        = string
  default     = "7.0"
}

variable "port" {
  description = "The port number on which each cache node will accept connections"
  type        = number
  default     = 6379
}

variable "parameter_group_name" {
  description = "Name of the parameter group to associate with this cache cluster"
  type        = string
  default     = "default.redis7"
}

variable "subnet_group_name" {
  description = "Name of the subnet group to be used for the cache cluster"
  type        = string
}

variable "security_group_ids" {
  description = "List of security group IDs to associate with this cache cluster"
  type        = list(string)
}

variable "apply_immediately" {
  description = "Specifies whether any modifications are applied immediately"
  type        = bool
  default     = false
}

variable "maintenance_window" {
  description = "Specifies the weekly time range for maintenance"
  type        = string
  default     = "sun:05:00-sun:09:00"
}

variable "snapshot_retention_limit" {
  description = "The number of days for which ElastiCache will retain automatic cache cluster snapshots"
  type        = number
  default     = 5
}

variable "snapshot_window" {
  description = "The daily time range during which automated backups are created"
  type        = string
  default     = "03:00-05:00"
}

variable "tags" {
  description = "A mapping of tags to assign to the resource"
  type        = map(string)
  default     = {}
}

variable "az_mode" {
  description = "Specifies whether the nodes in this Memcached cluster are created in a single Availability Zone"
  type        = string
  default     = "single-az"
}

variable "preferred_availability_zones" {
  description = "List of the Availability Zones in which cache nodes are created"
  type        = list(string)
  default     = []
}

variable "auth_token" {
  description = "AUTH token for Redis authentication (required when transit_encryption_enabled is true)"
  type        = string
  default     = null
  sensitive   = true
}

variable "transit_encryption_enabled" {
  description = "Whether to enable transit encryption (TLS)"
  type        = bool
  default     = true
}
