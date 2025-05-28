# S3 Bucket Module

This module creates an AWS S3 bucket with configurable features like versioning, encryption, lifecycle rules, CORS, and more.

## Features

- Create S3 buckets with customizable settings
- Configure bucket permissions and access controls
- Enable/disable versioning
- Set up server-side encryption
- Configure lifecycle rules for object management
- Set up CORS rules for web applications
- Apply bucket policies
- Control bucket destruction behavior

## Usage

```hcl
module "app_initialization_bucket" {
  source = "./modules/s3_bucket"

  bucket_name       = "app-initialization-scripts"
  enable_versioning = true
  enable_encryption = true
  
  # Use force_destroy to control whether the bucket can be destroyed with contents
  force_destroy     = var.environment != "prod"
  
  # Example lifecycle rule to expire objects after 90 days
  lifecycle_rules = [
    {
      id     = "expire-old-files"
      status = "Enabled"
      expiration = {
        days = 90
      }
    }
  ]
  
  tags = {
    Environment = var.environment
    Project     = var.app_name
    ManagedBy   = "terraform"
  }
}
```

## Examples

### Basic bucket

```hcl
module "simple_bucket" {
  source      = "./modules/s3_bucket"
  bucket_name = "my-simple-bucket"
}
```

### Bucket with versioning and encryption

```hcl
module "versioned_bucket" {
  source           = "./modules/s3_bucket"
  bucket_name      = "my-versioned-bucket"
  enable_versioning = true
  enable_encryption = true
}
```

### Bucket with lifecycle rules

```hcl
module "data_lake_bucket" {
  source      = "./modules/s3_bucket"
  bucket_name = "my-data-lake"
  
  lifecycle_rules = [
    {
      id     = "archive-after-30-days"
      status = "Enabled"
      transitions = [
        {
          days          = 30
          storage_class = "STANDARD_IA"
        },
        {
          days          = 90
          storage_class = "GLACIER"
        }
      ]
    }
  ]
}
```

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| bucket_name | Name of the S3 bucket to create | `string` | n/a | yes |
| force_destroy | Boolean that indicates all objects should be deleted from the bucket when the bucket is destroyed | `bool` | `false` | no |
| tags | A map of tags to assign to the bucket | `map(string)` | `{}` | no |
| block_public_acls | Whether Amazon S3 should block public ACLs for this bucket | `bool` | `true` | no |
| block_public_policy | Whether Amazon S3 should block public bucket policies for this bucket | `bool` | `true` | no |
| ignore_public_acls | Whether Amazon S3 should ignore public ACLs for this bucket | `bool` | `true` | no |
| restrict_public_buckets | Whether Amazon S3 should restrict public bucket policies for this bucket | `bool` | `true` | no |
| enable_versioning | Enable versioning on the bucket | `bool` | `false` | no |
| enable_encryption | Enable server-side encryption for the bucket | `bool` | `true` | no |
| kms_key_id | ARN of the KMS key to use for encryption. If not specified, AES256 encryption will be used | `string` | `null` | no |
| lifecycle_rules | List of maps containing lifecycle rules configuration | `any` | `[]` | no |
| cors_rules | List of maps containing CORS rules configuration | `any` | `[]` | no |
| bucket_policy | A bucket policy as a JSON formatted string | `string` | `null` | no |

## Outputs

| Name | Description |
|------|-------------|
| bucket_id | The name of the bucket |
| bucket_arn | The ARN of the bucket |
| bucket_domain_name | The bucket domain name |
| bucket_regional_domain_name | The regional domain name of the bucket |
| bucket_region | The AWS region the bucket resides in |

## Best Practices

1. Always enable encryption for buckets that will store sensitive data
2. Use versioning for important data to protect against accidental deletion
3. Set appropriate lifecycle rules to manage storage costs
4. Configure strict access controls to prevent unauthorized access
5. In production environments, set `force_destroy = false` to avoid accidental deletion