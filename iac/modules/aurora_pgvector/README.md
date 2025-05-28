# Aurora PostgreSQL with pgvector Module

This Terraform module provisions an Amazon Aurora PostgreSQL cluster with pgvector support for vector embeddings and similarity search. The module is designed to be highly configurable, supporting both Serverless v1 and Provisioned with Serverless v2 scaling options.

## Features

- **pgvector Support**: Pre-configured with pgvector extension for vector storage and similarity searches
- **Flexible Deployment Options**: Support for Serverless and Provisioned deployments
- **Auto-scaling**: Configure min/max capacity based on workload
- **Security**: Built-in security groups, encryption at rest, and IAM authentication
- **Monitoring**: Enhanced monitoring and Performance Insights
- **Alarms**: CloudWatch alarms for key metrics
- **High Availability**: Multi-AZ support with reader endpoints
- **Backups**: Configurable backup retention and snapshot management
- **Initialization**: Support for database initialization scripts

## Usage

```hcl
module "postgres_vector_db" {
  source = "./modules/aurora_pgvector"

  app_name    = "my-application"
  environment = "dev"
  
  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnet_ids
  
  allowed_security_groups = [module.ecs.security_group_id]
  
  database_name = "vectordb"
  
  # Serverless v2 (Provisioned with auto-scaling)
  use_serverless = false
  min_capacity   = 0.5  # 0.5 RPUs
  max_capacity   = 8    # 8 RPUs
  
  # Performance and monitoring
  performance_insights_enabled   = true
  enhanced_monitoring_interval   = 60
  create_cloudwatch_alarms       = true
  cloudwatch_alarm_actions       = [aws_sns_topic.db_alerts.arn]
  
  # Additional pgvector specific parameters
  additional_parameters = [
    {
      name  = "pgvector.dimension"
      value = "1536"  # OpenAI embeddings dimension
    },
    {
      name  = "pgvector.probes"
      value = "10"
    }
  ]
  
  # Tags
  tags = {
    Service     = "vector-database"
    CostCenter  = "data-platform"
  }
}
```

## Enabling pgvector in PostgreSQL

After the Aurora cluster is deployed, you'll need to create the pgvector extension in your database:

```sql
CREATE EXTENSION IF NOT EXISTS vector;

-- Create a table with a vector column
CREATE TABLE items (
  id SERIAL PRIMARY KEY,
  embedding VECTOR(1536),  -- For OpenAI embeddings
  content TEXT,
  metadata JSONB
);

-- Create a HNSW index for fast similarity search
CREATE INDEX ON items USING hnsw (embedding vector_l2_ops);

-- Example similarity search query
SELECT content, embedding <-> '[0.1, 0.2, ...]'::vector AS distance
FROM items
ORDER BY distance
LIMIT 5;
```

## Input Variables

| Name | Description | Type | Default |
|------|-------------|------|---------|
| app_name | Name of the application | string | - |
| environment | Environment (e.g., dev, stage, prod) | string | - |
| name_prefix | Prefix for resource names | string | null |
| vpc_id | VPC ID for deployment | string | - |
| subnet_ids | List of subnet IDs | list(string) | - |
| database_name | Name of the default database | string | - |
| master_username | Username for the master DB user | string | "postgres" |
| master_password | Password for the master DB user (auto-generated if null) | string | null |
| use_serverless | Whether to use Serverless v1 or Provisioned with v2 scaling | bool | false |
| min_capacity | Minimum capacity units | number | 0.5 |
| max_capacity | Maximum capacity units | number | 4 |
| instance_count | Number of DB instances (Provisioned only) | number | 1 |
| engine_version | PostgreSQL engine version | string | "15.4" |
| storage_encrypted | Whether to encrypt storage | bool | true |
| enable_iam_auth | Enable IAM database authentication | bool | false |
| apply_immediately | Apply changes immediately | bool | false |
| backup_retention_period | Backup retention days | number | 7 |
| deletion_protection | Enable deletion protection | bool | true |
| create_cloudwatch_alarms | Create CloudWatch alarms | bool | false |
| create_route53_record | Create Route53 DNS record | bool | false |
| [See variables.tf for the complete list]

## Outputs

| Name | Description |
|------|-------------|
| cluster_id | Aurora cluster identifier |
| cluster_endpoint | Writer endpoint for the cluster |
| reader_endpoint | Reader endpoint for the cluster |
| database_name | Name of the database |
| master_username | Master username |
| connection_string | PostgreSQL connection string |
| jdbc_connection_string | JDBC connection string |
| password_secret_arn | ARN of the password secret (if auto-generated) |
| security_group_id | ID of the security group |
| [See outputs.tf for the complete list]

## Version Requirements

- Terraform >= 1.0
- AWS Provider >= 4.0

## Notes

- For pgvector support, use Aurora PostgreSQL 13.9 or higher
- For production environments, consider using multiple instances for high availability
- Fine-tune parameter group settings for your specific workload
- Monitor vector index size and memory usage as they grow with data

## License

MIT