# API Gateway module - outputs.tf
output "api_gateway_id" {
  description = "ID of the API Gateway"
  value       = aws_api_gateway_rest_api.main.id
}

output "api_gateway_arn" {
  description = "ARN of the API Gateway"
  value       = aws_api_gateway_rest_api.main.arn
}

output "api_gateway_url" {
  description = "URL of the API Gateway"
  value       = "${aws_api_gateway_stage.main.invoke_url}/"
}

output "vpc_link_id" {
  description = "ID of the VPC Link for NLB connection"
  value       = aws_api_gateway_vpc_link.main.id
}

output "stage_name" {
  description = "Name of the API Gateway stage"
  value       = aws_api_gateway_stage.main.stage_name
}

output "stage_url" {
  description = "URL of the API Gateway stage"
  value       = aws_api_gateway_stage.main.invoke_url
}

# API Key and Usage Plan outputs
output "api_keys" {
  description = "Map of API key names to their IDs"
  value       = local.create_api_keys ? { for i, key in aws_api_gateway_api_key.api_keys : var.api_keys[i].name => key.id } : {}
  sensitive   = true
}

# output "usage_plans" {
#   description = "Map of usage plan names to their IDs"
#   value       = var.enable_api_keys ? { for i, plan in aws_api_gateway_usage_plan.usage_plans : var.usage_plans[i].name => plan.id } : {}
# }

output "api_keys_api_url" {
  description = "URL of the API Keys validation API if enabled"
  value       = local.create_api_keys && length(aws_api_gateway_stage.api_keys_api) > 0 ? "${aws_api_gateway_stage.api_keys_api[0].invoke_url}/validate" : null
}

output "cloudwatch_dashboard_name" {
  description = "Name of the CloudWatch dashboard for API metrics"
  value       = local.create_detailed_metrics && length(aws_cloudwatch_dashboard.api_dashboard) > 0 ? aws_cloudwatch_dashboard.api_dashboard["main"].dashboard_name : null
}

output "resources" {
  description = "Map of resource paths to their IDs"
  value       = merge(
    { "/{proxy+}" = aws_api_gateway_resource.proxy.id },
    { for i, resource in aws_api_gateway_resource.routes : local.routes[i + 1].path => resource.id }
  )
}
