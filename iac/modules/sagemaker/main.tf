# SageMaker Notebook Instance Module

locals {
  name_prefix = "${var.app_name}-${var.environment}-sagemaker"

  default_tags = {
    Name        = local.name_prefix
    Environment = var.environment
    Purpose     = "data-science"
    Module      = "sagemaker"
    Terraform   = "true"
  }

  tags = merge(var.tags, local.default_tags)
}

# Security Group
resource "aws_security_group" "sagemaker_notebook" {
  name        = "${local.name_prefix}-notebook-sg"
  description = "Security group for SageMaker Notebook instance"
  vpc_id      = var.vpc_id

  # Egress rule for Aurora database connection
  egress {
    from_port   = var.aurora_port
    to_port     = var.aurora_port
    protocol    = "tcp"
    cidr_blocks = var.vpc_cidr_block != null ? [var.vpc_cidr_block] : ["10.0.0.0/8"]
    description = "Allow PostgreSQL connection to Aurora"
  }

  # Egress rule for HTTPS (AWS services: S3, Secrets Manager, SageMaker API)
  egress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow HTTPS for AWS services"
  }

  # Egress rule for HTTP (package downloads)
  egress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow HTTP for package downloads"
  }

  # Egress rule for DNS
  egress {
    from_port   = 53
    to_port     = 53
    protocol    = "tcp"
    cidr_blocks = var.vpc_cidr_block != null ? [var.vpc_cidr_block] : ["10.0.0.0/8"]
    description = "Allow DNS resolution (TCP)"
  }

  egress {
    from_port   = 53
    to_port     = 53
    protocol    = "udp"
    cidr_blocks = var.vpc_cidr_block != null ? [var.vpc_cidr_block] : ["10.0.0.0/8"]
    description = "Allow DNS resolution (UDP)"
  }

  # Egress rule for NTP (time synchronization)
  egress {
    from_port   = 123
    to_port     = 123
    protocol    = "udp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow NTP for time sync"
  }

  # Egress rule for Git (if using Git repositories)
  egress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow SSH for Git operations"
  }

  tags = merge(local.tags, {
    Name = "${local.name_prefix}-notebook-sg"
  })
}

# IAM Role
resource "aws_iam_role" "sagemaker_notebook" {
  name = "${local.name_prefix}-notebook-role"
  path = "/"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "sagemaker.amazonaws.com"
        }
      }
    ]
  })

  tags = local.tags
}

# IAM Policy
resource "aws_iam_role_policy" "sagemaker_notebook" {
  name = "${local.name_prefix}-notebook-policy"
  role = aws_iam_role.sagemaker_notebook.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          "${var.data_bucket_arn}",
          "${var.data_bucket_arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ]
        Resource = [
          aws_secretsmanager_secret.aurora_connection.arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:log-group:/aws/sagemaker/*"
      },
      {
        Effect = "Allow"
        Action = [
          "ec2:DescribeNetworkInterfaces",
          "ec2:DescribeSecurityGroups",
          "ec2:DescribeSubnets",
          "ec2:DescribeVpcs",
          "ec2:CreateNetworkInterface",
          "ec2:CreateNetworkInterfacePermission",
          "ec2:DeleteNetworkInterface"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "sagemaker:*"
        ]
        Resource = "*"
      }
    ]
  })
}

# Attach policy
resource "aws_iam_role_policy_attachment" "sagemaker_notebook_policy" {
  role       = aws_iam_role.sagemaker_notebook.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSageMakerFullAccess"
}

# Secrets for aurora connection
resource "aws_secretsmanager_secret" "aurora_connection" {
  name        = "${local.name_prefix}-aurora-connection"
  description = "Connection details for Aurora database read replica for SageMaker"

  tags = local.tags
}

resource "aws_secretsmanager_secret_version" "aurora_connection" {
  secret_id = aws_secretsmanager_secret.aurora_connection.id

  secret_string = jsonencode({
    engine   = "postgres"
    host     = var.aurora_endpoint
    port     = var.aurora_port
    database = var.database_name
    username = var.database_username
    password = var.database_password
  })
}

# Lifecycle configuration for auto-stopping idle notebooks
resource "aws_sagemaker_notebook_instance_lifecycle_configuration" "auto_stop" {
  count = var.enable_lifecycle_config ? 1 : 0
  name  = "${local.name_prefix}-auto-stop"

  on_start = base64encode(templatefile("${path.module}/scripts/on-start.sh", {
    secret_name = aws_secretsmanager_secret.aurora_connection.name
    region      = data.aws_region.current.name
  }))

  on_create = base64encode(templatefile("${path.module}/scripts/on-create.sh", {
    idle_time = var.auto_shutdown_idle_time
  }))
}

# SageMaker Notebook Instance
resource "aws_sagemaker_notebook_instance" "main" {
  name                   = "${local.name_prefix}-notebook"
  instance_type          = var.notebook_instance_type
  role_arn               = aws_iam_role.sagemaker_notebook.arn
  subnet_id              = var.subnet_id
  security_groups        = [aws_security_group.sagemaker_notebook.id]
  direct_internet_access = var.direct_internet_access

  lifecycle_config_name = var.enable_lifecycle_config ? aws_sagemaker_notebook_instance_lifecycle_configuration.auto_stop[0].name : null

  default_code_repository      = var.default_code_repository
  additional_code_repositories = var.additional_code_repositories

  root_access         = var.root_access
  platform_identifier = var.platform_identifier

  volume_size = var.volume_size
  kms_key_id  = var.kms_key_id

  tags = local.tags
}

# CloudWatch Log Group for SageMaker
resource "aws_cloudwatch_log_group" "sagemaker" {
  name              = "/aws/sagemaker/NotebookInstances/${local.name_prefix}-notebook"
  retention_in_days = var.log_retention_days

  tags = local.tags
}

# CloudWatch Alarm for notebook instance utilization
resource "aws_cloudwatch_metric_alarm" "notebook_cpu" {
  count               = var.enable_monitoring ? 1 : 0
  alarm_name          = "${local.name_prefix}-notebook-high-cpu"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/SageMaker"
  period              = 300
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "SageMaker notebook high CPU utilization"
  alarm_actions       = var.alarm_actions

  dimensions = {
    NotebookInstanceName = aws_sagemaker_notebook_instance.main.name
  }

  tags = local.tags
}

# Data sources
data "aws_region" "current" {}
data "aws_caller_identity" "current" {}
