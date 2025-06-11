locals {
  name = "${var.name_prefix}-${var.environment}"

  # IAM configuration
  task_execution_role_arn  = aws_iam_role.ecs_task_execution_role.arn
  task_execution_role_name = aws_iam_role.ecs_task_execution_role.name

  # CloudWatch configuration
  log_group_name = "/ecs/${local.name}"
  cloudwatch_log_group_name = aws_cloudwatch_log_group.app.name
  cloudwatch_log_group_arn = aws_cloudwatch_log_group.app.arn

  # Feature flags
  enable_monitoring = var.enable_enhanced_monitoring
  enable_xray = var.enable_xray_tracing
  enable_discovery = var.enable_service_discovery

  # Common tags for all resources
  common_tags = merge(
    var.tags,
    {
      Environment = var.environment
      ManagedBy   = "terraform"
      Name        = local.name
    }
  )

  container_name = var.container_name != "" ? var.container_name : var.name_prefix
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
          local.enable_monitoring ? [
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
        dependsOn = local.enable_xray ? [
          {
            containerName = "xray-daemon"
            condition     = "START"
          }
        ] : null
      }
    ],
    local.enable_xray ? [
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

# ECS cluster for service discovery
resource "aws_ecs_cluster" "main" {
  name = "${local.name}-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  # Enable CloudWatch Container Insights for enhanced monitoring
  dynamic "configuration" {
    for_each = local.enable_monitoring ? [1] : []
    content {
      execute_command_configuration {
        logging = "OVERRIDE"
        log_configuration {
          cloud_watch_log_group_name = local.cloudwatch_log_group_name
        }
      }
    }
  }

  # Service discovery configuration for microservices communication
  dynamic "service_connect_defaults" {
    for_each = local.enable_discovery ? [1] : []
    content {
      namespace = var.service_discovery_namespace
    }
  }

  tags = merge(
    local.common_tags,
    {
      Name = "${local.name}-cluster"
    }
  )
}



# Data source to get VPC CIDR
data "aws_vpc" "main" {
  id = var.vpc_id
}

# Security group for ECS tasks
resource "aws_security_group" "ecs_tasks" {
  name        = "${local.name}-ecs-tasks-sg"
  description = "Allow inbound access from the NLB"
  vpc_id      = var.vpc_id

  ingress {
    from_port   = var.container_port
    to_port     = var.container_port
    protocol    = "tcp"
    cidr_blocks = [data.aws_vpc.main.cidr_block]
  }

  egress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = [data.aws_vpc.main.cidr_block]
  }

  egress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = [data.aws_vpc.main.cidr_block]
  }

  egress {
    from_port   = 53
    to_port     = 53
    protocol    = "udp"
    cidr_blocks = [data.aws_vpc.main.cidr_block]
    description = "DNS resolution"
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
      Name = "${local.name}-ecs-tasks-sg"
    }
  )
}

# Network Load Balancer
resource "aws_lb" "main" {
  name               = "${local.name}-nlb"
  internal           = var.internal_lb
  load_balancer_type = "network"
  subnets            = var.internal_lb ? var.private_subnet_ids : var.public_subnet_ids

  enable_deletion_protection = var.lb_deletion_protection

  # Enable cross-zone load balancing for high availability
  enable_cross_zone_load_balancing = var.enable_cross_zone_load_balancing

  tags = merge(
    local.common_tags,
    {
      Name = "${local.name}-nlb"
    }
  )
}

# Network Load Balancer for API Gateway VPC Link


# Target group for the NLB
resource "aws_lb_target_group" "app" {
  name        = "${local.name}-tg"
  port        = var.container_port
  protocol    = "TCP"
  vpc_id      = var.vpc_id
  target_type = "ip"

  health_check {
    port                = var.container_port
    protocol            = "TCP"
    interval            = 30
    timeout             = 6
    healthy_threshold   = 2
    unhealthy_threshold = 2
  }

  lifecycle {
    create_before_destroy = true
  }

  tags = merge(
    local.common_tags,
    {
      Name = "${local.name}-tg"
    }
  )
}

# NLB Listener
resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.main.arn
  port              = "80"
  protocol          = "TCP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.app.arn
  }
}

# ECS task execution role
resource "aws_iam_role" "ecs_task_execution_role" {
  name  = "${local.name}-ecs-task-execution-role"

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

  tags = merge(
    local.common_tags,
    {
      Name = "${local.name}-ecs-task-execution-role"
    }
  )
}

# Attach the task execution role policy
resource "aws_iam_role_policy_attachment" "ecs_task_execution_role_policy" {
  role       = aws_iam_role.ecs_task_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# Create ECR access policy
resource "aws_iam_policy" "ecr_access_policy" {
  name        = "${local.name}-ecr-access-policy"
  description = "Policy for ECR image pull and push access"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:BatchCheckLayerAvailability",
          "ecr:PutImage",
          "ecr:InitiateLayerUpload",
          "ecr:UploadLayerPart",
          "ecr:CompleteLayerUpload"
        ]
        Resource = "*"
      },
      {
        Effect   = "Allow"
        Action   = "ecr:GetAuthorizationToken"
        Resource = "*"
      }
    ]
  })

  tags = merge(
    local.common_tags,
    {
      Name = "${local.name}-ecr-access-policy"
    }
  )
}

resource "aws_iam_role_policy_attachment" "ecr_access_policy_attachment" {
  role       = aws_iam_role.ecs_task_execution_role.name
  policy_arn = aws_iam_policy.ecr_access_policy.arn
}

resource "aws_iam_policy" "xray_access_policy" {
  count = local.enable_xray ? 1 : 0

  name        = "${local.name}-xray-access-policy"
  description = "Policy for X-Ray tracing access"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "xray:PutTraceSegments",
          "xray:PutTelemetryRecords",
          "xray:GetSamplingRules",
          "xray:GetSamplingTargets",
          "xray:GetSamplingStatisticSummaries"
        ]
        Resource = "*"
      }
    ]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "xray_access_policy_attachment" {
  count = local.enable_xray ? 1 : 0

  role       = aws_iam_role.ecs_task_execution_role.name
  policy_arn = aws_iam_policy.xray_access_policy[0].arn
}

data "aws_region" "current" {}

# CloudWatch log group
resource "aws_cloudwatch_log_group" "app" {
  name              = local.log_group_name
  retention_in_days = var.logs_retention_in_days

  tags = merge(
    local.common_tags,
    {
      Name = "${local.name}-log-group"
    }
  )
}

# CloudWatch Log Metric Filters for API monitoring
resource "aws_cloudwatch_log_metric_filter" "api_errors" {
  count = local.enable_monitoring ? 1 : 0

  name           = "${local.name}-api-errors"
  pattern        = "{$.level = \"error\" || $.level = \"ERROR\"}"
  log_group_name = local.cloudwatch_log_group_name

  metric_transformation {
    name          = "${local.name}-APIErrors"
    namespace     = "API/Errors"
    value         = "1"
    default_value = "0"
  }
}

resource "aws_cloudwatch_log_metric_filter" "api_latency" {
  count = local.enable_monitoring ? 1 : 0

  name           = "${local.name}-api-latency"
  pattern        = "{$.responseTime > 0}"
  log_group_name = local.cloudwatch_log_group_name

  metric_transformation {
    name          = "${local.name}-APILatency"
    namespace     = "API/Performance"
    value         = "$.responseTime"
    default_value = "0"
  }
}

# CloudWatch Dashboard for API monitoring
resource "aws_cloudwatch_dashboard" "api_monitoring" {
  count = local.enable_monitoring ? 1 : 0

  dashboard_name = "${local.name}-api-monitoring"
  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/ECS", "CPUUtilization", "ServiceName", aws_ecs_service.app.name, "ClusterName", aws_ecs_cluster.main.name, { "stat" = "Average" }],
            [".", "MemoryUtilization", ".", ".", ".", ".", { "stat" = "Average" }]
          ]
          period  = 300
          region  = data.aws_region.current.name
          title   = "ECS Service CPU and Memory"
          view    = "timeSeries"
          stacked = false
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 0
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["API/Errors", "${local.name}-APIErrors", { "stat" = "Sum" }]
          ]
          period  = 300
          region  = data.aws_region.current.name
          title   = "API Errors"
          view    = "timeSeries"
          stacked = false
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 6
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["API/Performance", "${local.name}-APILatency", { "stat" = "Average" }],
            ["...", { "stat" = "p90" }],
            ["...", { "stat" = "p99" }]
          ]
          period  = 300
          region  = data.aws_region.current.name
          title   = "API Latency"
          view    = "timeSeries"
          stacked = false
        }
      },
      {
        type   = "log"
        x      = 12
        y      = 6
        width  = 12
        height = 6
        properties = {
          query  = "SOURCE '${local.cloudwatch_log_group_name}' | fields @timestamp, @message | filter level='error' OR level='ERROR' | sort @timestamp desc | limit 20"
          region = data.aws_region.current.name
          title  = "Recent API Errors"
          view   = "table"
        }
      }
    ]
  })
}

# Task definition
resource "aws_ecs_task_definition" "app" {
  family                   = "${local.name}-task"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.cpu
  memory                   = var.memory
  execution_role_arn       = local.task_execution_role_arn
  container_definitions    = local.container_definitions

  # Enable AWS X-Ray tracing for API monitoring
  dynamic "proxy_configuration" {
    for_each = local.enable_xray ? [1] : []
    content {
      type           = "APPMESH"
      container_name = "envoy"
      properties = {
        "ProxyIngressPort" = "15000"
        "ProxyEgressPort"  = "15001"
        "AppPorts"         = "${var.container_port}"
        "EgressIgnoredIPs" = "169.254.170.2,169.254.169.254"
      }
    }
  }

  tags = merge(
    local.common_tags,
    {
      Name = "${local.name}-task-definition"
    }
  )
}

# ECS service
resource "aws_ecs_service" "app" {
  name            = "${local.name}-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.app.arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"

  network_configuration {
    security_groups  = [aws_security_group.ecs_tasks.id]
    subnets          = var.private_subnet_ids
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.app.arn
    container_name   = local.container_name
    container_port   = var.container_port
  }

  deployment_controller {
    type = "ECS"
  }

  deployment_maximum_percent         = var.deployment_maximum_percent
  deployment_minimum_healthy_percent = var.deployment_minimum_healthy_percent

  # Enable CloudWatch Container Insights for detailed monitoring
  enable_ecs_managed_tags = true
  propagate_tags          = "SERVICE"

  # Circuit breaker to detect and handle failed deployments automatically
  deployment_circuit_breaker {
    enable   = var.enable_circuit_breaker
    rollback = var.enable_circuit_breaker
  }

  depends_on = [
    aws_lb_listener.http
  ]

  tags = merge(
    local.common_tags,
    {
      Name = "${local.name}-service"
    }
  )
}
