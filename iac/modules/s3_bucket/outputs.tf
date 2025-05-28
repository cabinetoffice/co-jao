# outputs.tf for S3 bucket module

output "bucket_id" {
  description = "The name of the bucket"
  value       = var.create_bucket ? aws_s3_bucket.this[0].id : var.bucket_name
}

output "bucket_arn" {
  description = "The ARN of the bucket"
  value       = var.create_bucket ? aws_s3_bucket.this[0].arn : "arn:aws:s3:::${var.bucket_name}"
}

output "bucket_domain_name" {
  description = "The bucket domain name"
  value       = var.create_bucket ? aws_s3_bucket.this[0].bucket_domain_name : "${var.bucket_name}.s3.amazonaws.com"
}

output "bucket_regional_domain_name" {
  description = "The regional domain name of the bucket"
  value       = var.create_bucket ? aws_s3_bucket.this[0].bucket_regional_domain_name : "${var.bucket_name}.s3.${data.aws_region.current.name}.amazonaws.com"
}

output "bucket_website_endpoint" {
  description = "The website endpoint, if the bucket is configured with a website"
  value       = var.create_bucket && var.website_configuration != null ? try(aws_s3_bucket_website_configuration.this[0].website_endpoint, null) : null
}

output "bucket_website_domain" {
  description = "The domain of the website endpoint, if the bucket is configured with a website"
  value       = var.create_bucket && var.website_configuration != null ? try(aws_s3_bucket_website_configuration.this[0].website_domain, null) : null
}

output "bucket_region" {
  description = "The AWS region the bucket resides in"
  value       = var.create_bucket ? aws_s3_bucket.this[0].region : data.aws_region.current.name
}