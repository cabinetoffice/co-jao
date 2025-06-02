# ECS module - main.tf
locals {
  # Resource naming
  name = "${var.name_prefix}-${var.environment}"

  task_execution_role_arn  = var.skip_iam_role_creation ? var.existing_task_execution_role_arn : (length(aws_iam_role.ecs_task_execution_role) > 0 ? aws_iam_role.ecs_task_execution_role[0].arn : "")
  task_execution_role_name = var.skip_iam_role_creation ? element(split("/", var.existing_task_execution_role_arn), 1) : (length(aws_iam_role.ecs_task_execution_role) > 0 ? aws_iam_role.ecs_task_execution_role[0].name : "")

  # Use specified log group name if provided, otherwise use default pattern
  log_group_name   = var.existing_log_group_name != "" ? var.existing_log_group_name : "/ecs/${local.name}"
  log_group_exists = var.skip_cloudwatch_creation

  # When skipping creation, use the explicit name, otherwise use the created resource
  cloudwatch_log_group_name = var.skip_cloudwatch_creation ? local.log_group_name : aws_cloudwatch_log_group.app[0].name

  # When skipping creation and using explicit name, use the data source if available
  cloudwatch_log_group_arn = var.skip_cloudwatch_creation ? (
    length(data.aws_cloudwatch_log_group.existing_app) > 0 ? data.aws_cloudwatch_log_group.existing_app[0].arn : ""
  ) : aws_cloudwatch_log_group.app[0].arn

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

# ECS cluster for service discovery
resource "aws_ecs_cluster" "main" {
  name = "${local.name}-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  # Enable CloudWatch Container Insights for enhanced monitoring
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

  # Service discovery configuration for microservices communication
  dynamic "service_connect_defaults" {
    for_each = var.enable_service_discovery ? [1] : []
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

# Security group for the ALB
resource "aws_security_group" "alb" {
  name        = "${local.name}-alb-sg"
  description = "Controls access to the ALB"
  vpc_id      = var.vpc_id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
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
    {
      Name = "${local.name}-alb-sg"
    }
  )
}

# Security group for ECS tasks
resource "aws_security_group" "ecs_tasks" {
  name        = "${local.name}-ecs-tasks-sg"
  description = "Allow inbound access from the ALB only"
  vpc_id      = var.vpc_id

  ingress {
    from_port       = var.container_port
    to_port         = var.container_port
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(
    local.common_tags,
    {
      Name = "${local.name}-ecs-tasks-sg"
    }
  )
}

# Application Load Balancer
resource "aws_lb" "main" {
  name               = "${local.name}-alb"
  internal           = var.internal_lb
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = var.internal_lb ? var.private_subnet_ids : var.public_subnet_ids

  enable_deletion_protection = var.lb_deletion_protection

  # Enable access logs for troubleshooting and analysis
  dynamic "access_logs" {
    for_each = var.enable_lb_access_logs ? [1] : []
    content {
      bucket  = var.lb_access_logs_bucket
      prefix  = "${local.name}-alb-logs"
      enabled = true
    }
  }

  # Enable cross-zone load balancing for high availability
  enable_cross_zone_load_balancing = var.enable_cross_zone_load_balancing

  tags = merge(
    local.common_tags,
    {
      Name = "${local.name}-alb"
    }
  )
}

# Target group for the ALB
resource "aws_lb_target_group" "app" {
  name        = "${local.name}-tg"
  port        = var.container_port
  protocol    = "HTTP"
  vpc_id      = var.vpc_id
  target_type = "ip"

  health_check {
    path                = var.health_check_path
    protocol            = "HTTP"
    matcher             = "200"
    interval            = 30
    timeout             = 5
    healthy_threshold   = 3
    unhealthy_threshold = 3
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

# ALB listener
resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.main.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.app.arn
  }
}

# ECS task execution role
resource "aws_iam_role" "ecs_task_execution_role" {
  count = var.skip_iam_role_creation ? 0 : 1
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
  count      = var.skip_iam_role_creation ? 0 : 1
  role       = aws_iam_role.ecs_task_execution_role[0].name
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

# Attach ECR access policy to task execution role
# ECS Task Role
resource "aws_iam_role_policy_attachment" "ecr_access_policy_attachment" {
  count      = var.skip_iam_role_creation ? 0 : 1
  role       = aws_iam_role.ecs_task_execution_role[0].name
  policy_arn = aws_iam_policy.ecr_access_policy.arn
}

# X-Ray policies for tracing API calls
resource "aws_iam_policy" "xray_access_policy" {
  count = var.enable_xray_tracing ? 1 : 0

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
  count = var.enable_xray_tracing && !var.skip_iam_role_creation ? 1 : 0

  role       = aws_iam_role.ecs_task_execution_role[0].name
  policy_arn = aws_iam_policy.xray_access_policy[0].arn
}

# Data source for current region
data "aws_region" "current" {}

# CloudWatch log group
resource "aws_cloudwatch_log_group" "app" {
  count             = var.skip_cloudwatch_creation ? 0 : 1
  name              = local.log_group_name
  retention_in_days = var.logs_retention_in_days

  tags = merge(
    local.common_tags,
    {
      Name = "${local.name}-log-group"
    }
  )
}

# Data source to read existing CloudWatch log group if skipping creation
data "aws_cloudwatch_log_group" "existing_app" {
  count = var.skip_cloudwatch_creation && var.existing_log_group_name != "" ? 1 : 0
  name  = var.existing_log_group_name != "" ? var.existing_log_group_name : "/ecs/${local.name}"
}

# CloudWatch Log Metric Filters for API monitoring
resource "aws_cloudwatch_log_metric_filter" "api_errors" {
  count = var.enable_enhanced_monitoring && (!var.skip_cloudwatch_creation || var.existing_log_group_name != "") ? 1 : 0

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
  count = var.enable_enhanced_monitoring && (!var.skip_cloudwatch_creation || var.existing_log_group_name != "") ? 1 : 0

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
  count = var.enable_enhanced_monitoring ? 1 : 0

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
    for_each = var.enable_xray_tracing ? [1] : []
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

  lifecycle {
    ignore_changes = [task_definition, desired_count]
  }

  tags = merge(
    local.common_tags,
    {
      Name = "${local.name}-service"
    }
  )
}
