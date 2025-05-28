# outputs.tf file with S3 bucket outputs
# Outputs for the main Terraform configuration

output "api_gateway_url" {
  description = "API Gateway URL"
  value       = module.api_gateway.api_gateway_url
}

output "backend_ecr_repository_url" {
  description = "Backend ECR Repository URL"
  value       = var.skip_ecr_creation ? "${var.aws_account_id}.dkr.ecr.${var.aws_region}.amazonaws.com/${var.app_name}-${var.environment}" : aws_ecr_repository.app[0].repository_url
}

output "frontend_ecr_repository_url" {
  description = "Frontend ECR Repository URL"
  value       = var.skip_ecr_creation ? "${var.aws_account_id}.dkr.ecr.${var.aws_region}.amazonaws.com/${var.app_name}-frontend-${var.environment}" : aws_ecr_repository.frontend[0].repository_url
}

output "backend_load_balancer_dns" {
  description = "Backend ALB DNS Name"
  value       = module.ecs.load_balancer_dns_name
}

output "frontend_load_balancer_dns" {
  description = "Frontend ALB DNS Name"
  value       = module.frontend.load_balancer_dns_name
}

output "vpc_id" {
  description = "ID of the VPC"
  value       = module.vpc.vpc_id
}

output "backend_ecs_cluster_name" {
  description = "Name of the Backend ECS cluster"
  value       = module.ecs.cluster_name
}

output "frontend_ecs_cluster_name" {
  description = "Name of the Frontend ECS cluster"
  value       = module.frontend.cluster_name
}

output "private_subnet_ids" {
  description = "IDs of the private subnets"
  value       = module.vpc.private_subnet_ids
}

output "public_subnet_ids" {
  description = "IDs of the public subnets"
  value       = module.vpc.public_subnet_ids
}

output "database_endpoint" {
  description = "The PostgreSQL database endpoint"
  value       = module.vectordb.cluster_endpoint
}

output "database_name" {
  description = "The PostgreSQL database name"
  value       = module.vectordb.database_name
}

output "database_username" {
  description = "The PostgreSQL master username"
  value       = module.vectordb.master_username
}

# output "database_password_secret" {
#   description = "ARN of the secret containing the database password"
#   value       = module.vectordb.password_secret_arn
#   sensitive   = true
# }

# S3 bucket outputs
output "initialization_bucket_name" {
  description = "Name of the S3 bucket for initialization scripts"
  value       = module.initialization_bucket.bucket_id
}

output "initialization_bucket_arn" {
  description = "ARN of the S3 bucket for initialization scripts"
  value       = module.initialization_bucket.bucket_arn
}

output "initialization_bucket_region" {
  description = "Region where the initialization bucket is located"
  value       = module.initialization_bucket.bucket_region
}
