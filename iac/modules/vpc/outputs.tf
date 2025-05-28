# VPC module - outputs.tf
output "vpc_id" {
  description = "ID of the VPC"
  value       = local.vpc_id
}

output "private_subnet_ids" {
  description = "IDs of the private subnets"
  value       = local.have_vpc ? aws_subnet.private[*].id : []
}

output "public_subnet_ids" {
  description = "IDs of the public subnets"
  value       = local.have_vpc ? aws_subnet.public[*].id : []
}

output "nat_gateway_ids" {
  description = "IDs of the NAT Gateways"
  value       = local.have_vpc ? aws_nat_gateway.nat[*].id : []
}

output "vpc_cidr_block" {
  description = "CIDR block of the VPC"
  value       = local.have_vpc ? (var.skip_vpc_creation ? data.aws_vpc.existing[0].cidr_block : aws_vpc.main[0].cidr_block) : ""
}

output "internet_gateway_id" {
  description = "ID of the Internet Gateway"
  value       = local.have_vpc && length(aws_internet_gateway.igw) > 0 ? aws_internet_gateway.igw[0].id : ""
}

output "public_route_table_id" {
  description = "ID of the public route table"
  value       = local.have_vpc && length(aws_route_table.public) > 0 ? aws_route_table.public[0].id : ""
}

output "private_route_table_ids" {
  description = "IDs of the private route tables"
  value       = local.have_vpc ? aws_route_table.private[*].id : []
}

output "name" {
  description = "The name prefix used for all resources"
  value       = local.name
}

output "azs" {
  description = "List of availability zones used"
  value       = var.azs
}