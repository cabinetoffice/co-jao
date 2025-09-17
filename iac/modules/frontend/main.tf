locals {
  name_prefix                  = "${var.name_prefix}-frontend-${var.environment}"
  container_name               = "${var.name_prefix}-frontend"
  container_port               = var.container_port
  region                       = data.aws_region.current.name
  frontend_execution_role_arn  = aws_iam_role.frontend_execution.arn
  frontend_task_role_arn       = aws_iam_role.frontend_task.arn
  frontend_execution_role_name = aws_iam_role.frontend_execution.name

  log_group_name            = "/ecs/${local.name_prefix}"
  cloudwatch_log_group_name = aws_cloudwatch_log_group.frontend.name
  cloudwatch_log_group_arn  = aws_cloudwatch_log_group.frontend.arn

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
        image     = var.ecr_repository_url
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
              value = "debug"
            }
          ] : []
        )
        healthCheck = {
          command     = ["CMD-SHELL", "curl -f http://localhost:${var.container_port}${var.health_check_path} || exit 1"]
          interval    = 300
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
  name              = local.log_group_name
  retention_in_days = var.logs_retention_in_days

  tags = local.tags
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
    interval            = 300
    timeout             = 10
    healthy_threshold   = 2
    unhealthy_threshold = 5
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
    subnets          = var.public_subnet_ids
    security_groups  = [aws_security_group.frontend_ecs.id]
    assign_public_ip = true
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

  tags = local.tags
}

# Auto Scaling for the frontend service
resource "aws_appautoscaling_target" "frontend" {
  count              = var.environment == "prod" ? 1 : 0
  max_capacity       = var.max_capacity
  min_capacity       = var.min_capacity
  resource_id        = "service/${aws_ecs_cluster.frontend.name}/${aws_ecs_service.frontend.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

# CPU Utilization Scaling Policy
resource "aws_appautoscaling_policy" "frontend_cpu" {
  count              = var.environment == "prod" ? 1 : 0
  name               = "${local.name_prefix}-cpu-scaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.frontend[0].resource_id
  scalable_dimension = aws_appautoscaling_target.frontend[0].scalable_dimension
  service_namespace  = aws_appautoscaling_target.frontend[0].service_namespace

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
  count              = var.environment == "prod" ? 1 : 0
  name               = "${local.name_prefix}-memory-scaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.frontend[0].resource_id
  scalable_dimension = aws_appautoscaling_target.frontend[0].scalable_dimension
  service_namespace  = aws_appautoscaling_target.frontend[0].service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageMemoryUtilization"
    }
    target_value       = 70
    scale_in_cooldown  = 300
    scale_out_cooldown = 60
  }
}
