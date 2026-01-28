# outputs.tf - JAO Data Engine Infrastructure Outputs

# =============================================================================
# ECR REPOSITORY
# =============================================================================

output "ecr_repository_url" {
  description = "ECR Repository URL (use with :data-engine-* or :skills-worker-* tags)"
  value       = aws_ecr_repository.main.repository_url
}

output "ecr_repository_name" {
  description = "ECR Repository Name"
  value       = aws_ecr_repository.main.name
}

output "data_engine_image_url" {
  description = "Full image URL for data engine (Python 3.12)"
  value       = "${aws_ecr_repository.main.repository_url}:${var.data_engine_image_tag}"
}

output "skills_worker_image_url" {
  description = "Full image URL for skills worker (Python 3.10)"
  value       = "${aws_ecr_repository.main.repository_url}:${var.skills_worker_image_tag}"
}

# =============================================================================
# VPC
# =============================================================================

output "vpc_id" {
  description = "ID of the VPC"
  value       = module.vpc.vpc_id
}

output "private_subnet_ids" {
  description = "IDs of the private subnets"
  value       = module.vpc.private_subnet_ids
}

output "public_subnet_ids" {
  description = "IDs of the public subnets"
  value       = module.vpc.public_subnet_ids
}

# =============================================================================
# DATABASE
# =============================================================================

output "database_endpoint" {
  description = "The PostgreSQL database endpoint"
  value       = module.vectordb.cluster_endpoint
}

output "database_reader_endpoint" {
  description = "The PostgreSQL database reader endpoint"
  value       = module.vectordb.reader_endpoint
}

output "database_name" {
  description = "The PostgreSQL database name"
  value       = module.vectordb.database_name
}

output "database_username" {
  description = "The PostgreSQL master username"
  value       = module.vectordb.master_username
}

output "database_port" {
  description = "The PostgreSQL database port"
  value       = module.vectordb.port
}

# =============================================================================
# ECS CLUSTER & TASKS
# =============================================================================

output "ecs_cluster_name" {
  description = "Name of the ECS cluster"
  value       = module.scheduled_tasks.cluster_name
}

output "ecs_cluster_arn" {
  description = "ARN of the ECS cluster"
  value       = module.scheduled_tasks.cluster_arn
}

output "data_engine_task_definition_arn" {
  description = "ARN of the data engine task definition"
  value       = module.scheduled_tasks.data_engine_task_definition_arn
}

output "data_engine_schedule_name" {
  description = "Name of the data engine EventBridge schedule"
  value       = module.scheduled_tasks.data_engine_schedule_name
}

output "skills_worker_task_definition_arn" {
  description = "ARN of the skills worker task definition"
  value       = module.scheduled_tasks.skills_worker_task_definition_arn
}

output "skills_worker_schedule_name" {
  description = "Name of the skills worker EventBridge schedule (if enabled)"
  value       = module.scheduled_tasks.skills_worker_schedule_name
}

output "task_log_group" {
  description = "CloudWatch log group for scheduled tasks"
  value       = module.scheduled_tasks.log_group_name
}

# =============================================================================
# S3 BUCKETS
# =============================================================================

output "initialization_bucket_name" {
  description = "Name of the S3 bucket for initialization scripts"
  value       = module.initialization_bucket.bucket_id
}

output "initialization_bucket_arn" {
  description = "ARN of the S3 bucket for initialization scripts"
  value       = module.initialization_bucket.bucket_arn
}

# =============================================================================
# BASTION HOST (Optional)
# =============================================================================

output "bastion_public_ip" {
  description = "Public IP of the bastion host"
  value       = var.enable_bastion_host ? module.bastion[0].bastion_public_ip : null
}

output "bastion_ssh_command" {
  description = "SSH command to connect to the bastion host"
  value       = var.enable_bastion_host ? "ssh -i <your-key.pem> ec2-user@${module.bastion[0].bastion_public_ip}" : null
}

# =============================================================================
# SAGEMAKER (Optional)
# =============================================================================

output "sagemaker_notebook_name" {
  description = "Name of the SageMaker notebook instance"
  value       = var.enable_sagemaker_environment ? module.sagemaker[0].notebook_instance_name : null
}

output "sagemaker_notebook_url" {
  description = "URL to access the SageMaker notebook instance"
  value       = var.enable_sagemaker_environment ? module.sagemaker[0].notebook_instance_url : null
}

output "data_science_bucket" {
  description = "S3 bucket for data science work"
  value       = var.enable_sagemaker_environment ? module.data_science_bucket[0].bucket_id : null
}

output "data_science_db_endpoint" {
  description = "Database endpoint for data science (read replica if available)"
  value = var.enable_sagemaker_environment ? coalesce(
    module.vectordb.data_science_replica_endpoint,
    module.vectordb.reader_endpoint
  ) : null
}

output "sagemaker_connection_instructions" {
  description = "Instructions for accessing SageMaker and connecting to the database"
  value       = var.enable_sagemaker_environment ? module.sagemaker[0].connection_instructions : "SageMaker environment not enabled"
}
