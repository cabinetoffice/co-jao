terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 4.0"
    }
  }
  required_version = ">= 1.0"
}

# Configure AWS Provider for LocalStack
provider "aws" {
  access_key                  = "test"
  secret_key                  = "test"
  region                      = var.aws_region
  s3_use_path_style           = true
  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_requesting_account_id  = true

  # LocalStack endpoints
  endpoints {
    apigateway       = "http://localhost:4566"
    apigatewayv2     = "http://localhost:4566"
    cloudformation   = "http://localhost:4566"
    cloudwatch       = "http://localhost:4566"
    dynamodb         = "http://localhost:4566"
    ec2              = "http://localhost:4566"
    ecr              = "http://localhost:4566"
    ecs              = "http://localhost:4566"
    iam              = "http://localhost:4566"
    lambda           = "http://localhost:4566"
    route53          = "http://localhost:4566"
    s3               = "http://localhost:4566"
    secretsmanager   = "http://localhost:4566"
    ses              = "http://localhost:4566"
    sns              = "http://localhost:4566"
    sqs              = "http://localhost:4566"
    ssm              = "http://localhost:4566"
    stepfunctions    = "http://localhost:4566"
    sts              = "http://localhost:4566"
  }
}

locals {
  name = "${var.app_name}-${var.environment}"
  common_tags = {
    Name        = local.name
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

# ECR Repository for Docker image
resource "aws_ecr_repository" "app_local" {
  name                 = "${var.app_name}-${var.environment}"
  image_tag_mutability = "MUTABLE"
  
  tags = local.common_tags
}

# Simplified VPC for LocalStack
resource "aws_vpc" "main_local" {
  cidr_block         = var.vpc_cidr
  enable_dns_support = true

  tags = merge(
    local.common_tags,
    { Name = "${local.name}-vpc" }
  )
}

# Public subnets
resource "aws_subnet" "public_local" {
  count             = length(var.public_subnet_cidrs)
  vpc_id            = aws_vpc.main_local.id
  cidr_block        = var.public_subnet_cidrs[count.index]
  availability_zone = var.availability_zones[count.index]

  tags = merge(
    local.common_tags,
    { Name = "${local.name}-public-subnet-${count.index}" }
  )
}

# Private subnets
resource "aws_subnet" "private_local" {
  count             = length(var.private_subnet_cidrs)
  vpc_id            = aws_vpc.main_local.id
  cidr_block        = var.private_subnet_cidrs[count.index]
  availability_zone = var.availability_zones[count.index]

  tags = merge(
    local.common_tags,
    { Name = "${local.name}-private-subnet-${count.index}" }
  )
}

# Internet Gateway
resource "aws_internet_gateway" "igw_local" {
  vpc_id = aws_vpc.main_local.id

  tags = merge(
    local.common_tags,
    { Name = "${local.name}-igw" }
  )
}

# Simplified ECS cluster for LocalStack
resource "aws_ecs_cluster" "main_local" {
  name = "${local.name}-cluster"

  tags = merge(
    local.common_tags,
    { Name = "${local.name}-cluster" }
  )
}

# Simplified security group for container
resource "aws_security_group" "ecs_tasks_local" {
  name        = "${local.name}-ecs-tasks-sg"
  description = "Allow container traffic"
  vpc_id      = aws_vpc.main_local.id

  ingress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(
    local.common_tags,
    { Name = "${local.name}-ecs-tasks-sg" }
  )
}

# Simplified ALB for LocalStack
resource "aws_lb" "main_local" {
  name               = "${local.name}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.ecs_tasks_local.id]
  subnets            = aws_subnet.private_local.*.id

  tags = merge(
    local.common_tags,
    { Name = "${local.name}-alb" }
  )
}

# Target group for the ALB
resource "aws_lb_target_group" "app_local" {
  name        = "${local.name}-tg"
  port        = var.container_port
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main_local.id
  target_type = "ip"
  
  health_check {
    path                = "/health"
    protocol            = "HTTP"
    matcher             = "200"
    interval            = 30
    timeout             = 5
    healthy_threshold   = 3
    unhealthy_threshold = 3
  }
  
  tags = merge(
    local.common_tags,
    { Name = "${local.name}-tg" }
  )
}

# ALB listener
resource "aws_lb_listener" "http_local" {
  load_balancer_arn = aws_lb.main_local.arn
  port              = 80
  protocol          = "HTTP"
  
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.app_local.arn
  }
}

# VPC Link for API Gateway v2
resource "aws_apigatewayv2_vpc_link" "main_local" {
  name               = "${local.name}-vpc-link"
  subnet_ids         = aws_subnet.private_local.*.id
  security_group_ids = [aws_security_group.ecs_tasks_local.id]
  
  tags = merge(
    local.common_tags,
    { Name = "${local.name}-vpc-link" }
  )
}

# HTTP API Gateway (v2)
resource "aws_apigatewayv2_api" "api_v2_local" {
  name          = "${local.name}-http-api"
  protocol_type = "HTTP"
  
  cors_configuration {
    allow_origins = ["*"]
    allow_methods = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    allow_headers = ["Content-Type", "Authorization", "X-Amz-Date", "X-Api-Key"]
    max_age       = 300
  }
  
  tags = merge(
    local.common_tags,
    { Name = "${local.name}-http-api" }
  )
}

# HTTP API Stage
resource "aws_apigatewayv2_stage" "api_v2_stage_local" {
  api_id      = aws_apigatewayv2_api.api_v2_local.id
  name        = "local"
  auto_deploy = true
  
  tags = merge(
    local.common_tags,
    { Name = "${local.name}-http-api-stage" }
  )
}

# HTTP API Integration
resource "aws_apigatewayv2_integration" "api_v2_integration_local" {
  api_id             = aws_apigatewayv2_api.api_v2_local.id
  integration_type   = "HTTP_PROXY"
  integration_method = "ANY"
  integration_uri    = "http://localhost:5000/{proxy}"
  connection_type    = "VPC_LINK"
  connection_id      = aws_apigatewayv2_vpc_link.main_local.id
  
  request_parameters = {
    "overwrite:path" = "$request.path"
  }
}

# HTTP API Routes
resource "aws_apigatewayv2_route" "api_v2_route_proxy_local" {
  api_id    = aws_apigatewayv2_api.api_v2_local.id
  route_key = "ANY /{proxy+}"
  target    = "integrations/${aws_apigatewayv2_integration.api_v2_integration_local.id}"
}

resource "aws_apigatewayv2_route" "api_v2_route_health_local" {
  api_id    = aws_apigatewayv2_api.api_v2_local.id
  route_key = "GET /health"
  target    = "integrations/${aws_apigatewayv2_integration.api_v2_integration_local.id}"
}

resource "aws_apigatewayv2_route" "api_v2_route_hello_local" {
  api_id    = aws_apigatewayv2_api.api_v2_local.id
  route_key = "GET /api/hello"
  target    = "integrations/${aws_apigatewayv2_integration.api_v2_integration_local.id}"
}

resource "aws_apigatewayv2_route" "api_v2_route_data_local" {
  api_id    = aws_apigatewayv2_api.api_v2_local.id
  route_key = "POST /api/data"
  target    = "integrations/${aws_apigatewayv2_integration.api_v2_integration_local.id}"
}

# REST API Gateway (v1) - Fallback for compatibility
resource "aws_api_gateway_rest_api" "api_local" {
  name = "${local.name}-api"
  
  tags = merge(
    local.common_tags,
    { Name = "${local.name}-rest-api" }
  )
}

# API Gateway resource - api
resource "aws_api_gateway_resource" "api_resource_local" {
  rest_api_id = aws_api_gateway_rest_api.api_local.id
  parent_id   = aws_api_gateway_rest_api.api_local.root_resource_id
  path_part   = "api"
}

# API Gateway resource - hello
resource "aws_api_gateway_resource" "hello_resource_local" {
  rest_api_id = aws_api_gateway_rest_api.api_local.id
  parent_id   = aws_api_gateway_resource.api_resource_local.id
  path_part   = "hello"
}

# API Gateway resource - data
resource "aws_api_gateway_resource" "data_resource_local" {
  rest_api_id = aws_api_gateway_rest_api.api_local.id
  parent_id   = aws_api_gateway_resource.api_resource_local.id
  path_part   = "data"
}

# Health check resource
resource "aws_api_gateway_resource" "health_resource_local" {
  rest_api_id = aws_api_gateway_rest_api.api_local.id
  parent_id   = aws_api_gateway_rest_api.api_local.root_resource_id
  path_part   = "health"
}

# GET /health method
resource "aws_api_gateway_method" "health_method_local" {
  rest_api_id   = aws_api_gateway_rest_api.api_local.id
  resource_id   = aws_api_gateway_resource.health_resource_local.id
  http_method   = "GET"
  authorization = "NONE"
}

# GET /api/hello method
resource "aws_api_gateway_method" "hello_method_local" {
  rest_api_id   = aws_api_gateway_rest_api.api_local.id
  resource_id   = aws_api_gateway_resource.hello_resource_local.id
  http_method   = "GET"
  authorization = "NONE"
}

# POST /api/data method
resource "aws_api_gateway_method" "data_method_local" {
  rest_api_id   = aws_api_gateway_rest_api.api_local.id
  resource_id   = aws_api_gateway_resource.data_resource_local.id
  http_method   = "POST"
  authorization = "NONE"
}

# HTTP_PROXY integrations to point directly to the container
resource "aws_api_gateway_integration" "health_integration_local" {
  rest_api_id = aws_api_gateway_rest_api.api_local.id
  resource_id = aws_api_gateway_resource.health_resource_local.id
  http_method = aws_api_gateway_method.health_method_local.http_method
  type        = "HTTP_PROXY"
  uri         = "http://localhost:5000/health"
  integration_http_method = "GET"
}

resource "aws_api_gateway_integration" "hello_integration_local" {
  rest_api_id = aws_api_gateway_rest_api.api_local.id
  resource_id = aws_api_gateway_resource.hello_resource_local.id
  http_method = aws_api_gateway_method.hello_method_local.http_method
  type        = "HTTP_PROXY"
  uri         = "http://localhost:5000/api/hello"
  integration_http_method = "GET"
}

resource "aws_api_gateway_integration" "data_integration_local" {
  rest_api_id = aws_api_gateway_rest_api.api_local.id
  resource_id = aws_api_gateway_resource.data_resource_local.id
  http_method = aws_api_gateway_method.data_method_local.http_method
  type        = "HTTP_PROXY"
  uri         = "http://localhost:5000/api/data"
  integration_http_method = "POST"
}

# API Gateway deployment
resource "aws_api_gateway_deployment" "api_deployment_local" {
  rest_api_id = aws_api_gateway_rest_api.api_local.id

  depends_on = [
    aws_api_gateway_integration.hello_integration_local,
    aws_api_gateway_integration.data_integration_local,
    aws_api_gateway_integration.health_integration_local
  ]

  lifecycle {
    create_before_destroy = true
  }
}

# API Gateway stage
resource "aws_api_gateway_stage" "api_stage_local" {
  deployment_id = aws_api_gateway_deployment.api_deployment_local.id
  rest_api_id   = aws_api_gateway_rest_api.api_local.id
  stage_name    = "local"
}

# Outputs
output "localstack_api_v2_url" {
  description = "LocalStack HTTP API Gateway URL (v2)"
  value       = "http://localhost:4566/apis/${aws_apigatewayv2_api.api_v2_local.id}"
}

output "localstack_api_url" {
  description = "LocalStack REST API Gateway URL (v1)"
  value       = "http://localhost:4566/restapis/${aws_api_gateway_rest_api.api_local.id}/local/_user_request_"
}

output "localstack_ecr_url" {
  description = "LocalStack ECR Repository URL"
  value       = aws_ecr_repository.app_local.repository_url
}