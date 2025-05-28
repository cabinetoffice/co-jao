# S3 bucket module - main.tf
# Get current AWS region
data "aws_region" "current" {}

resource "aws_s3_bucket" "this" {
  count         = var.create_bucket ? 1 : 0
  bucket        = var.bucket_name
  force_destroy = var.force_destroy

  tags = merge(
    var.tags,
    {
      Name = var.bucket_name
    }
  )

  # Set lifecycle configuration
  lifecycle {
    # Note: prevent_destroy cannot use variables, must be hardcoded
    prevent_destroy = false
  }
}

# Bucket Public Access Block
resource "aws_s3_bucket_public_access_block" "this" {
  count  = var.create_bucket ? 1 : 0
  bucket = aws_s3_bucket.this[0].id

  block_public_acls       = var.block_public_acls
  block_public_policy     = var.block_public_policy
  ignore_public_acls      = var.ignore_public_acls
  restrict_public_buckets = var.restrict_public_buckets
}

# Bucket Versioning
resource "aws_s3_bucket_versioning" "this" {
  count  = var.create_bucket ? 1 : 0
  bucket = aws_s3_bucket.this[0].id

  versioning_configuration {
    status = var.enable_versioning ? "Enabled" : "Suspended"
  }
}

# Server-side encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "this" {
  count = var.create_bucket && var.enable_encryption ? 1 : 0

  bucket = aws_s3_bucket.this[0].id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = var.kms_key_id != null ? "aws:kms" : "AES256"
      kms_master_key_id = var.kms_key_id
    }
  }
}

# Lifecycle configuration
resource "aws_s3_bucket_lifecycle_configuration" "this" {
  count = var.create_bucket && length(var.lifecycle_rules) > 0 ? 1 : 0

  bucket = aws_s3_bucket.this[0].id

  dynamic "rule" {
    for_each = var.lifecycle_rules

    content {
      id     = rule.value.id
      status = rule.value.status

      dynamic "expiration" {
        for_each = lookup(rule.value, "expiration", null) != null ? [rule.value.expiration] : []

        content {
          days = lookup(expiration.value, "days", null)
        }
      }

      dynamic "transition" {
        for_each = lookup(rule.value, "transitions", [])

        content {
          days          = lookup(transition.value, "days", null)
          storage_class = transition.value.storage_class
        }
      }
    }
  }
}

# CORS configuration
resource "aws_s3_bucket_cors_configuration" "this" {
  count = var.create_bucket && length(var.cors_rules) > 0 ? 1 : 0

  bucket = aws_s3_bucket.this[0].id

  dynamic "cors_rule" {
    for_each = var.cors_rules

    content {
      allowed_headers = lookup(cors_rule.value, "allowed_headers", null)
      allowed_methods = cors_rule.value.allowed_methods
      allowed_origins = cors_rule.value.allowed_origins
      expose_headers  = lookup(cors_rule.value, "expose_headers", null)
      max_age_seconds = lookup(cors_rule.value, "max_age_seconds", null)
    }
  }
}

# Website configuration
resource "aws_s3_bucket_website_configuration" "this" {
  count = var.create_bucket && var.website_configuration != null ? 1 : 0

  bucket = aws_s3_bucket.this[0].id

  dynamic "index_document" {
    for_each = var.website_configuration != null && lookup(var.website_configuration, "index_document", null) != null ? [var.website_configuration.index_document] : []
    content {
      suffix = index_document.value
    }
  }

  dynamic "error_document" {
    for_each = var.website_configuration != null && lookup(var.website_configuration, "error_document", null) != null ? [var.website_configuration.error_document] : []
    content {
      key = error_document.value
    }
  }

  dynamic "redirect_all_requests_to" {
    for_each = var.website_configuration != null && lookup(var.website_configuration, "redirect_all_requests_to", null) != null ? [var.website_configuration.redirect_all_requests_to] : []
    content {
      host_name = redirect_all_requests_to.value.host_name
      protocol  = lookup(redirect_all_requests_to.value, "protocol", null)
    }
  }

  dynamic "routing_rule" {
    for_each = var.website_configuration != null ? lookup(var.website_configuration, "routing_rules", []) : []
    content {
      condition {
        key_prefix_equals               = lookup(routing_rule.value.condition, "key_prefix_equals", null)
        http_error_code_returned_equals = lookup(routing_rule.value.condition, "http_error_code_returned_equals", null)
      }
      redirect {
        host_name               = lookup(routing_rule.value.redirect, "host_name", null)
        protocol                = lookup(routing_rule.value.redirect, "protocol", null)
        replace_key_prefix_with = lookup(routing_rule.value.redirect, "replace_key_prefix_with", null)
        replace_key_with        = lookup(routing_rule.value.redirect, "replace_key_with", null)
        http_redirect_code      = lookup(routing_rule.value.redirect, "http_redirect_code", null)
      }
    }
  }
}

# Bucket policy
resource "aws_s3_bucket_policy" "this" {
  count = var.create_bucket && var.bucket_policy != null ? 1 : 0

  bucket = aws_s3_bucket.this[0].id
  policy = var.bucket_policy
}
