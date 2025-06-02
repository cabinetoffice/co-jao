# Frontend ECS Module
# This module sets up the frontend container in ECS with load balancer

locals {
  name_prefix                  = "${var.name_prefix}-frontend-${var.environment}"
  container_name               = "${var.name_prefix}-frontend"
  container_port               = var.container_port
  region                       = data.aws_region.current.name
  frontend_execution_role_arn  = var.skip_iam_role_creation ? var.existing_execution_role_arn : (length(aws_iam_role.frontend_execution) > 0 ? aws_iam_role.frontend_execution[0].arn : "")
  frontend_task_role_arn       = var.skip_iam_role_creation ? var.existing_task_role_arn : (length(aws_iam_role.frontend_task) > 0 ? aws_iam_role.frontend_task[0].arn : "")
  frontend_execution_role_name = var.skip_iam_role_creation ? element(split("/", var.existing_execution_role_arn), 1) : (length(aws_iam_role.frontend_execution) > 0 ? aws_iam_role.frontend_execution[0].name : "")

  # Use specified log group name if provided, otherwise use default pattern
  log_group_name = var.existing_log_group_name != "" ? var.existing_log_group_name : "/ecs/${local.name_prefix}"

  # When skipping creation, use the explicit name, otherwise use the created resource
  cloudwatch_log_group_name = var.skip_cloudwatch_creation ? local.log_group_name : aws_cloudwatch_log_group.frontend[0].name

  # When skipping creation and using explicit name, use the data source if available
  cloudwatch_log_group_arn = var.skip_cloudwatch_creation ? (
    length(data.aws_cloudwatch_log_group.existing_frontend) > 0 ? data.aws_cloudwatch_log_group.existing_frontend[0].arn : ""
  ) : aws_cloudwatch_log_group.frontend[0].arn

  tags = merge(
    var.tags,
    {
      Name        = local.name_prefix
      Environment = var.environment
    }
  )

  container_definitions = jsonencode(concat(
    [
      {
        name      = local.container_name
        image     = "${var.ecr_repository_url}:latest"
        essential = true
        portMappings = [
          {
            containerPort = var.container_port
            hostPort      = var.container_port
            protocol      = "tcp"
          }
        ]
        environment = concat(
          [
            for key, value in var.environment_variables : {
              name  = key
              value = value
            }
          ],
          var.enable_enhanced_monitoring ? [
            {
              name  = "ENABLE_METRICS"
              value = "true"
            },
            {
              name  = "LOG_LEVEL"
              value = "info"
            }
          ] : []
        )
        healthCheck = {
          command     = ["CMD-SHELL", "curl -f http://localhost:${var.container_port}${var.health_check_path} || exit 1"]
          interval    = 30
          timeout     = 5
          retries     = 3
          startPeriod = 60
        }
        logConfiguration = {
          logDriver = "awslogs"
          options = {
            "awslogs-group"         = local.cloudwatch_log_group_name
            "awslogs-region"        = data.aws_region.current.name
            "awslogs-stream-prefix" = "xray"
          }
        }
        dependsOn = var.enable_xray_tracing ? [
          {
            containerName = "xray-daemon"
            condition     = "START"
          }
        ] : null
      }
    ],
    var.enable_xray_tracing ? [
      {
        name      = "xray-daemon"
        image     = "amazon/aws-xray-daemon:latest"
        essential = true
        portMappings = [
          {
            containerPort = 2000
            hostPort      = 2000
            protocol      = "udp"
          }
        ]
        logConfiguration = {
          logDriver = "awslogs"
          options = {
            "awslogs-group"         = local.cloudwatch_log_group_name
            "awslogs-region"        = data.aws_region.current.name
            "awslogs-stream-prefix" = "ecs"
          }
        }
      }
    ] : []
  ))
}

data "aws_region" "current" {}

# ECS cluster for frontend service
resource "aws_ecs_cluster" "frontend" {
  name = "${local.name_prefix}-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  dynamic "configuration" {
    for_each = var.enable_enhanced_monitoring ? [1] : []
    content {
      execute_command_configuration {
        logging = "OVERRIDE"
        log_configuration {
          cloud_watch_log_group_name = local.cloudwatch_log_group_name
        }
      }
    }
  }

  tags = local.tags
}

# CloudWatch Log Group for frontend
resource "aws_cloudwatch_log_group" "frontend" {
  count             = var.skip_cloudwatch_creation ? 0 : 1
  name              = local.log_group_name
  retention_in_days = var.logs_retention_in_days

  tags = local.tags
}

# Data source to read existing CloudWatch log group if skipping creation
data "aws_cloudwatch_log_group" "existing_frontend" {
  count = var.skip_cloudwatch_creation && var.existing_log_group_name != "" ? 1 : 0
  name  = var.existing_log_group_name != "" ? var.existing_log_group_name : "/ecs/${local.name_prefix}"
}

# Security Group for the Load Balancer
resource "aws_security_group" "frontend_lb" {
  name        = "${local.name_prefix}-lb-sg"
  description = "Security group for frontend load balancer"
  vpc_id      = var.vpc_id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow HTTP traffic"
  }

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow HTTPS traffic"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all outbound traffic"
  }

  tags = local.tags
}

# Security Group for ECS Tasks
resource "aws_security_group" "frontend_ecs" {
  name        = "${local.name_prefix}-ecs-sg"
  description = "Security group for frontend ECS tasks"
  vpc_id      = var.vpc_id

  ingress {
    from_port       = var.container_port
    to_port         = var.container_port
    protocol        = "tcp"
    security_groups = [aws_security_group.frontend_lb.id]
    description     = "Allow traffic from ALB"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all outbound traffic"
  }

  tags = local.tags
}

# Application Load Balancer for frontend
resource "aws_lb" "frontend" {
  name               = "${local.name_prefix}-alb"
  internal           = var.internal_lb
  load_balancer_type = "application"
  security_groups    = [aws_security_group.frontend_lb.id]
  subnets            = var.internal_lb ? var.private_subnet_ids : var.public_subnet_ids

  enable_deletion_protection = var.environment == "prod"

  tags = local.tags
}

# Target Group for frontend
resource "aws_lb_target_group" "frontend" {
  name        = "${local.name_prefix}-tg"
  port        = var.container_port
  protocol    = "HTTP"
  vpc_id      = var.vpc_id
  target_type = "ip"

  health_check {
    path                = var.health_check_path
    interval            = 30
    timeout             = 5
    healthy_threshold   = 3
    unhealthy_threshold = 3
    matcher             = "200"
  }

  tags = local.tags
}

# HTTP Listener
resource "aws_lb_listener" "frontend_http" {
  load_balancer_arn = aws_lb.frontend.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.frontend.arn
  }

  tags = local.tags
}

# ECS Task Execution Role
resource "aws_iam_role" "frontend_execution" {
  count = var.skip_iam_role_creation ? 0 : 1
  name  = "${local.name_prefix}-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })

  tags = local.tags
}

# ECS Task Role
resource "aws_iam_role" "frontend_task" {
  count = var.skip_iam_role_creation ? 0 : 1
  name  = "${local.name_prefix}-task-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })

  tags = local.tags
}


# Attach policies to the execution role
resource "aws_iam_role_policy_attachment" "frontend_execution" {
  count      = var.skip_iam_role_creation ? 0 : 1
  role       = aws_iam_role.frontend_execution[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# Task Definition for frontend
resource "aws_ecs_task_definition" "frontend" {
  family                   = "${local.name_prefix}-task"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.cpu
  memory                   = var.memory
  execution_role_arn       = local.frontend_execution_role_arn
  task_role_arn            = local.frontend_task_role_arn

  container_definitions = jsonencode([
    {
      name      = local.container_name
      image     = var.ecr_repository_url
      essential = true
      environment = [
        for key, value in var.environment_variables : {
          name  = key
          value = value
        }
      ]
      portMappings = [
        {
          containerPort = var.container_port
          hostPort      = var.container_port
          protocol      = "tcp"
        }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = local.cloudwatch_log_group_name
          "awslogs-region"        = local.region
          "awslogs-stream-prefix" = "ecs"
        }
      }
    }
  ])

  tags = local.tags
}

# ECS Service for frontend
resource "aws_ecs_service" "frontend" {
  name                   = "${local.name_prefix}-service"
  cluster                = aws_ecs_cluster.frontend.id
  task_definition        = aws_ecs_task_definition.frontend.arn
  desired_count          = var.desired_count
  launch_type            = "FARGATE"
  enable_execute_command = true

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [aws_security_group.frontend_ecs.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.frontend.arn
    container_name   = local.container_name
    container_port   = var.container_port
  }

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  lifecycle {
    ignore_changes = [desired_count]
  }

  tags = local.tags
}

# Auto Scaling for the frontend service
resource "aws_appautoscaling_target" "frontend" {
  max_capacity       = var.max_capacity
  min_capacity       = var.min_capacity
  resource_id        = "service/${aws_ecs_cluster.frontend.name}/${aws_ecs_service.frontend.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

# CPU Utilization Scaling Policy
resource "aws_appautoscaling_policy" "frontend_cpu" {
  name               = "${local.name_prefix}-cpu-scaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.frontend.resource_id
  scalable_dimension = aws_appautoscaling_target.frontend.scalable_dimension
  service_namespace  = aws_appautoscaling_target.frontend.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value       = 70
    scale_in_cooldown  = 300
    scale_out_cooldown = 60
  }
}

# Memory Utilization Scaling Policy
resource "aws_appautoscaling_policy" "frontend_memory" {
  name               = "${local.name_prefix}-memory-scaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.frontend.resource_id
  scalable_dimension = aws_appautoscaling_target.frontend.scalable_dimension
  service_namespace  = aws_appautoscaling_target.frontend.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageMemoryUtilization"
    }
    target_value       = 70
    scale_in_cooldown  = 300
    scale_out_cooldown = 60
  }
}
