# modules/scheduled_task/main.tf
#
# ECS Scheduled Tasks Module
# Runs containerized tasks on a schedule (e.g., weekly data pipeline)
# Supports multiple task definitions in a single cluster

locals {
  name = "${var.name_prefix}-${var.environment}"

  # Data engine container environment
  data_engine_environment = [
    for key, value in var.environment_variables : {
      name  = key
      value = value
    }
  ]

  # Skills worker container environment
  skills_worker_environment = [
    for key, value in var.skills_worker_environment_variables : {
      name  = key
      value = value
    }
  ]

  data_engine_container_definitions = jsonencode([
    {
      name      = "data-engine"
      image     = var.data_engine_image_url
      essential = true
      command   = var.data_engine_command

      environment = local.data_engine_environment

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.tasks.name
          "awslogs-region"        = data.aws_region.current.name
          "awslogs-stream-prefix" = "data-engine"
        }
      }
    }
  ])

  skills_worker_container_definitions = jsonencode([
    {
      name      = "skills-worker"
      image     = var.skills_worker_image_url
      essential = true
      command   = var.skills_worker_command

      environment = local.skills_worker_environment

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.tasks.name
          "awslogs-region"        = data.aws_region.current.name
          "awslogs-stream-prefix" = "skills-worker"
        }
      }
    }
  ])
}

data "aws_region" "current" {}

# =============================================================================
# ECS CLUSTER (Single cluster for all tasks)
# =============================================================================

resource "aws_ecs_cluster" "main" {
  name = "${local.name}-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = merge(var.tags, {
    Name = "${local.name}-cluster"
  })
}

# =============================================================================
# CLOUDWATCH LOG GROUP (Shared by all tasks)
# =============================================================================

resource "aws_cloudwatch_log_group" "tasks" {
  name              = "/ecs/${local.name}/tasks"
  retention_in_days = var.logs_retention_in_days

  tags = merge(var.tags, {
    Name = "${local.name}-task-logs"
  })
}

# =============================================================================
# IAM ROLES (Shared by all tasks)
# =============================================================================

# Task Execution Role (for ECS to pull images, write logs)
resource "aws_iam_role" "task_execution" {
  name = "${local.name}-task-execution-role"

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

  tags = var.tags
}

resource "aws_iam_role_policy_attachment" "task_execution" {
  role       = aws_iam_role.task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# Task Role (for the container itself to access AWS services)
resource "aws_iam_role" "task" {
  name = "${local.name}-task-role"

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

  tags = var.tags
}

# Allow task to access Bedrock for embeddings
resource "aws_iam_role_policy" "task_bedrock" {
  name = "${local.name}-bedrock-access"
  role = aws_iam_role.task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream"
        ]
        Resource = "*"
      }
    ]
  })
}

# Allow task to write to CloudWatch Logs
resource "aws_iam_role_policy" "task_logs" {
  name = "${local.name}-logs-access"
  role = aws_iam_role.task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "${aws_cloudwatch_log_group.tasks.arn}:*"
      }
    ]
  })
}

# =============================================================================
# SECURITY GROUP (Shared by all tasks)
# =============================================================================

resource "aws_security_group" "tasks" {
  name        = "${local.name}-tasks-sg"
  description = "Security group for ECS tasks"
  vpc_id      = var.vpc_id

  # HTTPS for AWS services (ECR, CloudWatch, Bedrock, etc.)
  egress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTPS for AWS services"
  }

  # DNS resolution
  egress {
    from_port   = 53
    to_port     = 53
    protocol    = "udp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "DNS resolution"
  }

  egress {
    from_port   = 53
    to_port     = 53
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "DNS resolution TCP"
  }

  tags = merge(var.tags, {
    Name = "${local.name}-tasks-sg"
  })
}

# =============================================================================
# TASK DEFINITIONS
# =============================================================================

# Data Engine Task Definition (Python 3.12)
resource "aws_ecs_task_definition" "data_engine" {
  family                   = "${local.name}-data-engine"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.data_engine_cpu
  memory                   = var.data_engine_memory
  execution_role_arn       = aws_iam_role.task_execution.arn
  task_role_arn            = aws_iam_role.task.arn
  container_definitions    = local.data_engine_container_definitions

  tags = merge(var.tags, {
    Name    = "${local.name}-data-engine-task"
    Runtime = "python3.12"
  })
}

# Skills Worker Task Definition (Python 3.10)
resource "aws_ecs_task_definition" "skills_worker" {
  family                   = "${local.name}-skills-worker"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.skills_worker_cpu
  memory                   = var.skills_worker_memory
  execution_role_arn       = aws_iam_role.task_execution.arn
  task_role_arn            = aws_iam_role.task.arn
  container_definitions    = local.skills_worker_container_definitions

  tags = merge(var.tags, {
    Name    = "${local.name}-skills-worker-task"
    Runtime = "python3.10"
  })
}

# =============================================================================
# EVENTBRIDGE SCHEDULER
# =============================================================================

# IAM Role for EventBridge to invoke ECS
resource "aws_iam_role" "eventbridge" {
  name = "${local.name}-eventbridge-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "scheduler.amazonaws.com"
        }
      }
    ]
  })

  tags = var.tags
}

resource "aws_iam_role_policy" "eventbridge_ecs" {
  name = "${local.name}-eventbridge-ecs-policy"
  role = aws_iam_role.eventbridge.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ecs:RunTask"
        ]
        Resource = [
          aws_ecs_task_definition.data_engine.arn,
          "${replace(aws_ecs_task_definition.data_engine.arn, "/:\\d+$/", "")}:*",
          aws_ecs_task_definition.skills_worker.arn,
          "${replace(aws_ecs_task_definition.skills_worker.arn, "/:\\d+$/", "")}:*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "iam:PassRole"
        ]
        Resource = [
          aws_iam_role.task_execution.arn,
          aws_iam_role.task.arn
        ]
      }
    ]
  })
}

# Schedule for Data Engine (Weekly Pipeline)
resource "aws_scheduler_schedule" "data_engine" {
  name        = "${local.name}-data-engine-schedule"
  description = "Run the weekly data pipeline (Python 3.12)"
  group_name  = "default"

  flexible_time_window {
    mode = "OFF"
  }

  schedule_expression          = var.data_engine_schedule_expression
  schedule_expression_timezone = "UTC"

  target {
    arn      = aws_ecs_cluster.main.arn
    role_arn = aws_iam_role.eventbridge.arn

    ecs_parameters {
      task_definition_arn = aws_ecs_task_definition.data_engine.arn
      launch_type         = "FARGATE"

      network_configuration {
        assign_public_ip = false
        security_groups  = concat([aws_security_group.tasks.id], var.security_group_ids)
        subnets          = var.private_subnet_ids
      }
    }

    retry_policy {
      maximum_event_age_in_seconds = 3600
      maximum_retry_attempts       = 3
    }
  }

  state = var.schedule_enabled ? "ENABLED" : "DISABLED"
}

# Schedule for Skills Worker (can be separate or triggered by data engine)
resource "aws_scheduler_schedule" "skills_worker" {
  count = var.enable_skills_worker_schedule ? 1 : 0

  name        = "${local.name}-skills-worker-schedule"
  description = "Run the skills extraction pipeline (Python 3.10)"
  group_name  = "default"

  flexible_time_window {
    mode = "OFF"
  }

  schedule_expression          = var.skills_worker_schedule_expression
  schedule_expression_timezone = "UTC"

  target {
    arn      = aws_ecs_cluster.main.arn
    role_arn = aws_iam_role.eventbridge.arn

    ecs_parameters {
      task_definition_arn = aws_ecs_task_definition.skills_worker.arn
      launch_type         = "FARGATE"

      network_configuration {
        assign_public_ip = false
        security_groups  = concat([aws_security_group.tasks.id], var.security_group_ids)
        subnets          = var.private_subnet_ids
      }
    }

    retry_policy {
      maximum_event_age_in_seconds = 3600
      maximum_retry_attempts       = 3
    }
  }

  state = var.schedule_enabled ? "ENABLED" : "DISABLED"
}
