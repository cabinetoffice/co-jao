locals {
  name = "${var.name_prefix}-${var.environment}"

  common_tags = merge(
    var.tags,
    {
      Environment = var.environment
      ManagedBy   = "terraform"
      Name        = local.name
    }
  )

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
    },
    {
      route_key = "POST /lint"
      methods   = ["POST"]
      path      = "/lint"
    },
    {
      route_key = "POST /lint-stub"
      methods   = ["POST"]
      path      = "/lint-stub"
    }
  ]

  # Simplified route selection
  routes = coalesce(var.routes, local.default_routes)

  # Feature flags
  create_api_keys         = var.enable_api_keys
  create_detailed_metrics = var.enable_detailed_metrics

  # Count calculations for resources
  api_keys_count = local.create_api_keys ? length(var.api_keys) : 0
  routes_count   = length(local.routes) - 1 # Subtract proxy route
}

data "aws_region" "current" {}

resource "aws_api_gateway_rest_api" "main" {
  name        = "${local.name}-api"
  description = "REST API for ${local.name}"

  endpoint_configuration {
    types = ["REGIONAL"]
  }

  binary_media_types = [
    "multipart/form-data",
    "application/octet-stream",
    "image/*"
  ]

  tags = merge(
    local.common_tags,
    {
      Name = "${local.name}-api"
    }
  )
}

# VPC Link for connecting to NLB
resource "aws_api_gateway_vpc_link" "main" {
  name        = "${local.name}-vpc-link"
  target_arns = [var.load_balancer_arn]

  tags = merge(
    local.common_tags,
    {
      Name        = "${local.name}-vpc-link"
      Description = "VPC Link connecting API Gateway to NLB"
    }
  )
}

resource "aws_api_gateway_deployment" "main" {
  rest_api_id = aws_api_gateway_rest_api.main.id

  depends_on = [
    aws_api_gateway_integration.routes,
    aws_api_gateway_integration.proxy
  ]

  variables = {
    deployed_at = timestamp()
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_api_gateway_stage" "main" {
  deployment_id = aws_api_gateway_deployment.main.id
  rest_api_id   = aws_api_gateway_rest_api.main.id
  stage_name    = var.stage_name

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api_gateway.arn
    format = jsonencode({
      requestId               = "$context.requestId"
      ip                      = "$context.identity.sourceIp"
      requestTime             = "$context.requestTime"
      httpMethod              = "$context.httpMethod"
      resourcePath            = "$context.resourcePath"
      status                  = "$context.status"
      protocol                = "$context.protocol"
      responseLength          = "$context.responseLength"
      integrationErrorMessage = "$context.integrationErrorMessage"
    })
  }

  tags = merge(
    local.common_tags,
    {
      Name = "${local.name}-${var.stage_name}-stage"
    }
  )
}

resource "aws_api_gateway_method_settings" "main" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  stage_name  = aws_api_gateway_stage.main.stage_name
  method_path = "*/*"

  settings {
    metrics_enabled        = var.enable_detailed_metrics
    logging_level          = "INFO"
    throttling_burst_limit = var.api_throttling_burst_limit
    throttling_rate_limit  = var.api_throttling_rate_limit
    # Enable detailed logging for troubleshooting
    data_trace_enabled = true
  }
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

# API Resources and Methods
resource "aws_api_gateway_resource" "proxy" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_rest_api.main.root_resource_id
  path_part   = "{proxy+}"
}

resource "aws_api_gateway_resource" "routes" {
  count = local.routes_count

  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_rest_api.main.root_resource_id
  path_part   = element(split("/", replace(local.routes[count.index + 1].path, "/{proxy+}", "")), 1)
}

# Methods for proxy resource
resource "aws_api_gateway_method" "proxy" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.proxy.id
  http_method   = "ANY"
  authorization = "NONE"

  # Add request parameters to pass all headers, query strings, and path parameters to the integration
  request_parameters = {
    "method.request.path.proxy" = true
  }
}

# Methods for other resources
resource "aws_api_gateway_method" "routes" {
  count = local.routes_count

  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.routes[count.index].id
  http_method   = element(local.routes[count.index + 1].methods, 0) # Use first method from methods array
  authorization = "NONE"

  # Forward query parameters
  request_parameters = {
    "method.request.querystring.all" = true
  }
}

# Integration for proxy resource
resource "aws_api_gateway_integration" "proxy" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.proxy.id
  http_method             = aws_api_gateway_method.proxy.http_method
  integration_http_method = "ANY"
  type                    = "HTTP_PROXY"
  uri                     = "http://${var.load_balancer_dns_name}/{proxy}"
  connection_type         = "VPC_LINK"
  connection_id           = aws_api_gateway_vpc_link.main.id

  request_parameters = {
    "integration.request.path.proxy" = "method.request.path.proxy"
  }

  # Add timeout setting for longer operations
  timeout_milliseconds = 29000
}

# Integration for other resources
resource "aws_api_gateway_integration" "routes" {
  count = local.routes_count

  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.routes[count.index].id
  http_method             = aws_api_gateway_method.routes[count.index].http_method
  integration_http_method = aws_api_gateway_method.routes[count.index].http_method
  type                    = "HTTP_PROXY"
  uri                     = "http://${var.load_balancer_dns_name}${local.routes[count.index + 1].path}"
  connection_type         = "VPC_LINK"
  connection_id           = aws_api_gateway_vpc_link.main.id

  # Add timeout setting for longer operations
  timeout_milliseconds = 29000
}

# For API key functionality, we need to use REST API Gateway
# REST API Gateway (APIGatewayV1) for API key management
resource "aws_api_gateway_rest_api" "api_keys_api" {
  count = local.create_api_keys ? 1 : 0

  name        = "${local.name}-keys-api"
  description = "REST API for API key management"

  endpoint_configuration {
    types = ["REGIONAL"]
  }

  tags = local.common_tags
}

# API resource for validation
resource "aws_api_gateway_resource" "validate" {
  count = local.create_api_keys ? 1 : 0

  rest_api_id = aws_api_gateway_rest_api.api_keys_api[0].id
  parent_id   = aws_api_gateway_rest_api.api_keys_api[0].root_resource_id
  path_part   = "validate"
}

# Method for validation
resource "aws_api_gateway_method" "validate" {
  count = local.create_api_keys ? 1 : 0

  rest_api_id      = aws_api_gateway_rest_api.api_keys_api[0].id
  resource_id      = aws_api_gateway_resource.validate[0].id
  http_method      = "GET"
  authorization    = "NONE"
  api_key_required = true
}

# Integration for validation
resource "aws_api_gateway_integration" "validate" {
  count = local.create_api_keys ? 1 : 0

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
  count = local.create_api_keys ? 1 : 0

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
  count = local.create_api_keys ? 1 : 0

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
  count = local.create_api_keys ? 1 : 0

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
  count = local.create_api_keys ? 1 : 0

  deployment_id = aws_api_gateway_deployment.api_keys_api[0].id
  rest_api_id   = aws_api_gateway_rest_api.api_keys_api[0].id
  stage_name    = var.stage_name
}

# API Keys
resource "aws_api_gateway_api_key" "api_keys" {
  count = local.api_keys_count

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
  for_each = local.create_detailed_metrics ? { "main" = true } : {}

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
            ["AWS/ApiGateway", "Count", "ApiName", aws_api_gateway_rest_api.main.name, "Stage", aws_api_gateway_stage.main.stage_name, { "stat" = "Sum" }],
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
            ["AWS/ApiGateway", "Latency", "ApiName", aws_api_gateway_rest_api.main.name, "Stage", aws_api_gateway_stage.main.stage_name, { "stat" = "Average" }],
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
  count = local.create_detailed_metrics ? 1 : 0

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
    ApiName = aws_api_gateway_rest_api.main.name
    Stage   = aws_api_gateway_stage.main.stage_name
  }
}

# Message about API key usage with HTTP APIs
resource "null_resource" "api_key_usage_note" {
  count = local.create_api_keys ? 1 : 0

  provisioner "local-exec" {
    command = "echo 'Note: To use the API with API keys, include the x-api-key header in your requests. You can verify key validity at ${aws_api_gateway_stage.api_keys_api[0].invoke_url}/validate'"
  }
}
