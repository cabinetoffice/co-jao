# outputs.tf - SageMaker Notebook Instance Module Outputs

output "notebook_instance_name" {
  description = "Name of the SageMaker notebook instance"
  value       = aws_sagemaker_notebook_instance.main.name
}

output "notebook_instance_arn" {
  description = "ARN of the SageMaker notebook instance"
  value       = aws_sagemaker_notebook_instance.main.arn
}

output "notebook_instance_url" {
  description = "URL to access the SageMaker notebook instance"
  value       = "https://${aws_sagemaker_notebook_instance.main.name}.notebook.${data.aws_region.current.name}.sagemaker.aws"
}

output "security_group_id" {
  description = "Security group ID for the SageMaker notebook instance"
  value       = aws_security_group.sagemaker_notebook.id
}

output "iam_role_arn" {
  description = "ARN of the IAM role for the SageMaker notebook instance"
  value       = aws_iam_role.sagemaker_notebook.arn
}

output "iam_role_name" {
  description = "Name of the IAM role for the SageMaker notebook instance"
  value       = aws_iam_role.sagemaker_notebook.name
}

output "aurora_connection_secret_arn" {
  description = "ARN of the Secrets Manager secret containing Aurora connection details"
  value       = aws_secretsmanager_secret.aurora_connection.arn
}

output "aurora_connection_secret_name" {
  description = "Name of the Secrets Manager secret containing Aurora connection details"
  value       = aws_secretsmanager_secret.aurora_connection.name
}

output "cloudwatch_log_group_name" {
  description = "Name of the CloudWatch log group for SageMaker notebook"
  value       = aws_cloudwatch_log_group.sagemaker.name
}

output "cloudwatch_log_group_arn" {
  description = "ARN of the CloudWatch log group for SageMaker notebook"
  value       = aws_cloudwatch_log_group.sagemaker.arn
}

output "lifecycle_config_name" {
  description = "Name of the lifecycle configuration attached to the notebook instance"
  value       = var.enable_lifecycle_config ? aws_sagemaker_notebook_instance_lifecycle_configuration.auto_stop[0].name : null
}

output "notebook_configuration" {
  description = "Configuration details of the notebook instance"
  value = {
    instance_type          = var.notebook_instance_type
    volume_size            = var.volume_size
    direct_internet_access = var.direct_internet_access
    root_access            = var.root_access
    auto_shutdown_minutes  = var.auto_shutdown_idle_time
  }
}

output "data_bucket_info" {
  description = "Information about the S3 bucket for data science work"
  value = {
    bucket_name = var.data_bucket_name
    bucket_arn  = var.data_bucket_arn
  }
}

output "connection_instructions" {
  description = "Instructions for connecting to the Aurora database from SageMaker"
  value       = <<-EOT
    ========================================
    SageMaker Notebook Instance Setup Complete
    ========================================

    Access your notebook instance:
    ${try("https://${aws_sagemaker_notebook_instance.main.name}.notebook.${data.aws_region.current.name}.sagemaker.aws", "URL will be available after creation")}

    The notebook instance has been configured with:
    - Database connection helper script (db_connection.py)
    - Example notebook (Database_Connection_Examples.ipynb)
    - Auto-stop after ${var.auto_shutdown_idle_time} minutes of inactivity

    Database Connection:
    --------------------
    The database credentials are securely stored in AWS Secrets Manager.
    Secret Name: ${aws_secretsmanager_secret.aurora_connection.name}

    To connect from your notebook:

    ```python
    from db_connection import db, query, test_connection

    # Test the connection
    test_connection()

    # Run a query
    df = query("SELECT * FROM your_table LIMIT 10")
    ```

    Available Helper Functions:
    - db.query(sql): Execute SELECT queries and return pandas DataFrame
    - db.execute(sql): Execute INSERT/UPDATE/DELETE commands
    - db.test_connection(): Test database connectivity
    - db.get_connection_info(): Get connection details (without password)

    Data Storage:
    ------------
    S3 Bucket: ${var.data_bucket_name}
    Use this bucket for storing datasets, models, and results.

    Auto-Stop Configuration:
    ------------------------
    ${var.auto_shutdown_idle_time > 0 ? "Instance will auto-stop after ${var.auto_shutdown_idle_time} minutes of inactivity" : "Auto-stop is disabled"}
    Check /home/ec2-user/SageMaker/AUTO_STOP_INFO.md for details

    Security Notes:
    --------------
    - Database access is read-only via the read replica
    - Credentials are managed via AWS Secrets Manager
    - Network traffic is isolated within your VPC
    - Direct internet access is ${var.direct_internet_access}
  EOT
}

output "quickstart_code" {
  description = "Python code snippet to quickly connect to the database"
  value       = <<-PYTHON
    # Quick start code for database connection
    # Run this in your SageMaker notebook

    from db_connection import db
    import pandas as pd

    # Test connection
    db.test_connection()

    # List all tables
    tables = db.query("""
        SELECT table_schema, table_name
        FROM information_schema.tables
        WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
        ORDER BY table_schema, table_name
    """)
    print(tables)

    # Example query (update with your table name)
    # df = db.query("SELECT * FROM your_schema.your_table LIMIT 100")
    # df.head()
  PYTHON
}

output "troubleshooting" {
  description = "Troubleshooting information"
  value       = <<-EOT
    Troubleshooting Guide:
    =====================

    If notebook won't start:
    - Check CloudWatch logs: ${aws_cloudwatch_log_group.sagemaker.name}
    - Verify IAM role permissions
    - Check VPC/subnet configuration

    If database connection fails:
    - Verify security group rules allow connection
    - Check Secrets Manager permissions
    - Ensure read replica is running
    - Verify VPC connectivity

    If auto-stop isn't working:
    - Check /home/ec2-user/SageMaker/auto-stop.log
    - Verify lifecycle configuration is attached
    - Check cron job: crontab -u ec2-user -l

    AWS CLI commands:
    - Start instance: aws sagemaker start-notebook-instance --notebook-instance-name ${aws_sagemaker_notebook_instance.main.name}
    - Stop instance: aws sagemaker stop-notebook-instance --notebook-instance-name ${aws_sagemaker_notebook_instance.main.name}
    - Get status: aws sagemaker describe-notebook-instance --notebook-instance-name ${aws_sagemaker_notebook_instance.main.name}
  EOT
}
