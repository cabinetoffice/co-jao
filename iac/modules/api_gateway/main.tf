# API Gateway module - main.tf
locals {
  # Resource naming
  name = "${var.name_prefix}-${var.environment}"

  # Common tags for all resources
  common_tags = merge(
    var.tags,
    {
      Environment = var.environment
      ManagedBy   = "terraform"
      Name        = local.name
    }
  )

  # Default routes if none are provided
  default_routes = [
    {
      route_key = "ANY /{proxy+}"
      methods   = ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]
      path      = "/{proxy+}"
    },
    {
      route_key = "GET /health"
      methods   = ["GET"]
      path      = "/health"
    }
  ]

  # Use provided routes or defaults
  routes = length(var.routes) > 0 ? var.routes : local.default_routes
}

# Data source for current region
data "aws_region" "current" {}

# HTTP API Gateway (APIGatewayV2)
resource "aws_apigatewayv2_api" "main" {
  name          = "${local.name}-api"
  protocol_type = "HTTP"

  tags = merge(
    local.common_tags,
    {
      Name = "${local.name}-api"
    }
  )
}

# Create VPC Link for API Gateway to communicate with ALB in the VPC
resource "aws_apigatewayv2_vpc_link" "main" {
  name               = "${local.name}-vpc-link"
  security_group_ids = []
  subnet_ids         = var.vpc_link_subnets

  tags = merge(
    local.common_tags,
    {
      Name = "${local.name}-vpc-link"
    }
  )
}

# API Gateway stage
resource "aws_apigatewayv2_stage" "main" {
  api_id      = aws_apigatewayv2_api.main.id
  name        = var.stage_name
  auto_deploy = true

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api_gateway.arn
    format = jsonencode({
      requestId               = "$context.requestId"
      ip                      = "$context.identity.sourceIp"
      requestTime             = "$context.requestTime"
      httpMethod              = "$context.httpMethod"
      path                    = "$context.path"
      routeKey                = "$context.routeKey"
      status                  = "$context.status"
      protocol                = "$context.protocol"
      responseLength          = "$context.responseLength"
      integrationErrorMessage = "$context.integrationErrorMessage"
    })
  }

  default_route_settings {
    detailed_metrics_enabled = var.enable_detailed_metrics
    throttling_burst_limit   = var.api_throttling_burst_limit
    throttling_rate_limit    = var.api_throttling_rate_limit
  }

  tags = merge(
    local.common_tags,
    {
      Name = "${local.name}-${var.stage_name}-stage"
    }
  )
}

# CloudWatch log group for API Gateway
resource "aws_cloudwatch_log_group" "api_gateway" {
  name              = "/aws/apigateway/${local.name}-api"
  retention_in_days = var.logs_retention_in_days

  tags = merge(
    local.common_tags,
    {
      Name = "${local.name}-api-log-group"
    }
  )
}

# API Gateway integration with ALB
resource "aws_apigatewayv2_integration" "main" {
  api_id                 = aws_apigatewayv2_api.main.id
  integration_type       = "HTTP_PROXY"
  integration_method     = "ANY"
  integration_uri        = var.integration_uri
  connection_type        = "VPC_LINK"
  connection_id          = aws_apigatewayv2_vpc_link.main.id
  payload_format_version = "1.0"
  timeout_milliseconds   = 30000
}

# HTTP API Gateway routes
resource "aws_apigatewayv2_route" "routes" {
  count     = length(local.routes)
  api_id    = aws_apigatewayv2_api.main.id
  route_key = local.routes[count.index].route_key
  target    = "integrations/${aws_apigatewayv2_integration.main.id}"
}

# For API key functionality, we need to use REST API Gateway
# REST API Gateway (APIGatewayV1) for API key management
resource "aws_api_gateway_rest_api" "api_keys_api" {
  count = var.enable_api_keys ? 1 : 0

  name        = "${local.name}-keys-api"
  description = "REST API for API key management"

  endpoint_configuration {
    types = ["REGIONAL"]
  }

  tags = local.common_tags
}

# API resource for validation
resource "aws_api_gateway_resource" "validate" {
  count = var.enable_api_keys ? 1 : 0

  rest_api_id = aws_api_gateway_rest_api.api_keys_api[0].id
  parent_id   = aws_api_gateway_rest_api.api_keys_api[0].root_resource_id
  path_part   = "validate"
}

# Method for validation
resource "aws_api_gateway_method" "validate" {
  count = var.enable_api_keys ? 1 : 0

  rest_api_id      = aws_api_gateway_rest_api.api_keys_api[0].id
  resource_id      = aws_api_gateway_resource.validate[0].id
  http_method      = "GET"
  authorization    = "NONE"
  api_key_required = true
}

# Integration for validation
resource "aws_api_gateway_integration" "validate" {
  count = var.enable_api_keys ? 1 : 0

  rest_api_id = aws_api_gateway_rest_api.api_keys_api[0].id
  resource_id = aws_api_gateway_resource.validate[0].id
  http_method = aws_api_gateway_method.validate[0].http_method
  type        = "MOCK"

  request_templates = {
    "application/json" = jsonencode({ statusCode = 200 })
  }
}

# Method response
resource "aws_api_gateway_method_response" "validate" {
  count = var.enable_api_keys ? 1 : 0

  rest_api_id = aws_api_gateway_rest_api.api_keys_api[0].id
  resource_id = aws_api_gateway_resource.validate[0].id
  http_method = aws_api_gateway_method.validate[0].http_method
  status_code = "200"

  response_models = {
    "application/json" = "Empty"
  }
}

# Integration response
resource "aws_api_gateway_integration_response" "validate" {
  count = var.enable_api_keys ? 1 : 0

  rest_api_id = aws_api_gateway_rest_api.api_keys_api[0].id
  resource_id = aws_api_gateway_resource.validate[0].id
  http_method = aws_api_gateway_method.validate[0].http_method
  status_code = aws_api_gateway_method_response.validate[0].status_code

  response_templates = {
    "application/json" = jsonencode({
      message = "API key is valid",
      valid   = true
    })
  }
}

# REST API Deployment
resource "aws_api_gateway_deployment" "api_keys_api" {
  count = var.enable_api_keys ? 1 : 0

  depends_on = [
    aws_api_gateway_integration.validate
  ]

  rest_api_id = aws_api_gateway_rest_api.api_keys_api[0].id

  lifecycle {
    create_before_destroy = true
  }
}

# REST API Stage
resource "aws_api_gateway_stage" "api_keys_api" {
  count = var.enable_api_keys ? 1 : 0

  deployment_id = aws_api_gateway_deployment.api_keys_api[0].id
  rest_api_id   = aws_api_gateway_rest_api.api_keys_api[0].id
  stage_name    = var.stage_name
}

# API Keys
resource "aws_api_gateway_api_key" "api_keys" {
  count = var.enable_api_keys ? length(var.api_keys) : 0

  name        = "${local.name}-${var.api_keys[count.index].name}"
  description = var.api_keys[count.index].description
  enabled     = var.api_keys[count.index].enabled
}

# Usage Plans
# resource "aws_api_gateway_usage_plan" "usage_plans" {
#   count = var.enable_api_keys ? length(var.usage_plans) : 0

#   name        = "${local.name}-${var.usage_plans[count.index].name}"
#   description = var.usage_plans[count.index].description

#   api_stages {
#     api_id = aws_api_gateway_rest_api.api_keys_api[0].id
#     stage  = aws_api_gateway_stage.api_keys_api[0].stage_name
#   }

#   quota_settings {
#     limit  = var.usage_plans[count.index].quota.limit
#     period = var.usage_plans[count.index].quota.period
#   }

#   throttle_settings {
#     burst_limit = var.usage_plans[count.index].throttle.burst_limit
#     rate_limit  = var.usage_plans[count.index].throttle.rate_limit
#   }
# }

# # Usage Plan Keys
# resource "aws_api_gateway_usage_plan_key" "usage_plan_keys" {
#   count = var.enable_api_keys ? length(local.usage_plan_keys) : 0

#   key_id        = local.usage_plan_keys[count.index].key_id
#   key_type      = "API_KEY"
#   usage_plan_id = local.usage_plan_keys[count.index].usage_plan_id
# }

# # Local value to create flattened list of usage plan keys
# locals {
#   usage_plan_keys = var.enable_api_keys ? flatten([
#     for plan_index, plan in var.usage_plans : [
#       for key_name in plan.api_key_names : {
#         usage_plan_id = aws_api_gateway_usage_plan.usage_plans[plan_index].id
#         key_id        = [for i, key in var.api_keys : aws_api_gateway_api_key.api_keys[i].id if key.name == key_name][0]
#       }
#     ]
#   ]) : []
# }

# CloudWatch Dashboard for API metrics
resource "aws_cloudwatch_dashboard" "api_dashboard" {
  for_each = var.enable_detailed_metrics ? { "main" = true } : {}

  dashboard_name = "${local.name}-api-dashboard"

  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/ApiGateway", "Count", "ApiId", aws_apigatewayv2_api.main.id, "Stage", aws_apigatewayv2_stage.main.name, { "stat" = "Sum" }],
            [".", "4XXError", ".", ".", ".", ".", { "stat" = "Sum" }],
            [".", "5XXError", ".", ".", ".", ".", { "stat" = "Sum" }]
          ]
          view    = "timeSeries"
          stacked = false
          region  = data.aws_region.current.name
          title   = "API Requests and Errors"
          period  = 300
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 0
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/ApiGateway", "Latency", "ApiId", aws_apigatewayv2_api.main.id, "Stage", aws_apigatewayv2_stage.main.name, { "stat" = "Average" }],
            [".", "IntegrationLatency", ".", ".", ".", ".", { "stat" = "Average" }]
          ]
          view    = "timeSeries"
          stacked = false
          region  = data.aws_region.current.name
          title   = "API Latency"
          period  = 300
        }
      }
    ]
  })
}

# CloudWatch Alarm for API errors
resource "aws_cloudwatch_metric_alarm" "api_error_rate" {
  count = var.enable_detailed_metrics ? 1 : 0

  alarm_name          = "${local.name}-api-error-rate"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "5XXError"
  namespace           = "AWS/ApiGateway"
  period              = 300
  statistic           = "Sum"
  threshold           = 10
  alarm_description   = "This alarm monitors the API Gateway 5XX error rate"

  dimensions = {
    ApiId = aws_apigatewayv2_api.main.id
    Stage = aws_apigatewayv2_stage.main.name
  }
}

# Message about API key usage with HTTP APIs
resource "null_resource" "api_key_usage_note" {
  count = var.enable_api_keys ? 1 : 0

  provisioner "local-exec" {
    command = "echo 'Note: To use the API with API keys, include the x-api-key header in your requests. You can verify key validity at ${aws_api_gateway_stage.api_keys_api[0].invoke_url}/validate'"
  }
}
