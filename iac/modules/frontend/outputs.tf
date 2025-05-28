# Frontend module outputs

output "load_balancer_dns_name" {
  description = "DNS name of the frontend load balancer"
  value       = aws_lb.frontend.dns_name
}

output "load_balancer_arn" {
  description = "ARN of the frontend load balancer"
  value       = aws_lb.frontend.arn
}

output "load_balancer_id" {
  description = "ID of the frontend load balancer"
  value       = aws_lb.frontend.id
}

output "lb_listener_arn" {
  description = "ARN of the frontend load balancer HTTP listener"
  value       = aws_lb_listener.frontend_http.arn
}

output "target_group_arn" {
  description = "ARN of the frontend target group"
  value       = aws_lb_target_group.frontend.arn
}

output "security_group_id" {
  description = "ID of the security group for frontend ECS tasks"
  value       = aws_security_group.frontend_ecs.id
}

output "cluster_name" {
  description = "Name of the frontend ECS cluster"
  value       = aws_ecs_cluster.frontend.name
}

output "service_name" {
  description = "Name of the frontend ECS service"
  value       = aws_ecs_service.frontend.name
}

output "task_definition_arn" {
  description = "ARN of the frontend task definition"
  value       = aws_ecs_task_definition.frontend.arn
}

output "cloudwatch_log_group" {
  description = "Name of the CloudWatch log group for frontend"
  value       = local.cloudwatch_log_group_name
}

output "execution_role_arn" {
  description = "ARN of the frontend task execution role"
  value       = local.frontend_execution_role_arn
}

output "task_role_arn" {
  description = "ARN of the frontend task role"
  value       = local.frontend_task_role_arn
}