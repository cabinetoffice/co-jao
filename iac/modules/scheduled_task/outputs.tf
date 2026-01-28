# modules/scheduled_task/outputs.tf

# =============================================================================
# CLUSTER
# =============================================================================

output "cluster_name" {
  description = "Name of the ECS cluster"
  value       = aws_ecs_cluster.main.name
}

output "cluster_arn" {
  description = "ARN of the ECS cluster"
  value       = aws_ecs_cluster.main.arn
}

# =============================================================================
# DATA ENGINE TASK
# =============================================================================

output "data_engine_task_definition_arn" {
  description = "ARN of the data engine task definition"
  value       = aws_ecs_task_definition.data_engine.arn
}

output "data_engine_task_definition_family" {
  description = "Family of the data engine task definition"
  value       = aws_ecs_task_definition.data_engine.family
}

output "data_engine_schedule_name" {
  description = "Name of the data engine EventBridge schedule"
  value       = aws_scheduler_schedule.data_engine.name
}

output "data_engine_schedule_arn" {
  description = "ARN of the data engine EventBridge schedule"
  value       = aws_scheduler_schedule.data_engine.arn
}

# =============================================================================
# SKILLS WORKER TASK
# =============================================================================

output "skills_worker_task_definition_arn" {
  description = "ARN of the skills worker task definition"
  value       = aws_ecs_task_definition.skills_worker.arn
}

output "skills_worker_task_definition_family" {
  description = "Family of the skills worker task definition"
  value       = aws_ecs_task_definition.skills_worker.family
}

output "skills_worker_schedule_name" {
  description = "Name of the skills worker EventBridge schedule (if enabled)"
  value       = var.enable_skills_worker_schedule ? aws_scheduler_schedule.skills_worker[0].name : null
}

output "skills_worker_schedule_arn" {
  description = "ARN of the skills worker EventBridge schedule (if enabled)"
  value       = var.enable_skills_worker_schedule ? aws_scheduler_schedule.skills_worker[0].arn : null
}

# =============================================================================
# SHARED RESOURCES
# =============================================================================

output "log_group_name" {
  description = "Name of the CloudWatch log group"
  value       = aws_cloudwatch_log_group.tasks.name
}

output "security_group_id" {
  description = "ID of the tasks security group"
  value       = aws_security_group.tasks.id
}

output "task_execution_role_arn" {
  description = "ARN of the task execution IAM role"
  value       = aws_iam_role.task_execution.arn
}

output "task_role_arn" {
  description = "ARN of the task IAM role"
  value       = aws_iam_role.task.arn
}
