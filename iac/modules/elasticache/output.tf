output "celery_broker_url" {
  description = "Redis URL for Celery broker"
  value       = "redis://${aws_elasticache_replication_group.this.configuration_endpoint_address}:${aws_elasticache_replication_group.this.port}/0"
}

output "celery_result_backend" {
  description = "Redis URL for Celery result backend"
  value       = "redis://${aws_elasticache_replication_group.this.configuration_endpoint_address}:${aws_elasticache_replication_group.this.port}/1"
}

# Additional useful outputs
output "redis_endpoint" {
  description = "Redis configuration endpoint (for cluster mode)"
  value       = aws_elasticache_replication_group.this.configuration_endpoint_address
}

output "redis_port" {
  description = "Redis port"
  value       = aws_elasticache_replication_group.this.port
}

output "replication_group_id" {
  description = "ElastiCache replication group ID"
  value       = aws_elasticache_replication_group.this.replication_group_id
}

# If you have auth token enabled
output "redis_auth_token" {
  description = "Redis authentication token (if enabled)"
  value       = aws_elasticache_replication_group.this.auth_token
  sensitive   = true
}
