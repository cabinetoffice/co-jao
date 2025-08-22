# SageMaker Data Science Environment Setup

This guide explains how to set up a SageMaker environment with access to a read replica of your Aurora PostgreSQL database for data science and analytics work.

## Overview

The setup includes:
- **Aurora PostgreSQL Read Replica**: A dedicated read-only instance for data science workloads
- **SageMaker Notebook Instance**: Jupyter environment for data analysis and model development
- **Secure Database Connection**: Credentials managed via AWS Secrets Manager
- **Cost Controls**: Auto-stop for idle notebooks and monitoring
- **Data Storage**: Dedicated S3 bucket for datasets and models

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                           VPC                                    │
│                                                                  │
│  ┌──────────────────┐        ┌──────────────────────────┐      │
│  │ Aurora Cluster   │        │ SageMaker Notebook       │      │
│  │                  │        │                          │      │
│  │ ┌──────────────┐ │        │ - Jupyter Lab           │      │
│  │ │ Primary      │ │        │ - Python Environment     │      │
│  │ └──────────────┘ │        │ - DB Connection Helper  │      │
│  │                  │        └───────────┬──────────────┘      │
│  │ ┌──────────────┐ │                    │                     │
│  │ │ Read Replica │◄├────────────────────┘                     │
│  │ │(Data Science)│ │         Secure Connection                │
│  │ └──────────────┘ │         via Security Groups              │
│  └──────────────────┘                                          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                                    │
                        ┌───────────▼──────────┐
                        │   Secrets Manager    │
                        │ (DB Credentials)     │
                        └──────────────────────┘
                                    │
                        ┌───────────▼──────────┐
                        │    S3 Data Bucket    │
                        │ (Datasets & Models)  │
                        └──────────────────────┘
```

## Prerequisites

1. **Existing Infrastructure**:
   - Aurora PostgreSQL cluster running
   - VPC with private subnets configured
   - ECS services deployed (backend/frontend)

2. **AWS Permissions**:
   - Admin access or specific permissions for:
     - RDS (modify clusters, create instances)
     - SageMaker (create notebook instances)
     - IAM (create roles and policies)
     - Secrets Manager (create secrets)
     - S3 (create buckets)

3. **Terraform Setup**:
   - Terraform >= 1.0
   - AWS provider ~> 4.0
   - Backend configured for state management

## Implementation Steps

### Step 1: Create Database User for Data Science

First, create a read-only database user for SageMaker access:

```sql
-- Connect to your Aurora database as admin
CREATE USER sagemaker_readonly WITH PASSWORD 'secure_password_here';

-- Grant connect privilege
GRANT CONNECT ON DATABASE your_database TO sagemaker_readonly;

-- Grant usage on schemas
GRANT USAGE ON SCHEMA public TO sagemaker_readonly;
GRANT USAGE ON SCHEMA your_schema TO sagemaker_readonly;

-- Grant select on all tables
GRANT SELECT ON ALL TABLES IN SCHEMA public TO sagemaker_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA your_schema TO sagemaker_readonly;

-- Grant select on future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO sagemaker_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA your_schema GRANT SELECT ON TABLES TO sagemaker_readonly;
```

### Step 2: Update Variables

Create or update your `terraform.tfvars` file:

```hcl
# Enable SageMaker environment
enable_sagemaker_environment = true
enable_data_science_replica = true

# Database credentials for SageMaker
sagemaker_db_username = "sagemaker_readonly"
sagemaker_db_password = "secure_password_here"  # Use AWS Secrets Manager in production

# SageMaker configuration
sagemaker_instance_type = "ml.t3.xlarge"  # Adjust based on workload
sagemaker_idle_timeout_minutes = 120      # Auto-stop after 2 hours

# Data team users (optional)
data_scientist_users = [
  "data-scientist-1",
  "data-scientist-2"
]

# Optional: Git repository with your analysis code
sagemaker_git_repository = "https://github.com/your-org/data-science-repo.git"
```

### Step 3: Apply Terraform Configuration

1. **Initialize Terraform** (if not already done):
   ```bash
   cd co/jao-work/co-jao/iac
   terraform init
   ```

2. **Plan the changes**:
   ```bash
   terraform plan -var-file=terraform.tfvars
   ```

3. **Review the plan** carefully, especially:
   - Aurora read replica configuration
   - SageMaker notebook instance settings
   - Security group rules
   - IAM roles and policies

4. **Apply the configuration**:
   ```bash
   terraform apply -var-file=terraform.tfvars
   ```

5. **Save the outputs**:
   ```bash
   terraform output -json > sagemaker_outputs.json
   ```

### Step 4: Access the SageMaker Notebook

1. **Get the notebook URL** from Terraform output:
   ```bash
   terraform output sagemaker_setup
   ```

2. **Access via AWS Console**:
   - Navigate to SageMaker > Notebook instances
   - Find your notebook instance (e.g., `jao-dev-sagemaker-notebook`)
   - Click "Open JupyterLab" or "Open Jupyter"

3. **Or use AWS CLI**:
   ```bash
   aws sagemaker create-presigned-notebook-instance-url \
     --notebook-instance-name $(terraform output -raw sagemaker_notebook_name) \
     --region eu-west-2
   ```

### Step 5: Verify Database Connection

Once in the notebook:

1. Open the pre-configured notebook: `Database_Connection_Examples.ipynb`

2. Test the connection:
   ```python
   from db_connection import db, test_connection
   
   # Test connection
   test_connection()
   
   # List all tables
   tables = db.query("""
       SELECT table_schema, table_name 
       FROM information_schema.tables 
       WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
       ORDER BY table_schema, table_name
   """)
   print(tables)
   ```

3. Run your first query:
   ```python
   # Example: Get row counts for all tables
   for _, row in tables.iterrows():
       schema = row['table_schema']
       table = row['table_name']
       count = db.query(f"SELECT COUNT(*) as count FROM {schema}.{table}")
       print(f"{schema}.{table}: {count['count'][0]} rows")
   ```

## Configuration Details

### Security Configuration

The setup implements multiple security layers:

1. **Network Isolation**:
   - SageMaker runs in private subnets
   - No direct internet access in production
   - Security groups restrict database access

2. **Access Control**:
   - IAM roles limit SageMaker permissions
   - Database user has read-only access
   - Secrets Manager stores credentials

3. **Encryption**:
   - EBS volumes encrypted (optional KMS)
   - S3 bucket encryption enabled
   - Database connections use SSL

### Cost Management

Built-in cost controls:

1. **Auto-stop Idle Notebooks**:
   - Default: 120 minutes of inactivity
   - Configurable per environment
   - Saves significant compute costs

2. **Resource Sizing**:
   - Dev: ml.t3.medium (2 vCPU, 4 GB RAM)
   - Staging: ml.t3.large (2 vCPU, 8 GB RAM)
   - Prod: ml.t3.xlarge (4 vCPU, 16 GB RAM)

3. **Monitoring**:
   - CloudWatch dashboards track usage
   - Alarms for high utilization
   - Cost alerts available

### Database Performance

The read replica is optimized for analytics:

```hcl
# PostgreSQL parameters tuned for analytics
work_mem = "256MB"                    # Memory for sorting
effective_cache_size = "4GB"          # Query planner hint
random_page_cost = "1.1"              # SSD optimization
max_parallel_workers_per_gather = "4" # Parallel queries
```

## Common Use Cases

### 1. Data Exploration and Analysis
```python
import pandas as pd
from db_connection import db

# Load data
df = db.query("SELECT * FROM orders WHERE created_at > '2024-01-01'")

# Analyze
print(df.describe())
df.groupby('status').agg({'total': 'sum', 'id': 'count'})
```

### 2. Feature Engineering for ML
```python
# Create features from multiple tables
features_query = """
SELECT 
    u.id,
    u.created_at,
    COUNT(DISTINCT o.id) as order_count,
    AVG(o.total) as avg_order_value,
    MAX(o.created_at) as last_order_date
FROM users u
LEFT JOIN orders o ON u.id = o.user_id
GROUP BY u.id, u.created_at
"""

features_df = db.query(features_query)
```

### 3. Model Training Data Preparation
```python
# Save training data to S3
training_data = db.query("SELECT * FROM training_dataset")
training_data.to_parquet('s3://jao-dev-data-science/training/dataset.parquet')
```

### 4. Batch Predictions
```python
# Load model and make predictions
import joblib

model = joblib.load('s3://jao-dev-data-science/models/model.pkl')
new_data = db.query("SELECT * FROM scoring_dataset")
predictions = model.predict(new_data)
```

## Monitoring and Troubleshooting

### CloudWatch Dashboards

Monitor your environment at:
- SageMaker metrics: CPU, memory, disk usage
- Aurora metrics: Connections, query latency, throughput
- S3 metrics: Request count, data transfer

### Common Issues and Solutions

1. **Database Connection Fails**:
   - Check security group rules
   - Verify credentials in Secrets Manager
   - Ensure read replica is running
   - Check VPC connectivity

2. **Notebook Won't Start**:
   - Check CloudWatch logs: `/aws/sagemaker/NotebookInstances/`
   - Verify IAM role permissions
   - Check subnet has available IPs

3. **Slow Queries**:
   - Check Aurora performance insights
   - Review query execution plans
   - Consider increasing instance size
   - Add appropriate indexes

4. **Auto-stop Not Working**:
   - Check lifecycle configuration
   - Verify cron job: `crontab -u ec2-user -l`
   - Review logs: `/home/ec2-user/SageMaker/auto-stop.log`

## Best Practices

### Data Science Workflow

1. **Development**:
   - Use dev environment for experimentation
   - Keep notebooks organized in folders
   - Version control important notebooks

2. **Data Management**:
   - Cache frequently used data locally
   - Use parquet format for better performance
   - Partition large datasets in S3

3. **Query Optimization**:
   - Limit result sets during exploration
   - Use sampling for large tables
   - Create materialized views for complex queries

4. **Security**:
   - Never hardcode credentials
   - Use IAM roles instead of keys
   - Rotate passwords regularly

### Resource Management

1. **Cost Optimization**:
   - Stop notebooks when not in use
   - Use smaller instances for development
   - Clean up old S3 data regularly

2. **Performance**:
   - Monitor query performance
   - Scale read replica as needed
   - Use caching strategically

3. **Collaboration**:
   - Share notebooks via Git
   - Document analysis thoroughly
   - Use consistent naming conventions

## Maintenance

### Regular Tasks

1. **Weekly**:
   - Review CloudWatch dashboards
   - Check for idle resources
   - Monitor costs

2. **Monthly**:
   - Review and optimize slow queries
   - Clean up old S3 data
   - Update documentation

3. **Quarterly**:
   - Review instance sizing
   - Audit user access
   - Update dependencies

### Updating the Environment

To update SageMaker or database configuration:

1. Modify variables in `terraform.tfvars`
2. Run `terraform plan` to review changes
3. Apply during maintenance window
4. Test connectivity and performance

### Scaling Considerations

As your data science needs grow:

1. **More Users**: Add to `data_scientist_users` list
2. **More Power**: Increase `sagemaker_instance_type`
3. **More Storage**: Increase `volume_size_gb`
4. **Better DB Performance**: Scale `data_science_replica_instance_class`

## Security Considerations

### Data Access

- Read-only access prevents accidental data modification
- Row-level security can be implemented if needed
- Audit logs track all database queries

### Network Security

- Private subnets prevent internet exposure
- Security groups limit access to specific resources
- VPC endpoints keep traffic within AWS

### Compliance

- All data stays within your VPC
- Encryption at rest and in transit
- CloudWatch logs for audit trails

## Support and Resources

### Documentation
- [AWS SageMaker Documentation](https://docs.aws.amazon.com/sagemaker/)
- [Aurora PostgreSQL Guide](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/)
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/)

### Internal Resources
- CloudWatch Dashboard: `jao-{environment}-data-science`
- Logs: `/aws/sagemaker/NotebookInstances/jao-{environment}-sagemaker-notebook`
- S3 Bucket: `jao-{environment}-data-science`

### Troubleshooting Contacts
- Infrastructure Team: For VPC, networking issues
- Database Team: For Aurora performance, access issues
- Security Team: For IAM, access control issues

## Appendix

### Complete Terraform Command Reference

```bash
# Initialize
terraform init

# Format code
terraform fmt -recursive

# Validate configuration
terraform validate

# Plan with specific environment
terraform plan -var="environment=dev" -out=plan.tfplan

# Apply saved plan
terraform apply plan.tfplan

# Destroy resources (careful!)
terraform destroy -var="environment=dev"

# Show current state
terraform show

# List resources
terraform state list

# Get specific output
terraform output sagemaker_setup
```

### SQL Permission Reference

```sql
-- Minimum required permissions for read-only access
GRANT CONNECT ON DATABASE dbname TO username;
GRANT USAGE ON SCHEMA schema_name TO username;
GRANT SELECT ON ALL TABLES IN SCHEMA schema_name TO username;
GRANT SELECT ON ALL SEQUENCES IN SCHEMA schema_name TO username;

-- Optional: Grant access to specific schemas only
GRANT USAGE ON SCHEMA analytics TO username;
GRANT SELECT ON ALL TABLES IN SCHEMA analytics TO username;

-- Check current permissions
SELECT * FROM information_schema.role_table_grants 
WHERE grantee = 'sagemaker_readonly';
```
