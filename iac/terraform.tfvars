# Override variables to work around resources that already exist

# Resource existence flags - COMMENTED OUT FOR SIMPLIFICATION
# skip_ecr_creation = true
aws_account_id = "860619597616"

# Skip creating resources that already exist - COMMENTED OUT FOR SIMPLIFICATION
# skip_iam_role_creation        = false
# skip_vpc_creation             = false
# skip_cloudwatch_creation      = false
# skip_s3_bucket_creation       = false
# skip_param_group_creation     = false
# skip_secret_creation          = true
# skip_policy_creation          = false

# Existing IAM role ARNs - COMMENTED OUT FOR SIMPLIFICATION
# existing_task_execution_role_arn = "arn:aws:iam::860619597616:role/ipa-scout-preprod-backend-ecs-task-role"
# existing_frontend_execution_role_arn = "arn:aws:iam::860619597616:role/ipa-scout-preprod-frontend-ecs-task-role"
# existing_frontend_task_role_arn = "arn:aws:iam::860619597616:role/ipa-scout-preprod-frontend-ecs-task-role"

# Disable features requiring enhanced permissions
enable_enhanced_monitoring   = false
performance_insights_enabled = false
enable_xray_tracing          = false
create_cloudwatch_alarms     = false
enable_api_keys              = false
enable_detailed_metrics      = false

# Use internal load balancer to avoid public exposure
internal_lb = false

# VPC Endpoints Configuration - Resolve ECR Docker endpoint conflict
create_vpc_endpoints    = true  # Enable VPC endpoints
create_ecr_dkr_endpoint = false # Existing endpoint already present
create_ecr_api_endpoint = true  # Create missing ECR API endpoint
create_s3_endpoint      = true  # Create S3 Gateway endpoint for ECR layers
create_logs_endpoint    = true  # Create CloudWatch Logs endpoint

# Self-manage the initialization
initialization_bucket = "jao-dev-initialization"
init_script           = null

# VPC configuration
availability_zones   = ["eu-west-2a", "eu-west-2b"]
vpc_cidr             = "10.0.0.0/16"
private_subnet_cidrs = ["10.0.1.0/24", "10.0.2.0/24"]
public_subnet_cidrs  = ["10.0.101.0/24", "10.0.102.0/24"]

# Reduce resource requirements
task_cpu      = 256
task_memory   = 512
desired_count = 1

# Prevent any deletion protection
lb_deletion_protection = false
deletion_protection    = false
enable_lb_access_logs  = false

# Django admin creds
jao_backend_superuser_username = "jao-admin"
jao_backend_superuser_password = "password"
jao_backend_superuser_email    = "jao-admin@example.com"

oleeo_url = "mssql+pyodbc://JAO_admin:85h0br7YOr@gridpatpreprodrdssqlstack-rdsdbinstance-kdljxcoy9jmr.cvgiwsy9mkjc.eu-west-2.rds.amazonaws.com/DART_Dev?driver=ODBC+Driver+17+for+SQL+Server"

# Enable Celery services
enable_celery_services = true

# Admin IP whitelisting - restrict Django admin access to specific IPs
# Replace with your actual IP addresses/CIDR blocks
admin_allowed_cidrs = [
  "195.144.8.0/24",
  "51.149.8.0/24"
]
