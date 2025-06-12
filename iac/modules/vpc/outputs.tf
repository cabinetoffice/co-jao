# VPC module - outputs.tf
output "vpc_id" {
  description = "ID of the VPC"
  value       = local.vpc_id
}

output "private_subnet_ids" {
  description = "IDs of the private subnets"
  value       = aws_subnet.private[*].id
}

output "public_subnet_ids" {
  description = "IDs of the public subnets"
  value       = aws_subnet.public[*].id
}

output "nat_gateway_ids" {
  description = "IDs of the NAT Gateways"
  value       = aws_nat_gateway.nat[*].id
}

output "vpc_cidr_block" {
  description = "CIDR block of the VPC"
  value       = aws_vpc.main.cidr_block
}

output "internet_gateway_id" {
  description = "ID of the Internet Gateway"
  value       = aws_internet_gateway.igw.id
}

output "public_route_table_id" {
  description = "ID of the public route table"
  value       = aws_route_table.public.id
}

output "private_route_table_ids" {
  description = "IDs of the private route tables"
  value       = aws_route_table.private[*].id
}

output "name" {
  description = "The name prefix used for all resources"
  value       = "${var.name_prefix}-${var.environment}"
}

output "azs" {
  description = "List of availability zones used"
  value       = var.azs
}

# VPC Endpoint Outputs
output "ecr_dkr_endpoint_id" {
  description = "ID of the ECR Docker VPC endpoint"
  value       = var.existing_ecr_dkr_endpoint_id != "" ? var.existing_ecr_dkr_endpoint_id : (length(aws_vpc_endpoint.ecr_dkr) > 0 ? aws_vpc_endpoint.ecr_dkr[0].id : null)
}

output "ecr_api_endpoint_id" {
  description = "ID of the ECR API VPC endpoint"
  value       = var.existing_ecr_api_endpoint_id != "" ? var.existing_ecr_api_endpoint_id : (length(aws_vpc_endpoint.ecr_api) > 0 ? aws_vpc_endpoint.ecr_api[0].id : null)
}

output "s3_endpoint_id" {
  description = "ID of the S3 Gateway VPC endpoint"
  value       = var.existing_s3_endpoint_id != "" ? var.existing_s3_endpoint_id : (length(aws_vpc_endpoint.s3) > 0 ? aws_vpc_endpoint.s3[0].id : null)
}

output "logs_endpoint_id" {
  description = "ID of the CloudWatch Logs VPC endpoint"
  value       = var.existing_logs_endpoint_id != "" ? var.existing_logs_endpoint_id : (length(aws_vpc_endpoint.logs) > 0 ? aws_vpc_endpoint.logs[0].id : null)
}

output "vpc_endpoints_security_group_id" {
  description = "ID of the security group used by VPC endpoints"
  value       = length(aws_security_group.vpc_endpoints) > 0 ? aws_security_group.vpc_endpoints[0].id : null
}

output "vpc_endpoints_created" {
  description = "Map of which VPC endpoints were created vs existing"
  value = {
    ecr_dkr_created = length(aws_vpc_endpoint.ecr_dkr) > 0
    ecr_api_created = length(aws_vpc_endpoint.ecr_api) > 0
    s3_created      = length(aws_vpc_endpoint.s3) > 0
    logs_created    = length(aws_vpc_endpoint.logs) > 0
    ecr_dkr_existing = var.existing_ecr_dkr_endpoint_id != ""
    ecr_api_existing = var.existing_ecr_api_endpoint_id != ""
    s3_existing      = var.existing_s3_endpoint_id != ""
    logs_existing    = var.existing_logs_endpoint_id != ""
  }
}