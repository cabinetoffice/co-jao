# Infrastructure as Code (IaC) Directory

This directory contains the Terraform configuration for deploying the API infrastructure to AWS.

## Directory Structure

```
iac/
├── modules/               # Terraform modules
│   ├── api_gateway/       # API Gateway configuration
│   ├── ecs/               # ECS cluster and service
│   └── vpc/               # VPC configuration
├── main.tf                # Main Terraform configuration
├── variables.tf           # Variable definitions
└── .terraform.lock.hcl    # Terraform dependency lock file
```

## Modules

### VPC Module

Sets up the Virtual Private Cloud with public and private subnets, NAT gateways, and routing tables.

### ECS Module

Configures the Elastic Container Service cluster, task definitions, services, and application load balancer.

### API Gateway Module

Sets up the API Gateway v2 (HTTP API) with routes, integrations, and VPC links to connect to the ECS service.

## Deployment

To deploy this infrastructure, use the wrapper script from the project root:

```bash
# Initialize Terraform
./tf.sh init

# Plan changes
./tf.sh plan

# Apply changes
./tf.sh apply

# Show outputs
./tf.sh output
```

Alternatively, you can run Terraform commands directly in this directory:

```bash
cd iac
terraform init
terraform apply
```

## Configuration

The infrastructure is configured via variables in `variables.tf`. Common parameters include:

- `app_name`: Name of the application
- `environment`: Deployment environment (dev, staging, prod)
- `aws_region`: AWS region for deployment
- `container_port`: Port exposed by the container
- `task_cpu` and `task_memory`: Resources allocated to the ECS task

## Outputs

After deployment, important information is available via Terraform outputs:

- `api_gateway_url`: URL of the deployed API
- `ecr_repository_url`: URL of the ECR repository for Docker images
- `ecs_cluster_name`: Name of the ECS cluster
- `load_balancer_dns`: DNS name of the Application Load Balancer

## Security and Best Practices

This configuration follows best practices:

- Resources are deployed in private subnets where possible
- Public exposure is limited to the API Gateway and Load Balancer
- Resource naming follows a consistent pattern based on app name and environment

## State Management

Terraform state is managed locally by default. For production use, consider using remote state with S3 and DynamoDB locking.