resource "aws_elasticache_cluster" "redis" {
  cluster_id           = var.cluster_id
  engine               = "redis"
  node_type            = var.node_type
  num_cache_nodes      = var.num_cache_nodes
  parameter_group_name = var.parameter_group_name
  port                 = var.port
  subnet_group_name    = var.subnet_group_name
  security_group_ids   = var.security_group_ids
  engine_version       = var.engine_version

  # Maintenance and backup settings
  apply_immediately        = var.apply_immediately
  maintenance_window       = var.maintenance_window
  snapshot_retention_limit = var.snapshot_retention_limit
  snapshot_window          = var.snapshot_window

  # Availability zone settings
  az_mode                      = var.az_mode
  preferred_availability_zones = length(var.preferred_availability_zones) > 0 ? var.preferred_availability_zones : null

  tags = merge(
    var.tags,
    {
      Name    = var.cluster_id
      Purpose = "Celery Redis Backend"
    }
  )
}

resource "aws_elasticache_parameter_group" "celery_redis" {
  count  = var.parameter_group_name == "default.redis7" ? 1 : 0
  family = "redis7"
  name   = "${var.cluster_id}-celery-params"
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
