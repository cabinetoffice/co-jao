# Complete Aurora PostgreSQL with pgvector Example
# This example shows a complete deployment of the Aurora PostgreSQL module with pgvector

provider "aws" {
  region = "eu-west-2"
}

# Create a VPC for the database
module "vpc" {
  source = "terraform-aws-modules/vpc/aws"

  name = "pgvector-demo-vpc"
  cidr = "10.0.0.0/16"

  azs             = ["eu-west-2a", "eu-west-2b", "eu-west-2c"]
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]

  enable_nat_gateway = true
  single_nat_gateway = true
  
  tags = {
    Environment = "dev"
    Project     = "pgvector-demo"
  }
}

# Create an EC2 security group for client access
resource "aws_security_group" "client" {
  name        = "pgvector-client"
  description = "Security group for clients accessing PostgreSQL"
  vpc_id      = module.vpc.vpc_id
  
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  tags = {
    Environment = "dev"
    Project     = "pgvector-demo"
  }
}

# Create an SNS topic for database alerts
resource "aws_sns_topic" "db_alerts" {
  name = "pgvector-db-alerts"
}

# Create KMS key for encryption
resource "aws_kms_key" "db_encryption" {
  description             = "KMS key for pgvector database encryption"
  deletion_window_in_days = 7
  enable_key_rotation     = true
  
  tags = {
    Environment = "dev"
    Project     = "pgvector-demo"
  }
}

# Create an S3 bucket for initialization scripts
resource "aws_s3_bucket" "init_scripts" {
  bucket = "pgvector-init-scripts-${random_id.bucket_suffix.hex}"
  
  tags = {
    Environment = "dev"
    Project     = "pgvector-demo"
  }
}

# Random ID for unique bucket name
resource "random_id" "bucket_suffix" {
  byte_length = 4
}

# Create the Aurora PostgreSQL cluster with pgvector
module "aurora_pgvector" {
  source = "../../"  # Path to the aurora_pgvector module
  
  # Basic configuration
  app_name    = "pgvector-demo"
  environment = "dev"
  
  # Network configuration
  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets
  
  # Access configuration
  allowed_security_groups = [aws_security_group.client.id]
  allowed_cidr_blocks     = ["10.0.0.0/16"]  # Allow from within VPC
  
  # Database configuration
  database_name    = "vectordb"
  master_username  = "pgadmin"
  
  # Use PostgreSQL 15.4 which supports pgvector
  engine_version   = "15.4"
  
  # Serverless v2 (Provisioned with auto-scaling)
  use_serverless   = false
  instance_count   = 1
  min_capacity     = 0.5  # 0.5 RPUs
  max_capacity     = 4    # 4 RPUs
  
  # Backups and maintenance
  backup_retention_period = 7
  skip_final_snapshot     = true  # For demo purposes only
  deletion_protection     = false # For demo purposes only
  apply_immediately       = true
  
  # Security
  storage_encrypted = true
  kms_key_id        = aws_kms_key.db_encryption.arn
  enable_iam_auth   = true
  
  # Performance and monitoring
  performance_insights_enabled       = true
  performance_insights_retention_period = 7
  enhanced_monitoring_interval       = 60
  create_cloudwatch_alarms           = true
  cloudwatch_alarm_actions           = [aws_sns_topic.db_alerts.arn]
  
  # Additional pgvector specific parameters
  additional_parameters = [
    {
      name  = "pgvector.dimension"
      value = "1536"  # Dimension for OpenAI embeddings
    },
    {
      name  = "pgvector.probes"
      value = "10"    # Number of HNSW probes for search
    },
    {
      name  = "pgvector.ef_search"
      value = "40"    # HNSW search parameter
    },
    {
      name  = "shared_buffers"
      value = "{DBInstanceClassMemory/4}"  # 25% of memory for shared buffers
    },
    {
      name  = "max_connections"
      value = "200"  # Maximum number of concurrent connections
    }
  ]
  
  # Database initialization script (optional)
  init_script_bucket = aws_s3_bucket.init_scripts.id
  init_script        = "${path.module}/init.sql.tpl"
  
  # Tags
  tags = {
    Environment = "dev"
    Project     = "pgvector-demo"
    Service     = "vector-database"
    CostCenter  = "data-platform"
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

output "security_group_id" {
  description = "Security group ID for the Aurora cluster"
  value       = module.aurora_pgvector.security_group_id
}