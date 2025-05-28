# LocalStack configuration for local development and testing

# This provider will be used conditionally based on localstack_enabled variable
provider "aws" {
  alias = "localstack"
  
  access_key                  = "test"
  secret_key                  = "test"
  region                      = var.aws_region
  s3_use_path_style           = true
  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_requesting_account_id  = true

  # LocalStack endpoints
  endpoints {
    apigateway       = "http://localhost:4566"
    apigatewayv2     = "http://localhost:4566"
    cloudformation   = "http://localhost:4566"
    cloudwatch       = "http://localhost:4566"
    dynamodb         = "http://localhost:4566"
    ec2              = "http://localhost:4566"
    ecr              = "http://localhost:4566"
    ecs              = "http://localhost:4566"
    iam              = "http://localhost:4566"
    lambda           = "http://localhost:4566"
    route53          = "http://localhost:4566"
    s3               = "http://localhost:4566"
    secretsmanager   = "http://localhost:4566"
    ses              = "http://localhost:4566"
    sns              = "http://localhost:4566"
    sqs              = "http://localhost:4566"
    ssm              = "http://localhost:4566"
    stepfunctions    = "http://localhost:4566"
    sts              = "http://localhost:4566"
  }
}

# Standard AWS provider for real deployments
provider "aws" {
  alias  = "standard"
  region = var.aws_region
}

# Default provider selection based on environment
provider "aws" {
  region = var.aws_region
  
  # Use settings from localstack provider if localstack is enabled
  access_key                  = var.localstack_enabled ? "test" : null
  secret_key                  = var.localstack_enabled ? "test" : null
  s3_use_path_style           = var.localstack_enabled ? true : null
  skip_credentials_validation = var.localstack_enabled ? true : null
  skip_metadata_api_check     = var.localstack_enabled ? true : null
  skip_requesting_account_id  = var.localstack_enabled ? true : null
  
  dynamic "endpoints" {
    for_each = var.localstack_enabled ? [1] : []
    content {
      apigateway       = "http://localhost:4566"
      apigatewayv2     = "http://localhost:4566"
      cloudformation   = "http://localhost:4566"
      cloudwatch       = "http://localhost:4566"
      dynamodb         = "http://localhost:4566"
      ec2              = "http://localhost:4566"
      ecr              = "http://localhost:4566"
      ecs              = "http://localhost:4566"
      iam              = "http://localhost:4566"
      lambda           = "http://localhost:4566"
      route53          = "http://localhost:4566"
      s3               = "http://localhost:4566"
      secretsmanager   = "http://localhost:4566"
      ses              = "http://localhost:4566"
      sns              = "http://localhost:4566"
      sqs              = "http://localhost:4566"
      ssm              = "http://localhost:4566"
      stepfunctions    = "http://localhost:4566"
      sts              = "http://localhost:4566"
    }
  }
}

# LocalStack-specific variables
variable "localstack_enabled" {
  description = "Whether to use LocalStack for local development"
  type        = bool
  default     = false
}