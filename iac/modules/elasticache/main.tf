# resource "aws_elasticache_cluster" "redis" {
#   cluster_id                   = var.cluster_id
#   replication_group_id         = aws_elasticache_replication_group.this.replication_group_id
#   apply_immediately            = var.apply_immediately
#   preferred_availability_zones = length(var.preferred_availability_zones) > 0 ? var.preferred_availability_zones : null

#   tags = merge(
#     var.tags,
#     {
#       Name    = var.cluster_id
#       Purpose = "Celery Redis Backend"
#     }
#   )
# }

resource "aws_elasticache_replication_group" "this" {
  description                = "Celery Redis Backend Replication Group"
  replication_group_id       = var.cluster_id
  at_rest_encryption_enabled = true
  transit_encryption_enabled = true

  replicas_per_node_group    = 1
  automatic_failover_enabled = true
  num_node_groups            = 2
  node_type                  = var.node_type
  snapshot_retention_limit   = var.snapshot_retention_limit
  snapshot_window            = var.snapshot_window
  port                       = var.port
  subnet_group_name          = var.subnet_group_name
  security_group_ids         = var.security_group_ids
  parameter_group_name       = aws_elasticache_parameter_group.celery_redis[0].name
  maintenance_window         = var.maintenance_window
  engine_version             = var.engine_version

}

resource "aws_elasticache_parameter_group" "celery_redis" {
  count  = var.parameter_group_name == "default.redis7" ? 1 : 0
  family = "redis7"
  name   = "${var.cluster_id}-celery-params"
  parameter {
    name  = "cluster-enabled"
    value = "yes"
  }
  parameter {
    name  = "maxmemory-policy"
    value = "allkeys-lru"
  }
  parameter {
    name  = "timeout"
    value = "300"
  }
  parameter {
    name  = "tcp-keepalive"
    value = "60"
  }
  tags = var.tags
}
