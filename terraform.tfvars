# AWS Configuration
aws_region = "eu-west-2"
app_name   = "jao"
environment = "dev"

# Network Configuration
vpc_cidr               = "10.0.0.0/16"
availability_zones     = ["eu-west-2a", "eu-west-2b"]
private_subnet_cidrs   = ["10.0.1.0/24", "10.0.2.0/24"]
public_subnet_cidrs    = ["10.0.101.0/24", "10.0.102.0/24"]

# ECS Configuration
container_port = 8000
task_cpu    = 512
task_memory   = 4096
desired_count = 2
image_tag     = "latest"

# Environment Variables for Container
environment_variables = {
  LOG_LEVEL = "DEBUG"
}


# Database Access - ADD YOUR IP HERE
# This is what was missing and causing your connection issues
allowed_cidr_blocks = [
  "195.144.8.0/24",
  "51.149.8.0/24",
  "195.144.8.62/32"
]
# JAO Backend Configuration
jao_backend_superuser_username = "admin"
jao_backend_superuser_email    = "admin@example.com" 
jao_backend_superuser_password = "your-secure-password-here"

# External Service Configuration
oleeo_url = "your-oleeo-url-here"

# Storage Configuration
initialization_bucket = ""
aws_account_id       = ""

# Monitoring and Observability
performance_insights_enabled = false
enable_enhanced_monitoring   = false
create_cloudwatch_alarms     = false
enable_xray_tracing         = false
enable_detailed_metrics     = true

# API Configuration
enable_api_keys           = true
enable_api_monitoring     = true
enable_api_tracing        = false
api_rate_limit_default    = 100
api_burst_limit_default   = 200
enable_third_party_access = false
api_log_level            = "DEBUG"
enable_api_dashboard     = true

# Load Balancer Configuration
lb_deletion_protection = false
deletion_protection    = false
enable_lb_access_logs  = false
internal_lb           = true
lb_access_logs_bucket = ""
allowed_security_groups = []


# Admin Access
admin_allowed_cidrs = [
  "195.144.8.62/32"  # Same as database access
]

# Database Initialization
init_script = null

# VPC Endpoints Configuration
create_vpc_endpoints      = true
create_ecr_dkr_endpoint   = false
create_ecr_api_endpoint   = true
create_s3_endpoint        = true
create_logs_endpoint      = true

# Existing VPC Endpoints (if any)
existing_ecr_dkr_endpoint_id = ""
existing_ecr_api_endpoint_id = ""
existing_s3_endpoint_id      = ""
existing_logs_endpoint_id    = ""

# Redis Configuration
redis_auth_token                 = null
redis_transit_encryption_enabled = false

# Celery Configuration
enable_celery_services = true

# SageMaker Configuration
enable_sagemaker_environment = true
sagemaker_db_username       = "sagemaker_readonly"
sagemaker_db_password       = "your-secure-sagemaker-password-here"
                                                                       
