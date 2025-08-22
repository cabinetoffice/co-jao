# Aurora PostgreSQL with pgvector module

locals {
  name_prefix = var.name_prefix != null ? var.name_prefix : "${var.app_name}-${var.environment}"
  port        = var.port != null ? var.port : 5432

  engine_version = var.use_serverless ? "13.9" : var.engine_version

  default_parameters = [
    {
      name  = "shared_preload_libraries"
      value = "pg_stat_statements,pg_hint_plan"
    },
    {
      name  = "log_min_duration_statement"
      value = var.log_min_duration
    },
    {
      name  = "wal_sender_timeout"
      value = "0"
    }
  ]

  combined_parameters = concat(local.default_parameters, var.additional_parameters)

  # Compute all tags
  tags = merge(
    var.tags,
    {
      Name        = local.name_prefix
      Environment = var.environment
      Terraform   = "true"
      Module      = "aurora_pgvector"
    }
  )
}

# Security Group for the Aurora cluster
resource "aws_security_group" "aurora" {
  name        = "${local.name_prefix}-aurora-sg"
  description = "Security group for Aurora PostgreSQL"
  vpc_id      = var.vpc_id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = local.tags
}

resource "aws_security_group_rule" "aurora_ingress_cidr" {
  count = length(var.allowed_cidr_blocks) > 0 ? 1 : 0

  security_group_id = aws_security_group.aurora.id
  type              = "ingress"
  from_port         = local.port
  to_port           = local.port
  protocol          = "tcp"
  cidr_blocks       = var.allowed_cidr_blocks
  description       = "Allow PostgreSQL from specified CIDR blocks"
}

resource "aws_security_group_rule" "aurora_ingress_sg" {
  count = length(var.allowed_security_groups)

  security_group_id        = aws_security_group.aurora.id
  type                     = "ingress"
  from_port                = local.port
  to_port                  = local.port
  protocol                 = "tcp"
  source_security_group_id = var.allowed_security_groups[count.index]
  description              = "Allow PostgreSQL from security group ${var.allowed_security_groups[count.index]}"
}

# Security group rule for SageMaker access should be created in main.tf to avoid circular dependency

# subnet group for the Aurora cluster
resource "aws_db_subnet_group" "aurora" {
  name       = "${local.name_prefix}-subnet-group"
  subnet_ids = var.subnet_ids

  tags = local.tags
}

# parameter group for PostgreSQL
resource "aws_rds_cluster_parameter_group" "aurora" {
  name        = "${local.name_prefix}-param-group"
  family      = "aurora-postgresql${split(".", local.engine_version)[0]}"
  description = "Parameter group for Aurora PostgreSQL"

  dynamic "parameter" {
    for_each = local.combined_parameters
    content {
      name         = parameter.value.name
      value        = tostring(parameter.value.value)
      apply_method = try(parameter.value.apply_method, "pending-reboot")
    }
  }

  tags = local.tags
}

# Create the Aurora cluster
resource "aws_rds_cluster" "aurora" {
  cluster_identifier = "${local.name_prefix}-cluster"
  engine             = "aurora-postgresql"
  engine_version     = local.engine_version
  engine_mode        = var.use_serverless ? "serverless" : "provisioned"
  database_name      = var.database_name
  master_username    = var.master_username
  # master_password         = var.master_password != null ? var.master_password : aws_secretsmanager_secret_version.password["main"].secret_string
  master_password         = "secrettpassword"
  port                    = local.port
  db_subnet_group_name    = aws_db_subnet_group.aurora.name
  vpc_security_group_ids  = [aws_security_group.aurora.id]
  backup_retention_period = var.backup_retention_period
  preferred_backup_window = var.preferred_backup_window

  # Serverless v1 settings
  dynamic "scaling_configuration" {
    for_each = var.use_serverless ? [1] : []
    content {
      auto_pause               = var.auto_pause
      min_capacity             = var.min_capacity
      max_capacity             = var.max_capacity
      seconds_until_auto_pause = var.seconds_until_auto_pause
      timeout_action           = "RollbackCapacityChange"
    }
  }

  # Provisioned settings
  dynamic "serverlessv2_scaling_configuration" {
    for_each = !var.use_serverless ? [1] : []
    content {
      min_capacity = var.min_capacity
      max_capacity = var.max_capacity
    }
  }

  db_cluster_parameter_group_name = aws_rds_cluster_parameter_group.aurora.name
  apply_immediately               = var.apply_immediately
  skip_final_snapshot             = var.skip_final_snapshot
  final_snapshot_identifier       = var.skip_final_snapshot ? null : "${local.name_prefix}-final-snapshot-${formatdate("YYYYMMDDhhmmss", timestamp())}"
  deletion_protection             = var.deletion_protection

  # Enable IAM database authentication if requested
  iam_database_authentication_enabled = var.enable_iam_auth

  # Enable storage encryption if requested
  storage_encrypted = var.storage_encrypted
  kms_key_id        = var.kms_key_id

  # Conditional snapshot identifier for restoring from snapshot
  snapshot_identifier = var.snapshot_identifier

  # Enable PostgreSQL Logical Replication
  enabled_cloudwatch_logs_exports = ["postgresql"]

  lifecycle {
    prevent_destroy = false
  }

  tags = local.tags
}

# Create Aurora instances (only for provisioned clusters)
resource "aws_rds_cluster_instance" "aurora" {
  count = var.use_serverless ? 0 : var.instance_count

  identifier           = "${local.name_prefix}-instance-${count.index + 1}"
  cluster_identifier   = aws_rds_cluster.aurora.id
  instance_class       = "db.serverless"
  engine               = aws_rds_cluster.aurora.engine
  engine_version       = aws_rds_cluster.aurora.engine_version
  db_subnet_group_name = aws_db_subnet_group.aurora.name

  # Performance Insights settings
  performance_insights_enabled          = var.performance_insights_enabled
  performance_insights_retention_period = var.performance_insights_enabled ? var.performance_insights_retention_period : null

  monitoring_interval = var.enhanced_monitoring_interval
  monitoring_role_arn = var.enhanced_monitoring_interval > 0 ? aws_iam_role.monitoring[0].arn : null

  apply_immediately = var.apply_immediately

  tags = local.tags
}

# Create dedicated read replica for data science workloads
resource "aws_rds_cluster_instance" "data_science_replica" {
  count = var.create_data_science_replica && !var.use_serverless ? 1 : 0

  identifier           = "${local.name_prefix}-data-science-replica"
  cluster_identifier   = aws_rds_cluster.aurora.id
  instance_class       = var.data_science_instance_class != null ? var.data_science_instance_class : "db.serverless"
  engine               = aws_rds_cluster.aurora.engine
  engine_version       = aws_rds_cluster.aurora.engine_version
  db_subnet_group_name = aws_db_subnet_group.aurora.name

  # Enable query performance monitoring for data science workloads
  performance_insights_enabled          = true
  performance_insights_retention_period = var.performance_insights_retention_period != null ? var.performance_insights_retention_period : 7

  monitoring_interval = var.enhanced_monitoring_interval
  monitoring_role_arn = var.enhanced_monitoring_interval > 0 ? aws_iam_role.monitoring[0].arn : null

  apply_immediately = var.apply_immediately

  tags = merge(local.tags, {
    Purpose = "data-science"
    Type    = "read-replica"
  })
}

# Store password in Secrets Manager if auto-generated
# resource "aws_secretsmanager_secret" "password" {
#   for_each    = var.master_password == null ? { "main" = true } : {}
#   name        = "${local.name_prefix}-db-password"
#   description = "Master password for ${local.name_prefix} Aurora PostgreSQL cluster"
#   tags        = local.tags
# }

# resource "aws_secretsmanager_secret_version" "password" {
#   for_each      = var.master_password == null ? { "main" = true } : {}
#   secret_id     = aws_secretsmanager_secret.password["main"].id
#   secret_string = random_password.master["main"].result
# }

# Create CloudWatch alarms for the cluster
resource "aws_cloudwatch_metric_alarm" "cpu_utilization" {
  count               = var.create_cloudwatch_alarms ? 1 : 0
  alarm_name          = "${local.name_prefix}-high-cpu"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/RDS"
  period              = 300
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "Aurora PostgreSQL high CPU utilization"
  alarm_actions       = var.cloudwatch_alarm_actions
  ok_actions          = var.cloudwatch_ok_actions

  dimensions = {
    DBClusterIdentifier = aws_rds_cluster.aurora.id
  }

  tags = local.tags
}

resource "aws_cloudwatch_metric_alarm" "free_memory" {
  count               = var.create_cloudwatch_alarms ? 1 : 0
  alarm_name          = "${local.name_prefix}-low-memory"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 2
  metric_name         = "FreeableMemory"
  namespace           = "AWS/RDS"
  period              = 300
  statistic           = "Average"
  threshold           = 1000000000 # 1GB in bytes
  alarm_description   = "Aurora PostgreSQL low freeable memory"
  alarm_actions       = var.cloudwatch_alarm_actions
  ok_actions          = var.cloudwatch_ok_actions

  dimensions = {
    DBClusterIdentifier = aws_rds_cluster.aurora.id
  }

  tags = local.tags
}

resource "aws_cloudwatch_metric_alarm" "disk_queue_depth" {
  count               = var.create_cloudwatch_alarms ? 1 : 0
  alarm_name          = "${local.name_prefix}-disk-queue"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "DiskQueueDepth"
  namespace           = "AWS/RDS"
  period              = 300
  statistic           = "Average"
  threshold           = 20
  alarm_description   = "Aurora PostgreSQL high disk queue depth"
  alarm_actions       = var.cloudwatch_alarm_actions
  ok_actions          = var.cloudwatch_ok_actions

  dimensions = {
    DBClusterIdentifier = aws_rds_cluster.aurora.id
  }

  tags = local.tags
}

# Create a Route53 DNS record if requested
resource "aws_route53_record" "aurora" {
  count   = var.create_route53_record ? 1 : 0
  zone_id = var.route53_zone_id
  name    = var.route53_record_name != null ? var.route53_record_name : local.name_prefix
  type    = "CNAME"
  ttl     = 300
  records = [aws_rds_cluster.aurora.endpoint]
}

# Create a db entry bootstrap script in S3 if provided
resource "aws_s3_object" "init_script" {
  count  = var.init_script != null ? 1 : 0
  bucket = var.init_script_bucket
  key    = "${local.name_prefix}/init.sql"
  content = templatefile(var.init_script, {
    database_name = var.database_name
  })
  etag = md5(templatefile(var.init_script, {
    database_name = var.database_name
  }))
}
