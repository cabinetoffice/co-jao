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
  
  # Use existing VPC ID if skipping creation and VPC ID provided, otherwise use created VPC
  vpc_id = var.skip_vpc_creation && var.existing_vpc_id != "" ? data.aws_vpc.existing[0].id : (length(aws_vpc.main) > 0 ? aws_vpc.main[0].id : "")
  
  # Determine if we have a valid VPC (either created or existing)
  have_vpc = (!var.skip_vpc_creation) || (var.skip_vpc_creation && var.existing_vpc_id != "")
  
  # Determine the number of NAT gateways to create
  nat_gateway_count = var.enable_nat_gateway ? (var.single_nat_gateway ? 1 : length(var.public_subnet_cidrs)) : 0
}

# VPC
resource "aws_vpc" "main" {
  count = var.skip_vpc_creation ? 0 : 1
  
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = merge(
    local.common_tags,
    var.vpc_tags,
    {
      Name = "${local.name}-vpc"
    }
  )
}

# Data source to fetch existing VPC if skipping creation
data "aws_vpc" "existing" {
  count = var.skip_vpc_creation && var.existing_vpc_id != "" ? 1 : 0
  id    = var.existing_vpc_id
}

# Public subnets
resource "aws_subnet" "public" {
  count                   = local.have_vpc ? length(var.public_subnet_cidrs) : 0
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
  count             = local.have_vpc ? length(var.private_subnet_cidrs) : 0
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
  count  = local.have_vpc ? 1 : 0
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
  count      = local.have_vpc ? local.nat_gateway_count : 0
  depends_on = [aws_internet_gateway.igw[0]]

  tags = merge(
    local.common_tags,
    {
      Name = "${local.name}-eip-${count.index + 1}"
    }
  )
}

# NAT Gateway
# NAT gateways - one per public subnet or just one if single_nat_gateway is true
resource "aws_nat_gateway" "nat" {
  count         = local.have_vpc ? local.nat_gateway_count : 0
  allocation_id = aws_eip.nat[count.index].id
  subnet_id     = aws_subnet.public[count.index].id
  depends_on    = [aws_internet_gateway.igw[0]]

  tags = merge(
    local.common_tags,
    {
      Name = "${local.name}-nat-${count.index + 1}"
    }
  )
}

# Route table for public subnets
resource "aws_route_table" "public" {
  count  = local.have_vpc ? 1 : 0
  vpc_id = local.vpc_id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.igw[0].id
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
  count  = local.have_vpc ? (var.single_nat_gateway ? 1 : length(var.private_subnet_cidrs)) : 0
  vpc_id = local.vpc_id

  dynamic "route" {
    for_each = var.enable_nat_gateway && local.have_vpc ? [1] : []
    content {
      cidr_block     = "0.0.0.0/0"
      nat_gateway_id = var.single_nat_gateway ? aws_nat_gateway.nat[0].id : (count.index < length(aws_nat_gateway.nat) ? aws_nat_gateway.nat[count.index].id : aws_nat_gateway.nat[0].id)
    }
  }

  tags = merge(
    local.common_tags,
    {
      Name = "${local.name}-private-rt-${count.index + 1}"
    }
  )
}

# Associate public subnets with public route table
resource "aws_route_table_association" "public" {
  count          = local.have_vpc ? length(var.public_subnet_cidrs) : 0
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public[0].id
}

# Associate private subnets with private route tables
resource "aws_route_table_association" "private" {
  count          = local.have_vpc ? length(var.private_subnet_cidrs) : 0
  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = var.single_nat_gateway ? aws_route_table.private[0].id : aws_route_table.private[count.index].id
}
