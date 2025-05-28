# Deployment Guide for JAO Application

This guide explains how to deploy the JAO application, which consists of a frontend, backend API, and supporting AWS infrastructure.

## Prerequisites

- AWS CLI installed and configured with appropriate credentials
- Docker installed and running
- Terraform (version 1.0 or higher) installed
- Access to create resources in AWS (ECR, ECS, VPC, etc.)

## Deployment Options

The application can be deployed using the consolidated deployment script `deploy-terraform.sh`, which supports various deployment scenarios.

### Quick Start

For a standard deployment with default settings:

```bash
./deploy-terraform.sh
```

This will:
1. Build and push Docker images for frontend and backend
2. Deploy the infrastructure using Terraform
3. Update the ECS services to use the latest images

### Common Deployment Scenarios

#### 1. Deploying to a Specific Environment

```bash
./deploy-terraform.sh --env prod --region us-west-2
```

#### 2. Handling Existing Resources

When deploying to an environment with existing resources:

```bash
./deploy-terraform.sh --import-resources --skip-existing
```

This will import existing AWS resources into Terraform state and configure Terraform to skip creating resources that already exist.

#### 3. Using S3 Remote State

To use S3 for storing Terraform state (recommended for team environments):

```bash
./deploy-terraform.sh --state-bucket my-terraform-state
```

#### 4. Skipping Certain Steps

Skip building/pushing Docker images:

```bash
./deploy-terraform.sh --skip-backend --skip-frontend
```

Skip Terraform infrastructure changes:

```bash
./deploy-terraform.sh --skip-terraform
```

## Available Options

| Option | Description |
|--------|-------------|
| `--region REGION` | AWS region (default: eu-west-2) |
| `--app-name NAME` | Application name (default: python-api) |
| `--env ENV` | Environment (default: dev) |
| `--tag TAG` | Docker image tag (default: latest) |
| `--state-bucket BUCKET` | S3 bucket for Terraform state |
| `--skip-backend` | Skip building and pushing backend Docker image |
| `--skip-frontend` | Skip building and pushing frontend Docker image |
| `--skip-terraform` | Skip Terraform deployment |
| `--skip-service-update` | Skip ECS service update |
| `--force-push` | Force push to ECR even if image already exists |
| `--import-resources` | Import existing AWS resources into Terraform state |
| `--skip-existing` | Skip creating resources that already exist in AWS |
| `--clean-state` | Clean Terraform state before importing resources |
| `--help` | Display help message |

## Troubleshooting

### Resource Already Exists

If you encounter "resource already exists" errors:

```bash
./deploy-terraform.sh --import-resources --skip-existing
```

### Failed Build/Push

If Docker image build fails:
- Check that your Dockerfile is valid
- Ensure your application code can be built successfully locally

### Failed Infrastructure Deployment

If Terraform deployment fails:
- Check AWS credentials and permissions
- Look for specific error messages in the Terraform output
- Try running with `--import-resources` if resources already exist

## Working with Existing Resources

The deployment script includes built-in handling for existing resources through these mechanisms:

1. **Resource Import**: The `--import-resources` option attempts to import existing resources into Terraform state so they can be managed rather than recreated.

2. **Skip Creation**: The `--skip-existing` option sets Terraform variables to skip creating resources that might already exist.

3. **State Storage**: Using `--state-bucket` enables S3 state storage, which is useful when multiple team members are deploying the same infrastructure.

## Cleaning Up

To destroy all created resources:

```bash
cd iac
terraform destroy
```

**Warning**: This will permanently delete all resources managed by Terraform!