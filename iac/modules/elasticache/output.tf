locals {
  # Determine which endpoint to use based on what's available
  redis_endpoint = coalesce(
    aws_elasticache_replication_group.this.reader_endpoint_address,
    aws_elasticache_replication_group.this.primary_endpoint_address,
    aws_elasticache_replication_group.this.configuration_endpoint_address
  )
}

output "celery_broker_url" {
  description = "Redis URL for Celery broker"
  value       = "redis://${local.redis_endpoint}:${aws_elasticache_replication_group.this.port}/0"
}

output "celery_result_backend" {
  description = "Redis URL for Celery result backend"
  value       = "redis://${local.redis_endpoint}:${aws_elasticache_replication_group.this.port}/1"
}

output "redis_endpoint" {
  description = "Redis endpoint address"
  value       = local.redis_endpoint
}

output "redis_port" {
  description = "Redis port"
  value       = aws_elasticache_replication_group.this.port
}

output "replication_group_id" {
  description = "ElastiCache replication group ID"
  value       = aws_elasticache_replication_group.this.replication_group_id
}
