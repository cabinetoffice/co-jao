# ECS module - outputs.tf
output "cluster_id" {
  description = "ID of the ECS cluster"
  value       = aws_ecs_cluster.main.id
}

output "cluster_name" {
  description = "Name of the ECS cluster"
  value       = aws_ecs_cluster.main.name
}

output "service_name" {
  description = "Name of the ECS service"
  value       = aws_ecs_service.app.name
}

output "task_definition_arn" {
  description = "ARN of the task definition"
  value       = aws_ecs_task_definition.app.arn
}

output "load_balancer_arn" {
  description = "ARN of the load balancer"
  value       = aws_lb.main.arn
}

output "load_balancer_dns_name" {
  description = "DNS name of the load balancer"
  value       = aws_lb.main.dns_name
}

output "target_group_arn" {
  description = "ARN of the target group"
  value       = aws_lb_target_group.app.arn
}

output "security_group_ecs_tasks_id" {
  description = "ID of the ECS tasks security group"
  value       = aws_security_group.ecs_tasks.id
}

output "lb_listener_arn" {
  value       = aws_lb_listener.http.arn
  description = "The ARN of the load balancer listener"
}

output "nlb_arn" {
  description = "ARN of the Network Load Balancer"
  value       = aws_lb.nlb.arn
}

output "nlb_dns_name" {
  description = "DNS name of the Network Load Balancer"
  value       = aws_lb.nlb.dns_name
}

output "nlb_listener_arn" {
  description = "ARN of the NLB listener"
  value       = aws_lb_listener.nlb.arn
}


# Enhanced API monitoring outputs
output "security_group_id" {
  description = "ID of the ECS tasks security group (alias for backward compatibility)"
  value       = aws_security_group.ecs_tasks.id
}

output "cloudwatch_log_group_name" {
  description = "Name of the CloudWatch log group"
  value       = local.cloudwatch_log_group_name
}

output "cloudwatch_log_group_arn" {
  description = "ARN of the CloudWatch log group"
  value       = local.cloudwatch_log_group_arn
}

output "api_dashboard_name" {
  description = "Name of the API CloudWatch dashboard if enabled"
  value       = var.enable_enhanced_monitoring && length(aws_cloudwatch_dashboard.api_monitoring) > 0 ? aws_cloudwatch_dashboard.api_monitoring[0].dashboard_name : null
}

output "api_error_metric_name" {
  description = "Name of the API error metric if enabled"
  value       = var.enable_enhanced_monitoring ? "${local.name}-APIErrors" : null
}

output "api_latency_metric_name" {
  description = "Name of the API latency metric if enabled"
  value       = var.enable_enhanced_monitoring ? "${local.name}-APILatency" : null
}

output "xray_policy_arn" {
  description = "ARN of the X-Ray policy if enabled"
  value       = var.enable_xray_tracing ? aws_iam_policy.xray_access_policy[0].arn : null
}
