provider "aws" {
  region = "eu-west-2"
}

# Get default VPC and subnets
data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "private" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

# Create a simple security group for database access
resource "aws_security_group" "db_access" {
  name        = "pgvector-simple-access"
  description = "Allow access to PostgreSQL database"
  vpc_id      = data.aws_vpc.default.id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "pgvector-simple-access"
  }
}

# Create the Aurora PostgreSQL cluster with pgvector
module "aurora_pgvector" {
  source = "../../" # Path to the aurora_pgvector module

  # Basic configuration
  app_name    = "simple-vector-db"
  environment = "dev"

  # Network configuration
  vpc_id     = data.aws_vpc.default.id
  subnet_ids = data.aws_subnets.private.ids

  # Security group access
  allowed_security_groups = [aws_security_group.db_access.id]

  # Database configuration
  database_name   = "vectordb"
  master_username = "dbadmin"

  # Serverless v2 settings for cost-effective development
  use_serverless = false # Use provisioned with serverless v2 scaling
  instance_count = 1     # Single instance for development
  min_capacity   = 0.5   # Minimum capacity of 0.5 RPUs
  max_capacity   = 2     # Maximum capacity of 2 RPUs

  # Development settings to reduce costs
  skip_final_snapshot = true
  deletion_protection = false
  apply_immediately   = true

  # Basic monitoring
  performance_insights_enabled = true

  # Vector-specific parameters
  additional_parameters = [
    {
      name  = "pgvector.dimension"
      value = "1536" # OpenAI embedding dimension
    }
  ]

  # Development tags
  tags = {
    Project     = "vector-db-demo"
    Environment = "development"
  }
}

# Outputs
output "cluster_endpoint" {
  description = "Aurora cluster endpoint"
  value       = module.aurora_pgvector.cluster_endpoint
}

output "database_name" {
  description = "Name of the database"
  value       = module.aurora_pgvector.database_name
}

output "connection_string" {
  description = "PostgreSQL connection string (without credentials)"
  value       = module.aurora_pgvector.connection_string
}

output "master_username" {
  description = "Master username for the database"
  value       = module.aurora_pgvector.master_username
}

output "password_secret_arn" {
  description = "ARN of the secret containing the database password"
  value       = module.aurora_pgvector.password_secret_arn
}
