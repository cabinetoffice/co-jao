output "cluster_id" {
  description = "The cluster identifier"
  value       = aws_elasticache_cluster.redis.cluster_id
}

output "cache_nodes" {
  description = "List of cache nodes"
  value       = aws_elasticache_cluster.redis.cache_nodes
}

output "primary_endpoint" {
  description = "The primary endpoint for the Redis cluster"
  value       = aws_elasticache_cluster.redis.cache_nodes[0].address
}

output "port" {
  description = "The port number on which the cache nodes accept connections"
  value       = aws_elasticache_cluster.redis.port
}

output "redis_url" {
  description = "Redis URL for Celery configuration"
  value       = "redis://${aws_elasticache_cluster.redis.cache_nodes[0].address}:${aws_elasticache_cluster.redis.port}"
}

output "celery_broker_url" {
  description = "Celery broker URL"
  value       = "redis://${aws_elasticache_cluster.redis.cache_nodes[0].address}:${aws_elasticache_cluster.redis.port}/0"
}

output "celery_result_backend" {
  description = "Celery result backend URL"
  value       = "redis://${aws_elasticache_cluster.redis.cache_nodes[0].address}:${aws_elasticache_cluster.redis.port}/1"
}

output "parameter_group_name" {
  description = "The parameter group name used by the cluster"
  value       = var.parameter_group_name == "default.redis7" ? aws_elasticache_parameter_group.celery_redis[0].name : var.parameter_group_name
}
