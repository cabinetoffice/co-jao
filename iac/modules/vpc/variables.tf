# VPC module - variables.tf
variable "name_prefix" {
  description = "Prefix to use for all resource names"
  type        = string
}

variable "environment" {
  description = "Environment name (e.g. dev, staging, prod)"
  type        = string
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
}

variable "azs" {
  description = "List of availability zones to use"
  type        = list(string)
}

variable "private_subnet_cidrs" {
  description = "CIDR blocks for private subnets"
  type        = list(string)
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for public subnets"
  type        = list(string)
}

variable "tags" {
  description = "Additional tags to apply to all resources"
  type        = map(string)
  default     = {}
}

# VPC Endpoints Configuration
variable "create_vpc_endpoints" {
  description = "Whether to create VPC endpoints"
  type        = bool
  default     = true
}

variable "create_ecr_dkr_endpoint" {
  description = "Whether to create ECR Docker Registry VPC endpoint"
  type        = bool
  default     = true
}

variable "create_ecr_api_endpoint" {
  description = "Whether to create ECR API VPC endpoint"
  type        = bool
  default     = true
}

variable "create_s3_endpoint" {
  description = "Whether to create S3 Gateway VPC endpoint"
  type        = bool
  default     = true
}

variable "create_logs_endpoint" {
  description = "Whether to create CloudWatch Logs VPC endpoint"
  type        = bool
  default     = true
}

variable "existing_ecr_dkr_endpoint_id" {
  description = "ID of existing ECR Docker Registry VPC endpoint (if any)"
  type        = string
  default     = ""
}

variable "existing_ecr_api_endpoint_id" {
  description = "ID of existing ECR API VPC endpoint (if any)"
  type        = string
  default     = ""
}

variable "existing_s3_endpoint_id" {
  description = "ID of existing S3 Gateway VPC endpoint (if any)"
  type        = string
  default     = ""
}

variable "existing_logs_endpoint_id" {
  description = "ID of existing CloudWatch Logs VPC endpoint (if any)"
  type        = string
  default     = ""
}

variable "vpc_tags" {
  description = "Additional tags for the VPC"
  type        = map(string)
  default     = {}
}

variable "private_subnet_tags" {
  description = "Additional tags for private subnets"
  type        = map(string)
  default     = {}
}



variable "public_subnet_tags" {
  description = "Additional tags for the public subnets"
  type        = map(string)
  default     = {}
}

variable "enable_nat_gateway" {
  description = "Should be true if you want to provision NAT Gateways"
  type        = bool
  default     = true
}

variable "single_nat_gateway" {
  description = "Should be true if you want to provision a single shared NAT Gateway across all private subnets"
  type        = bool
  default     = false
}