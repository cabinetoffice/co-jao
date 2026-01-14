# Aurora PostgreSQL with pgvector module outputs
# outputs.tf

output "cluster_id" {
  description = "The Aurora cluster identifier"
  value       = aws_rds_cluster.aurora.id
}

output "cluster_arn" {
  description = "The ARN of the Aurora cluster"
  value       = aws_rds_cluster.aurora.arn
}

output "cluster_endpoint" {
  description = "The cluster endpoint"
  value       = aws_rds_cluster.aurora.endpoint
}

output "reader_endpoint" {
  description = "The cluster reader endpoint"
  value       = aws_rds_cluster.aurora.reader_endpoint
}

output "port" {
  description = "The port on which the DB accepts connections"
  value       = aws_rds_cluster.aurora.port
}

output "database_name" {
  description = "Name of the database"
  value       = aws_rds_cluster.aurora.database_name
}

output "master_username" {
  description = "The master username for the database"
  value       = aws_rds_cluster.aurora.master_username
}

output "security_group_id" {
  description = "ID of the security group used by the Aurora cluster"
  value       = aws_security_group.aurora.id
}

output "parameter_group_id" {
  description = "ID of the DB parameter group used by the Aurora cluster"
  value       = aws_rds_cluster_parameter_group.aurora.id
}

output "subnet_group_id" {
  description = "ID of the DB subnet group used by the Aurora cluster"
  value       = aws_db_subnet_group.aurora.id
}

# output "password_secret_arn" {
#   description = "ARN of the Secrets Manager secret containing the master password (if auto-generated)"
#   value       = var.master_password == null && length(aws_secretsmanager_secret.password) > 0 ? aws_secretsmanager_secret.password["main"].arn : null
# }

output "instance_ids" {
  description = "List of instance identifiers"
  value       = var.use_serverless ? [] : aws_rds_cluster_instance.aurora[*].id
}

output "instance_arns" {
  description = "List of instance ARNs"
  value       = var.use_serverless ? [] : aws_rds_cluster_instance.aurora[*].arn
}

output "connection_string" {
  description = "PostgreSQL connection string without credentials"
  value       = "postgresql://${aws_rds_cluster.aurora.endpoint}:${aws_rds_cluster.aurora.port}/${aws_rds_cluster.aurora.database_name}"
}

output "jdbc_connection_string" {
  description = "JDBC connection string without credentials"
  value       = "jdbc:postgresql://${aws_rds_cluster.aurora.endpoint}:${aws_rds_cluster.aurora.port}/${aws_rds_cluster.aurora.database_name}"
}

output "dns_record" {
  description = "DNS record created for the Aurora cluster"
  value       = var.create_route53_record ? aws_route53_record.aurora[0].fqdn : null
}

output "monitoring_role_arn" {
  description = "ARN of the monitoring IAM role"
  value       = var.enhanced_monitoring_interval > 0 ? aws_iam_role.monitoring[0].arn : null
}

output "cluster_resource_id" {
  description = "The resource ID of the Aurora cluster"
  value       = aws_rds_cluster.aurora.cluster_resource_id
}

output "is_serverless" {
  description = "Whether the Aurora cluster is serverless"
  value       = var.use_serverless
}

output "cloudwatch_alarm_arns" {
  description = "ARNs of the CloudWatch alarms"
  value = var.create_cloudwatch_alarms ? [
    aws_cloudwatch_metric_alarm.cpu_utilization[0].arn,
    aws_cloudwatch_metric_alarm.free_memory[0].arn,
    aws_cloudwatch_metric_alarm.disk_queue_depth[0].arn
  ] : []
}

# Data Science Replica Outputs
output "data_science_replica_id" {
  description = "Instance identifier for the data science read replica"
  value       = var.create_data_science_replica && !var.use_serverless ? aws_rds_cluster_instance.data_science_replica[0].id : null
}

output "data_science_replica_arn" {
  description = "ARN of the data science read replica instance"
  value       = var.create_data_science_replica && !var.use_serverless ? aws_rds_cluster_instance.data_science_replica[0].arn : null
}

output "data_science_replica_endpoint" {
  description = "Endpoint for the data science read replica"
  value       = var.create_data_science_replica && !var.use_serverless ? aws_rds_cluster_instance.data_science_replica[0].endpoint : null
}

output "data_science_connection_string" {
  description = "PostgreSQL connection string for data science replica (without credentials)"
  value       = var.create_data_science_replica && !var.use_serverless ? "postgresql://${aws_rds_cluster_instance.data_science_replica[0].endpoint}/${aws_rds_cluster.aurora.database_name}" : null
}
