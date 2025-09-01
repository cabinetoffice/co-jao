locals {
  name = "${var.name_prefix}-${var.environment}"

  # IAM configuration
  task_execution_role_arn  = aws_iam_role.ecs_task_execution_role.arn
  task_execution_role_name = aws_iam_role.ecs_task_execution_role.name
  task_role_arn            = aws_iam_role.ecs_task_role.arn
  task_role_name           = aws_iam_role.ecs_task_role.name

  # CloudWatch configuration
  log_group_name            = "/ecs/${local.name}"
  cloudwatch_log_group_name = aws_cloudwatch_log_group.app.name
  cloudwatch_log_group_arn  = aws_cloudwatch_log_group.app.arn

  # Feature flags
  enable_monitoring = var.enable_enhanced_monitoring
  enable_xray       = var.enable_xray_tracing
  enable_discovery  = var.enable_service_discovery
  enable_celery     = var.enable_celery_services

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


  base_environment = concat(
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

  # Web API container definitions
  api_container_definitions = jsonencode(concat(
    [
      {
        name      = local.container_name
        image     = var.ecr_repository_url
        essential = true
        command   = var.api_command
        portMappings = [
          {
            containerPort = var.container_port
            hostPort      = var.container_port
            protocol      = "tcp"
          }
        ]
        environment = local.base_environment
        healthCheck = {
          command     = ["CMD-SHELL", "curl -f http://localhost:${var.container_port}${var.health_check_path} || python -c \"import urllib.request; urllib.request.urlopen('http://localhost:${var.container_port}${var.health_check_path}')\" || exit 1"]
          interval    = 30
          timeout     = 10
          retries     = 3
          startPeriod = 120
        }
        logConfiguration = {
          logDriver = "awslogs"
          options = {
            "awslogs-group"         = local.cloudwatch_log_group_name
            "awslogs-region"        = data.aws_region.current.name
            "awslogs-stream-prefix" = "web"
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
            "awslogs-stream-prefix" = "xray"
          }
        }
      }
    ] : []
  ))

  # Celery Worker container definitions
  worker_container_definitions = jsonencode([
    {
      name      = "celery-worker"
      image     = var.ecr_repository_url
      essential = true
      command   = var.celery_worker_command
      environment = concat(
        local.base_environment,
        [
          {
            name  = "CELERY_WORKER_CONCURRENCY"
            value = tostring(var.celery_worker_concurrency)
          }
        ]
      )
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = local.cloudwatch_log_group_name
          "awslogs-region"        = data.aws_region.current.name
          "awslogs-stream-prefix" = "worker"
        }
      }
    }
  ])

  # Celery Beat container definitions
  beat_container_definitions = jsonencode([
    {
      name      = "celery-beat"
      image     = var.ecr_repository_url
      essential = true
      command   = var.celery_beat_command
      portMappings = [
        {
          containerPort = var.container_port
          hostPort      = var.container_port
          protocol      = "tcp"
        }
      ]
      environment = local.base_environment
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = local.cloudwatch_log_group_name
          "awslogs-region"        = data.aws_region.current.name
          "awslogs-stream-prefix" = "beat"
        }
      }
    }
  ])
}

# Data sources
data "aws_vpc" "main" {
  id = var.vpc_id
}

data "aws_region" "current" {}

# ECS cluster
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

resource "aws_vpc_endpoint" "bedrock" {
  vpc_id            = var.vpc_id
  service_name      = "com.amazonaws.eu-west-2.bedrock"
  vpc_endpoint_type = "Interface"
  subnet_ids        = var.private_subnet_ids

  security_group_ids = [aws_security_group.ecs_tasks.id]

  private_dns_enabled = true

  tags = {
    Name        = "bedrock-endpoint"
    Environment = var.environment
  }
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

  # Allow traffic from admin ALB
  ingress {
    from_port       = var.container_port
    to_port         = var.container_port
    protocol        = "tcp"
    security_groups = [aws_security_group.admin_alb.id]
    description     = "HTTP from admin ALB"
  }

  # HTTP for health checks and external APIs
  egress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # HTTPS for VPC endpoints and external APIs
  egress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = [data.aws_vpc.main.cidr_block]
    description = "HTTPS to VPC endpoints"
  }

   # DNS resolution
  egress {
    from_port   = 53
    to_port     = 53
    protocol    = "tcp"
    cidr_blocks = [data.aws_vpc.main.cidr_block]
    description = "DNS TCP to VPC"
  }

  egress {
    from_port   = 53
    to_port     = 53
    protocol    = "udp"
    cidr_blocks = [data.aws_vpc.main.cidr_block]
    description = "DNS UDP to VPC"
  }

  # Database access (PostgreSQL)
  egress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = [data.aws_vpc.main.cidr_block]
    description = "PostgreSQL database access"
  }

  # Redis access
  egress {
    from_port   = 6379
    to_port     = 6379
    protocol    = "tcp"
    cidr_blocks = [data.aws_vpc.main.cidr_block]
    description = "Redis database access"
  }

  tags = merge(
    local.common_tags,
    {
      Name = "${local.name}-ecs-tasks-sg"
    }
  )
}

# Security group for admin ALB
resource "aws_security_group" "admin_alb" {
  name        = "${local.name}-admin-alb-sg"
  description = "Security group for admin ALB"
  vpc_id      = var.vpc_id

  # Allow HTTP from allowed IPs only (configured via variable)
  dynamic "ingress" {
    for_each = var.admin_allowed_cidrs != null ? var.admin_allowed_cidrs : ["0.0.0.0/0"]
    content {
      from_port   = 80
      to_port     = 80
      protocol    = "tcp"
      cidr_blocks = [ingress.value]
      description = "HTTP from ${ingress.value}"
    }
  }

  # Allow HTTPS from allowed IPs only (configured via variable)
  dynamic "ingress" {
    for_each = var.admin_allowed_cidrs != null ? var.admin_allowed_cidrs : ["0.0.0.0/0"]
    content {
      from_port   = 443
      to_port     = 443
      protocol    = "tcp"
      cidr_blocks = [ingress.value]
      description = "HTTPS from ${ingress.value}"
    }
  }

  # Allow all outbound traffic to ECS tasks
  egress {
    from_port   = var.container_port
    to_port     = var.container_port
    protocol    = "tcp"
    cidr_blocks = [data.aws_vpc.main.cidr_block]
    description = "HTTP to ECS tasks"
  }

  tags = merge(
    local.common_tags,
    {
      Name = "${local.name}-admin-alb-sg"
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

  enable_cross_zone_load_balancing = var.enable_cross_zone_load_balancing

  tags = merge(
    local.common_tags,
    {
      Name = "${local.name}-nlb"
    }
  )
}

# Target group for the NLB
resource "aws_lb_target_group" "app" {
  name        = "${local.name}-nlb-tg"
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
      Name = "${local.name}-nlb-tg"
    }
  )
}

# NLB Listener
resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.main.arn
  port              = 80
  protocol          = "TCP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.app.arn
  }
}

# Amazon Load Balancer for admin user
resource "aws_lb" "admin" {
  name               = "${local.name}-alb"
  internal           = !var.admin_lb_internet_facing
  load_balancer_type = "application"
  subnets            = var.admin_lb_internet_facing ? var.public_subnet_ids : var.private_subnet_ids
  security_groups    = [aws_security_group.admin_alb.id]

  enable_deletion_protection = var.lb_deletion_protection

  tags = merge(
    local.common_tags,
    {
      Name = "${local.name}-alb"
    }
  )
}


# Target group for the ALB
resource "aws_lb_target_group" "admin" {
  name        = "${local.name}-alb-tg"
  port        = var.container_port
  protocol    = "HTTP"
  vpc_id      = var.vpc_id
  target_type = "ip"

  health_check {
    enabled             = true
    healthy_threshold   = 2
    unhealthy_threshold = 2
    timeout             = 5
    interval            = 30
    path                = "/health"
    matcher             = "200"
    protocol            = "HTTP"
    port                = var.container_port
  }

  tags = merge(
    local.common_tags,
    {
      Name = "${local.name}-alb-tg"
    }
  )
}

# ALB Listener
resource "aws_lb_listener" "admin" {
  load_balancer_arn = aws_lb.admin.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.admin.arn
  }
}





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

# Task definitions
resource "aws_ecs_task_definition" "api" {
  family                   = "${local.name}-api-task"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.api_cpu
  memory                   = var.api_memory
  execution_role_arn       = local.task_execution_role_arn
  task_role_arn            = local.task_role_arn
  container_definitions    = local.api_container_definitions

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
      Name = "${local.name}-web-task-definition"
    }
  )
}

# Celery Worker Task Definition
resource "aws_ecs_task_definition" "worker" {
  count = local.enable_celery ? 1 : 0

  family                   = "${local.name}-worker-task"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.worker_cpu
  memory                   = var.worker_memory
  execution_role_arn       = local.task_execution_role_arn
  task_role_arn            = local.task_role_arn
  container_definitions    = local.worker_container_definitions

  tags = merge(
    local.common_tags,
    {
      Name = "${local.name}-worker-task-definition"
    }
  )
}

# Celery Beat Task Definition
resource "aws_ecs_task_definition" "beat" {
  count = local.enable_celery ? 1 : 0

  family                   = "${local.name}-beat-task"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.beat_cpu
  memory                   = var.beat_memory
  execution_role_arn       = local.task_execution_role_arn
  task_role_arn            = local.task_role_arn
  container_definitions    = local.beat_container_definitions

  tags = merge(
    local.common_tags,
    {
      Name = "${local.name}-beat-task-definition"
    }
  )
}

# ECS service
resource "aws_ecs_service" "api" {
  name                   = "${local.name}-api-service"
  cluster                = aws_ecs_cluster.main.id
  task_definition        = aws_ecs_task_definition.api.arn
  desired_count          = var.desired_count
  launch_type            = "FARGATE"
  enable_execute_command = true

  network_configuration {
    security_groups  = concat([aws_security_group.ecs_tasks.id], var.additional_security_group_ids)
    subnets          = var.private_subnet_ids
    assign_public_ip = false
  }

  # Load balancer for API interface
  load_balancer {
    target_group_arn = aws_lb_target_group.app.arn
    container_name   = local.container_name
    container_port   = var.container_port
  }

  # Load balancer for admin interface
  load_balancer {
    target_group_arn = aws_lb_target_group.admin.arn
    container_name   = local.container_name
    container_port   = var.container_port
  }

  deployment_controller {
    type = "ECS"
  }

  deployment_maximum_percent         = var.deployment_maximum_percent
  deployment_minimum_healthy_percent = var.deployment_minimum_healthy_percent

  enable_ecs_managed_tags = true
  propagate_tags          = "SERVICE"

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
      Name = "${local.name}-api-service"
    }
  )
}

resource "aws_ecs_service" "worker" {
  count = local.enable_celery ? 1 : 0

  name                   = "${local.name}-worker-service"
  cluster                = aws_ecs_cluster.main.id
  task_definition        = aws_ecs_task_definition.worker[0].arn
  desired_count          = var.worker_desired_count
  launch_type            = "FARGATE"
  enable_execute_command = true

  network_configuration {
    security_groups  = concat([aws_security_group.ecs_tasks.id], var.additional_security_group_ids)
    subnets          = var.private_subnet_ids
    assign_public_ip = false
  }

  deployment_controller {
    type = "ECS"
  }

  deployment_maximum_percent         = var.deployment_maximum_percent
  deployment_minimum_healthy_percent = var.deployment_minimum_healthy_percent

  enable_ecs_managed_tags = true
  propagate_tags          = "SERVICE"

  deployment_circuit_breaker {
    enable   = var.enable_circuit_breaker
    rollback = var.enable_circuit_breaker
  }

  tags = merge(
    local.common_tags,
    {
      Name = "${local.name}-worker-service"
    }
  )
}

resource "aws_ecs_service" "beat" {
  count = local.enable_celery ? 1 : 0

  name                   = "${local.name}-beat-service"
  cluster                = aws_ecs_cluster.main.id
  task_definition        = aws_ecs_task_definition.beat[0].arn
  desired_count          = 1
  launch_type            = "FARGATE"
  enable_execute_command = true

  network_configuration {
    security_groups  = concat([aws_security_group.ecs_tasks.id], var.additional_security_group_ids)
    subnets          = var.private_subnet_ids
    assign_public_ip = false
  }

  deployment_controller {
    type = "ECS"
  }

  deployment_maximum_percent         = 100
  deployment_minimum_healthy_percent = 0

  enable_ecs_managed_tags = true
  propagate_tags          = "SERVICE"

  deployment_circuit_breaker {
    enable   = var.enable_circuit_breaker
    rollback = var.enable_circuit_breaker
  }

  tags = merge(
    local.common_tags,
    {
      Name = "${local.name}-beat-service"
    }
  )
}

resource "aws_appautoscaling_target" "worker" {
  count = local.enable_celery && var.enable_worker_autoscaling ? 1 : 0

  max_capacity       = var.worker_max_capacity
  min_capacity       = var.worker_min_capacity
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.worker[0].name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

resource "aws_appautoscaling_policy" "worker_cpu_scaling" {
  count = local.enable_celery && var.enable_worker_autoscaling ? 1 : 0

  name               = "${local.name}-worker-cpu-scaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.worker[0].resource_id
  scalable_dimension = aws_appautoscaling_target.worker[0].scalable_dimension
  service_namespace  = aws_appautoscaling_target.worker[0].service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value       = var.worker_cpu_target_value
    scale_in_cooldown  = 300
    scale_out_cooldown = 300
  }
}


resource "aws_cloudwatch_dashboard" "api_monitoring" {
  count = local.enable_monitoring ? 1 : 0

  dashboard_name = "${local.name}-monitoring"
  dashboard_body = jsonencode({
    widgets = concat([
      {
        type   = "metric"
        x      = 0
        y      = 0
        height = 6
        properties = {
          metrics = [
            ["AWS/ECS", "CPUUtilization", "ServiceName", aws_ecs_service.api.name, "ClusterName", aws_ecs_cluster.main.name, { "stat" = "Average" }],
            [".", "MemoryUtilization", ".", ".", ".", ".", { "stat" = "Average" }]
          ]
          period  = 300
          region  = data.aws_region.current.name
          title   = "Web Service - CPU and Memory"
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
          metrics = concat(
            [
              ["API/Errors", "${local.name}-APIErrors", { "stat" = "Sum" }]
            ],
            local.enable_celery ? [
              ["Celery/Errors", "${local.name}-CeleryErrors", { "stat" = "Sum" }]
            ] : []
          )
          period  = 300
          region  = data.aws_region.current.name
          title   = "Error Counts"
          view    = "timeSeries"
          stacked = false
        }
      }
      ],
      (local.enable_celery ? [
        {
          type   = "metric"
          x      = 0
          y      = 6
          width  = 12
          height = 6
          properties = {
            metrics = [
              ["AWS/ECS", "CPUUtilization", "ServiceName", aws_ecs_service.worker[0].name, "ClusterName", aws_ecs_cluster.main.name, { "stat" = "Average" }],
              [".", "MemoryUtilization", ".", ".", ".", ".", { "stat" = "Average" }]
            ],
            period  = 300,
            region  = data.aws_region.current.name,
            title   = "Worker Service - CPU and Memory",
            view    = "timeSeries",
            stacked = false
          }
        },
        {
          type   = "metric"
          x      = 12
          y      = 6
          width  = 12
          height = 6
          properties = {
            metrics = [
              ["AWS/ECS", "RunningTaskCount", "ServiceName", aws_ecs_service.beat[0].name, "ClusterName", aws_ecs_cluster.main.name, { "stat" = "Average" }],
              [".", ".", "ServiceName", "${local.name}-beat-service", ".", ".", { "stat" = "Average" }]
            ],
            period  = 300,
            region  = data.aws_region.current.name,
            title   = "Celery Services - Running Tasks",
            view    = "timeSeries",
            stacked = false
          }
        }
    ] : []))
  })
}
