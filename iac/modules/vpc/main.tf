# VPC module - main.tf
locals {
  # Resource naming
  name = "${var.name_prefix}-${var.environment}"

  # Common tags for all resources
  common_tags = merge(
    var.tags,
    {
      Environment = var.environment
      ManagedBy   = "terraform"
      Name        = local.name
    }
  )
  
  vpc_id = aws_vpc.main.id
  
  # Determine the number of NAT gateways to create
  nat_gateway_count = var.enable_nat_gateway ? (var.single_nat_gateway ? 1 : length(var.public_subnet_cidrs)) : 0
}

# VPC
resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = merge(
    local.common_tags,
    var.vpc_tags,
    {
      Name = "${var.name_prefix}-${var.environment}-vpc"
    }
  )
}

# Data source to fetch existing VPC if skipping creation


# Public subnets
resource "aws_subnet" "public" {
  count                   = length(var.public_subnet_cidrs)
  vpc_id                  = local.vpc_id
  cidr_block              = var.public_subnet_cidrs[count.index]
  availability_zone       = var.azs[count.index]
  map_public_ip_on_launch = true

  tags = merge(
    local.common_tags,
    var.public_subnet_tags,
    {
      Name = "${local.name}-public-subnet-${var.azs[count.index]}"
      Tier = "Public"
    }
  )
}

# Private subnets
resource "aws_subnet" "private" {
  count             = length(var.private_subnet_cidrs)
  vpc_id            = local.vpc_id
  cidr_block        = var.private_subnet_cidrs[count.index]
  availability_zone = var.azs[count.index]

  tags = merge(
    local.common_tags,
    var.private_subnet_tags,
    {
      Name = "${local.name}-private-subnet-${var.azs[count.index]}"
      Tier = "Private"
    }
  )
}

# Internet Gateway
resource "aws_internet_gateway" "igw" {
  vpc_id = local.vpc_id

  tags = merge(
    local.common_tags,
    {
      Name = "${local.name}-igw"
    }
  )
}

# Elastic IP for NAT Gateway
resource "aws_eip" "nat" {
  count      = local.nat_gateway_count
  depends_on = [aws_internet_gateway.igw]

  tags = merge(
    local.common_tags,
    {
      Name = "${local.name}-eip-${count.index + 1}"
    }
  )
}

# NAT Gateway
resource "aws_nat_gateway" "nat" {
  count         = local.nat_gateway_count
  allocation_id = aws_eip.nat[count.index].id
  subnet_id     = aws_subnet.public[count.index].id
  depends_on    = [aws_internet_gateway.igw]

  tags = merge(
    local.common_tags,
    {
      Name = "${local.name}-nat-${count.index + 1}"
    }
  )
}

# Route tables for public subnets
resource "aws_route_table" "public" {
  vpc_id = local.vpc_id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.igw.id
  }

  tags = merge(
    local.common_tags,
    {
      Name = "${local.name}-public-rt"
    }
  )
}

# Route table for private subnets
resource "aws_route_table" "private" {
  count  = var.single_nat_gateway ? 1 : length(var.private_subnet_cidrs)
  vpc_id = local.vpc_id

  dynamic "route" {
    for_each = var.enable_nat_gateway ? [1] : []
    content {
      cidr_block     = "0.0.0.0/0"
      nat_gateway_id = var.single_nat_gateway ? aws_nat_gateway.nat[0].id : aws_nat_gateway.nat[count.index].id
    }
  }

  tags = merge(
    local.common_tags,
    {
      Name = "${var.name_prefix}-${var.environment}-private-rt-${count.index + 1}"
    }
  )
}

# Associate public subnets with public route table
# Route table association for public subnets
resource "aws_route_table_association" "public" {
  count          = length(var.public_subnet_cidrs)
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

# Associate private subnets with private route tables
resource "aws_route_table_association" "private" {
  count          = length(var.private_subnet_cidrs)
  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = var.single_nat_gateway ? aws_route_table.private[0].id : aws_route_table.private[count.index].id
}

# Data source for current AWS region
data "aws_region" "current" {}

# Security group for VPC endpoints
resource "aws_security_group" "vpc_endpoints" {
  count       = var.create_vpc_endpoints ? 1 : 0
  name        = "${local.name}-vpc-endpoints-sg"
  description = "Security group for VPC endpoints"
  vpc_id      = local.vpc_id

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
    description = "HTTPS from VPC"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "All outbound traffic"
  }

  tags = merge(
    local.common_tags,
    {
      Name = "${local.name}-vpc-endpoints-sg"
    }
  )
}

# Data sources for existing VPC endpoints
data "aws_vpc_endpoint" "existing_ecr_dkr" {
  count        = var.existing_ecr_dkr_endpoint_id != "" ? 1 : 0
  vpc_id       = local.vpc_id
  service_name = "com.amazonaws.${data.aws_region.current.name}.ecr.dkr"
}

data "aws_vpc_endpoint" "existing_ecr_api" {
  count        = var.existing_ecr_api_endpoint_id != "" ? 1 : 0
  vpc_id       = local.vpc_id
  service_name = "com.amazonaws.${data.aws_region.current.name}.ecr.api"
}

data "aws_vpc_endpoint" "existing_s3" {
  count        = var.existing_s3_endpoint_id != "" ? 1 : 0
  vpc_id       = local.vpc_id
  service_name = "com.amazonaws.${data.aws_region.current.name}.s3"
}

data "aws_vpc_endpoint" "existing_logs" {
  count        = var.existing_logs_endpoint_id != "" ? 1 : 0
  vpc_id       = local.vpc_id
  service_name = "com.amazonaws.${data.aws_region.current.name}.logs"
}

# VPC Endpoint for ECR Docker Registry
resource "aws_vpc_endpoint" "ecr_dkr" {
  count               = var.create_vpc_endpoints && var.create_ecr_dkr_endpoint && var.existing_ecr_dkr_endpoint_id == "" ? 1 : 0
  vpc_id              = local.vpc_id
  service_name        = "com.amazonaws.${data.aws_region.current.name}.ecr.dkr"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = aws_subnet.private[*].id
  security_group_ids  = [aws_security_group.vpc_endpoints[0].id]
  private_dns_enabled = true

  tags = merge(
    local.common_tags,
    {
      Name = "${local.name}-ecr-dkr-endpoint"
    }
  )
}

# VPC Endpoint for ECR API - Required for authentication and repository management
resource "aws_vpc_endpoint" "ecr_api" {
  count               = var.create_vpc_endpoints && var.create_ecr_api_endpoint && var.existing_ecr_api_endpoint_id == "" ? 1 : 0
  vpc_id              = local.vpc_id
  service_name        = "com.amazonaws.${data.aws_region.current.name}.ecr.api"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = aws_subnet.private[*].id
  security_group_ids  = [aws_security_group.vpc_endpoints[0].id]
  private_dns_enabled = true

  tags = merge(
    local.common_tags,
    {
      Name = "${local.name}-ecr-api-endpoint"
    }
  )
}

# VPC Endpoint for S3 - Required for ECR image layers (Gateway endpoint for cost efficiency)
resource "aws_vpc_endpoint" "s3" {
  count             = var.create_vpc_endpoints && var.create_s3_endpoint && var.existing_s3_endpoint_id == "" ? 1 : 0
  vpc_id            = local.vpc_id
  service_name      = "com.amazonaws.${data.aws_region.current.name}.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = aws_route_table.private[*].id

  tags = merge(
    local.common_tags,
    {
      Name = "${local.name}-s3-endpoint"
    }
  )
}

# VPC Endpoint for CloudWatch Logs - Optional but recommended for container logging
resource "aws_vpc_endpoint" "logs" {
  count               = var.create_vpc_endpoints && var.create_logs_endpoint && var.existing_logs_endpoint_id == "" ? 1 : 0
  vpc_id              = local.vpc_id
  service_name        = "com.amazonaws.${data.aws_region.current.name}.logs"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = aws_subnet.private[*].id
  security_group_ids  = [aws_security_group.vpc_endpoints[0].id]
  private_dns_enabled = true

  tags = merge(
    local.common_tags,
    {
      Name = "${local.name}-logs-endpoint"
    }
  )
}
