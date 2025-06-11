# API Gateway module - variables.tf
variable "name_prefix" {
  description = "Prefix to use for all resource names"
  type        = string
}

variable "environment" {
  description = "Environment name (e.g. dev, staging, prod)"
  type        = string
}

variable "vpc_id" {
  description = "ID of the VPC"
  type        = string
}

variable "vpc_link_subnets" {
  description = "Subnet IDs to include in the VPC link (only used for HTTP APIs, not REST APIs)"
  type        = list(string)
  default     = []
}

variable "load_balancer_arn" {
  description = "ARN of the load balancer"
  type        = string
}

variable "load_balancer_dns_name" {
  description = "DNS name of the load balancer"
  type        = string
}

variable "stage_name" {
  description = "Name of the API Gateway stage"
  type        = string
  default     = "dev"
}

variable "logs_retention_in_days" {
  description = "Number of days to retain logs in CloudWatch"
  type        = number
  default     = 30
}

variable "tags" {
  description = "Additional tags for all resources"
  type        = map(string)
  default     = {}
}

variable "api_throttling_rate_limit" {
  description = "API Gateway default rate limit (requests per second)"
  type        = number
  default     = 100
}

variable "api_throttling_burst_limit" {
  description = "API Gateway default burst limit"
  type        = number
  default     = 200
}

variable "routes" {
  description = "List of API routes to create (path must start with /)"
  type = list(object({
    route_key = string
    methods   = list(string)
    path      = string
  }))
  default = []
}

# integration_uri variable removed - no longer needed for direct ALB connection

# Enhanced API management for third-party consumers
variable "enable_api_keys" {
  description = "Whether to enable API key authentication for the API"
  type        = bool
  default     = false
}

variable "api_keys" {
  description = "List of API keys to create"
  type = list(object({
    name        = string
    description = string
    enabled     = bool
  }))
  default = []
}

# variable "usage_plans" {
#   description = "List of API usage plans to create"
#   type = list(object({
#     name        = string
#     description = string
#     quota = object({
#       limit  = number
#       period = string # DAY, WEEK, or MONTH
#     })
#     throttle = object({
#       rate_limit  = number
#       burst_limit = number
#     })
#     # List of API key names (from api_keys) to associate with this usage plan
#     api_key_names = list(string)
#   }))
#   default = []
# }

variable "enable_waf" {
  description = "Whether to enable WAF for the API Gateway"
  type        = bool
  default     = false
}

variable "waf_rules" {
  description = "List of WAF rules to apply to the API Gateway"
  type = list(object({
    name     = string
    priority = number
    action   = string # ALLOW, BLOCK, COUNT
    # Add additional rule properties as needed
  }))
  default = []
}

variable "enable_request_validation" {
  description = "Whether to enable request validation for the API"
  type        = bool
  default     = false
}

variable "enable_cognito_authorizer" {
  description = "Whether to enable Cognito authorizer for the API"
  type        = bool
  default     = false
}

variable "cognito_user_pool_arn" {
  description = "ARN of the Cognito user pool to use for authorization"
  type        = string
  default     = ""
}

variable "enable_lambda_authorizer" {
  description = "Whether to enable Lambda authorizer for the API"
  type        = bool
  default     = false
}

variable "lambda_authorizer_arn" {
  description = "ARN of the Lambda function to use for authorization"
  type        = string
  default     = ""
}

variable "enable_detailed_metrics" {
  description = "Whether to enable detailed metrics for the API Gateway"
  type        = bool
  default     = true
}

variable "route_specific_throttling" {
  description = "Map of route keys to throttling settings"
  type = map(object({
    rate_limit  = number
    burst_limit = number
  }))
  default = {}
}
