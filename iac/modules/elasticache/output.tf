locals {
  # Determine which endpoint to use based on what's available
  # Primary endpoint is used for writes (required by Celery)
  redis_endpoint = coalesce(
    aws_elasticache_replication_group.this.primary_endpoint_address,
    aws_elasticache_replication_group.this.configuration_endpoint_address,
    aws_elasticache_replication_group.this.reader_endpoint_address
  )

  # Use rediss:// protocol for TLS connections, redis:// for non-TLS
  redis_protocol = aws_elasticache_replication_group.this.transit_encryption_enabled ? "rediss" : "redis"

  # Build auth string if auth token is provided
  auth_string = var.auth_token != null ? ":${var.auth_token}@" : ""
}

output "celery_broker_url" {
  description = "Redis URL for Celery broker"
  value       = "${local.redis_protocol}://${local.auth_string}${local.redis_endpoint}:${aws_elasticache_replication_group.this.port}/0"
}

output "celery_result_backend" {
  description = "Redis URL for Celery result backend"
  value       = "${local.redis_protocol}://${local.auth_string}${local.redis_endpoint}:${aws_elasticache_replication_group.this.port}/1"
}

output "redis_endpoint" {
  description = "Redis endpoint address (primary for writes)"
  value       = local.redis_endpoint
}

output "redis_primary_endpoint" {
  description = "Redis primary endpoint address (for writes)"
  value       = aws_elasticache_replication_group.this.primary_endpoint_address
}

output "redis_reader_endpoint" {
  description = "Redis reader endpoint address (for read-only operations)"
  value       = aws_elasticache_replication_group.this.reader_endpoint_address
}

output "redis_port" {
  description = "Redis port"
  value       = aws_elasticache_replication_group.this.port
}

output "replication_group_id" {
  description = "ElastiCache replication group ID"
  value       = aws_elasticache_replication_group.this.replication_group_id
}
