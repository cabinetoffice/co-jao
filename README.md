# Terraform AWS API Gateway with Python ECS Backend

This project deploys a Python Flask API on AWS ECS with API Gateway integration using Terraform. It has been designed to be highly reusable across multiple projects and environments. It also supports deployment to LocalStack for local development and testing.

## Quick Start

To deploy this application to AWS:

1. Deploy everything with a single script:
   ```bash
   ./deploy-apigw-app.sh
   ```

   This script will:
   - Build and push the Docker image to ECR
   - Apply the Terraform configuration
   - Update the ECS service

2. Or step-by-step:

   a. Build and push the Docker image:
   ```bash
   ./deploy-apigw-app.sh --skip-terraform --skip-service-update
   ```

   b. Apply the Terraform configuration:
   ```bash
   ./tf.sh init
   ./tf.sh apply
   ```

   c. Update the ECS service:
   ```bash
   aws ecs update-service --force-new-deployment --service python-api-dev-service --cluster python-api-dev-cluster --region eu-west-2
   ```

## Architecture

```
   +----------------+    +----------------+    +-----------------+
   |                |    |                |    |                 |
   |  API Gateway   +--->+   VPC Link     +--->+   Application   |
   |                |    |                |    |  Load Balancer  |
   +----------------+    +----------------+    +-------+---------+
                                                       |
                                                       v
                                               +-------+---------+
                                               |                 |
                                               |  ECS Service    |
                                               |                 |
                                               +-------+---------+
                                                       |
                                                       v
                                               +-------+---------+
                                               |                 |
                                               |  ECR Container  |
                                               |                 |
                                               +-----------------+
```

## Prerequisites

- AWS CLI configured with appropriate credentials
- Terraform installed (v1.0+ recommended)
- Docker installed (for building and pushing container images)

## Project Structure

```
terraform-api-ecs/
│
├── app/                         # Python Flask application
│   ├── app.py                   # Main application file
│   ├── requirements.txt         # Python dependencies
│   └── Dockerfile               # Docker configuration
│
├── modules/                     # Terraform modules
│   ├── vpc/                     # VPC configuration
│   ├── ecs/                     # ECS cluster and service
│   └── api_gateway/             # API Gateway configuration
│
├── useful-scripts/              # Helper scripts for tasks like ECR management
│   ├── build-amd64-image.sh     # Build image for x86/amd64 architecture
│   ├── build-multiplatform-image.sh # Build for multiple architectures
│   ├── check-ecr-permissions.sh # Check AWS permissions for ECR
│   ├── fix-ecr-issues.sh        # Comprehensive script for fixing ECR issues
│   ├── recreate-ecr-repo.sh     # Recreate ECR repository with proper permissions
│   └── README.md                # Documentation for the scripts
│
├── build-python312-image.sh     # Main script to build Python 3.12 image for ECS
├── main.tf                      # Main Terraform configuration
├── variables.tf                 # Variable definitions
└── README.md                    # Project documentation
```

## Reusability Features

This project is designed to be highly reusable:

1. **Name Prefixing**: All resources use a consistent naming scheme based on `name_prefix` and `environment` variables.
2. **Environment-based Configuration**: Different configurations for dev, staging, and prod environments.
3. **Flexible Tagging**: Common tags are applied to all resources for better organization.
4. **Modular Design**: Each component (VPC, ECS, API Gateway) is a separate module that can be reused independently.

## How to Use for Multiple Projects

You can use this infrastructure for multiple projects by:

### Option 1: Using Workspace-based Approach

```bash
# Create workspaces for different projects
terraform workspace new project1
terraform workspace new project2

# Select the workspace
terraform workspace select project1

# Create a tfvars file for each project
# project1.tfvars
app_name = "project1"
environment = "dev"
...

# Apply with project-specific variables
terraform apply -var-file=project1.tfvars
```

### Option 2: Using Multiple Terraform Directories

```
infrastructure/
├── project1/
│   ├── main.tf          # References the shared modules
│   ├── variables.tf
│   └── terraform.tfvars # Project-specific values
│
├── project2/
│   ├── main.tf
│   ├── variables.tf
│   └── terraform.tfvars
│
└── modules/             # Shared modules
    ├── vpc/
    ├── ecs/
    └── api_gateway/
```

Example of a project-specific main.tf:

```hcl
module "api_infrastructure" {
  source = "../modules"

  app_name    = "customer-portal"
  environment = "prod"

  # Project-specific configuration
  container_port = 8080
  desired_count  = 3
  ...
}
```

## Module Configuration Options

### VPC Module

```hcl
module "vpc" {
  source = "./modules/vpc"

  name_prefix         = "myapp"
  environment         = "dev"
  vpc_cidr            = "10.0.0.0/16"
  azs                 = ["eu-west-2a", "eu-west-2b"]
  private_subnet_cidrs = ["10.0.1.0/24", "10.0.2.0/24"]
  public_subnet_cidrs  = ["10.0.101.0/24", "10.0.102.0/24"]

  # Cost-saving options for dev environments
  enable_nat_gateway  = true
  single_nat_gateway  = true  # Use false for production for higher availability

  tags = {
    Project = "MyProject"
    Owner   = "DevOps"
  }
}
```

### ECS Module

```hcl
module "ecs" {
  source = "./modules/ecs"

  name_prefix          = "myapp"
  environment          = "dev"
  ecr_repository_url   = "123456789012.dkr.ecr.eu-west-2.amazonaws.com/myapp"
  container_port       = 5000
  vpc_id               = module.vpc.vpc_id
  private_subnet_ids   = module.vpc.private_subnet_ids
  cpu                  = 256
  memory               = 512
  desired_count        = 2
  container_name       = "api"
  health_check_path    = "/health"
  internal_lb          = true  # Set to false for public-facing load balancers

  environment_variables = {
    LOG_LEVEL = "INFO"
    API_KEY   = "secure-key-reference"
  }

  tags = {
    Project = "MyProject"
    Owner   = "DevOps"
  }
}
```

### API Gateway Module

```hcl
module "api_gateway" {
  source = "./modules/api_gateway"

  name_prefix           = "myapp"
  environment           = "dev"
  vpc_id                = module.vpc.vpc_id
  vpc_link_subnets      = module.vpc.private_subnet_ids
  load_balancer_arn     = module.ecs.load_balancer_arn
  load_balancer_dns_name = module.ecs.load_balancer_dns_name
  stage_name            = "v1"

  # Define your API routes
  routes = [
    {
      route_key = "GET /users"
      methods   = ["GET"]
      path      = "/users"
    },
    {
      route_key = "POST /users"
      methods   = ["POST"]
      path      = "/users"
    }
  ]

  cors_allow_origins = ["https://example.com", "https://www.example.com"]

  tags = {
    Project = "MyProject"
    Owner   = "DevOps"
  }
}
```

## API Endpoints

The API includes the following endpoints:

- `GET /health` - Health check endpoint
- `GET /api/hello` - Returns a simple greeting message
- `GET /api/env` - Returns environment variables from the container
- `POST /api/data` - Accepts JSON data and returns a confirmation response

The application is built using Python 3.12 and Flask, with the latest compatible versions of dependencies.

### POST Endpoint Details

The `/api/data` endpoint accepts JSON data via POST requests. It will:

1. Validate that the request includes JSON data
2. Return the data as part of the response with a success message
3. Return a status code 201 (Created) on success, or 400 if no data was provided

## Deployment Steps

1. **Initialize Terraform**

   ```
   ./tf.sh init
   ```

   Or if using the IaC directory directly:

   ```
   cd iac
   terraform init
   ```

2. **Create a variable file for your project**

   Create an `iac/terraform.tfvars` file:

   ```
   app_name = "myapp"
   environment = "dev"
   aws_region = "eu-west-2"
   container_port = 5000
   ```

3. **Plan the deployment**

   ```
   ./tf.sh plan -var-file=terraform.tfvars
   ```

   Or if using the IaC directory directly:

   ```
   cd iac
   terraform plan -var-file=terraform.tfvars
   ```

4. **Apply the Terraform configuration**

   ```
   ./tf.sh apply -var-file=terraform.tfvars
   ```

   Or if using the IaC directory directly:

   ```
   cd iac
   terraform apply -var-file=terraform.tfvars
   ```

5. **Build and Push Docker Image**

   ```bash
   # Using the deployment script (recommended)
   ./deploy-apigw-app.sh --skip-terraform
   
   # Or manually:
   
   # Get ECR repo URL
   ECR_REPO=$(./tf.sh output -raw ecr_repository_url)

   # Build image for AMD64 platform (important for ECS compatibility)
   cd app
   docker build --platform=linux/amd64 -t ${ECR_REPO}:latest .

   # Login to ECR
   aws ecr get-login-password --region eu-west-2 | docker login --username AWS --password-stdin ${ECR_REPO}

   # Push image
   docker push ${ECR_REPO}:latest
   ```

6. **Test the API**

   ```
   # Test GET endpoint
   curl $(./tf.sh output -raw api_gateway_url)/api/hello

   # Test POST endpoint
   curl -X POST \
     -H "Content-Type: application/json" \
     -d '{"name": "Example", "message": "Hello API"}' \
     $(./tf.sh output -raw api_gateway_url)/api/data
   ```

## Testing POST Requests

This project includes example tools for testing the POST endpoint:

### Using HTML Test Page

1. Open `examples/post-request-test.html` in a web browser
2. Enter your API Gateway URL
3. Use either the JSON or Form Data tab to customize your request
4. Click "Send POST Request" to submit the data

### Using Python Script

```bash
# Install requirements
pip install requests

# Basic usage
python examples/post_request_test.py --url https://your-api-gateway-url.execute-api.region.amazonaws.com/dev/

# With custom data
python examples/post_request_test.py --url https://your-api-gateway-url.execute-api.region.amazonaws.com/dev/ \
  --data '{"name":"Test User","email":"test@example.com"}'

# With data from file
python examples/post_request_test.py --url https://your-api-gateway-url.execute-api.region.amazonaws.com/dev/ \
  --file examples/sample_data.json
```

## LocalStack Deployment

You can deploy this project to LocalStack for local development and testing without incurring AWS costs.

### Prerequisites

- Docker and Docker Compose
- LocalStack (via Docker)
- Terraform
- AWS CLI (optional, for testing)
- jq (optional, for formatting JSON output)

### Deployment Steps

1. **Run the LocalStack deployment script**

   ```bash
   chmod +x localstack-deploy.sh
   ./localstack-deploy.sh
   ```

   This script will:
   - Check for required dependencies
   - Start LocalStack in a Docker container
   - Create a LocalStack-specific tfvars file
   - Apply the Terraform configuration to LocalStack
   - Start the API container
   - Test all API endpoints automatically
   - Display helpful information and commands

2. **Script options**

   The script supports several command line options:

   ```bash
   # Skip testing endpoints after deployment
   ./localstack-deploy.sh --skip-test

   # Force a clean start, removing all existing LocalStack data
   ./localstack-deploy.sh --clean

   # If you encounter permission issues, try running with sudo
   sudo ./localstack-deploy.sh --clean

   # Show help message
   ./localstack-deploy.sh --help
   ```

3. **Manually test the API endpoints**

   ```bash
   # Test the GET endpoint
   curl http://localhost:4566/restapis/*/local/_user_request_/api/hello

   # Test the POST endpoint
   curl -X POST \
     -H "Content-Type: application/json" \
     -d '{"name":"Test"}' \
     http://localhost:4566/restapis/*/local/_user_request_/api/data

   # Test the health endpoint
   curl http://localhost:4566/restapis/*/local/_user_request_/health
   ```

   If you know the exact API ID, replace the `*` with your API ID for more reliable requests:

   ```bash
   # Get the API ID
   API_ID=$(aws --endpoint-url=http://localhost:4566 apigateway get-rest-apis --query "items[0].id" --output text)

   # Test with specific API ID
   curl http://localhost:4566/restapis/$API_ID/local/_user_request_/api/hello
   ```

4. **Stop LocalStack**

   ```bash
   docker-compose -f docker-compose.localstack.yml down
   ```

### LocalStack Limitations

- Some AWS services may have limited functionality in LocalStack
- The free version of LocalStack has limitations compared to the Pro version
- ECS in LocalStack has simplified functionality compared to real AWS
- The API Gateway URL format in LocalStack differs from real AWS

### Troubleshooting LocalStack

If you encounter the "Device or resource busy" error when running LocalStack, try these solutions:

1. Run the deployment script with the `--clean` flag:
   ```
   ./localstack-deploy.sh --clean
   ```

2. If that doesn't work, try running with sudo:
   ```
   sudo ./localstack-deploy.sh --clean
   ```

3. Manually clean up LocalStack resources:
   ```
   # Stop and remove all LocalStack containers
   docker ps -a | grep localstack | awk '{print $1}' | xargs -r docker rm -f

   # Remove LocalStack volumes
   docker volume ls | grep localstack | awk '{print $2}' | xargs -r docker volume rm

   # Remove temporary directories (may require sudo)
   sudo rm -rf /tmp/localstack*
   ```

4. Restart Docker if all else fails:
   ```
   # On Linux
   sudo systemctl restart docker

   # On macOS
   osascript -e 'quit app "Docker"' && open -a Docker
   ```

## Helper Scripts

The project includes several helper scripts to simplify common tasks:

### Main Scripts

- `deploy-apigw-app.sh` - Deploys the complete application (builds image, applies Terraform, updates ECS)
- `tf.sh` - Wrapper script for Terraform commands that automatically uses the iac directory
- `deploy.sh` - Original deployment script (for reference)

### Directory Structure

- `app/` - Contains the Flask application code, Dockerfile, and requirements
- `iac/` - Contains all Terraform configuration (modules, main.tf, variables.tf)
- `localstack/` - Configuration for local development using LocalStack
- `examples/` - Example code and client applications

## Common Issues and Solutions

### Platform Compatibility
If you encounter the error `image Manifest does not contain descriptor matching platform 'linux/amd64'`, it means you've built your Docker image on a different architecture (e.g., ARM64 on M1/M2 Macs) than what ECS expects (AMD64). Use the `build-python312-image.sh` script to ensure platform compatibility.

### ECR Permission Issues
If you see `403 Forbidden` errors when pushing to ECR, use the `check-ecr-permissions.sh` script to diagnose permission issues or `recreate-ecr-repo.sh` to set up a new repository with the correct permissions.

## Clean Up

To remove all resources created by this project:

```
./tf.sh destroy -var-file=terraform.tfvars
```

Or if using the IaC directory directly:

```
cd iac
terraform destroy -var-file=terraform.tfvars
```

## Best Practices for Multi-Environment Setups

1. **Environment-specific variables**: Create separate `.tfvars` files for each environment.
2. **State management**: Use Terraform remote state with state locking.
3. **CI/CD integration**: Set up pipelines to deploy to different environments.
4. **Secrets management**: Use AWS Secrets Manager or Parameter Store for sensitive values.
5. **Least privilege IAM**: Create specific IAM roles for each deployment environment.
6. **Local development**: Use LocalStack for local development and testing before deploying to AWS.

## Security Considerations

- For production, always enable HTTPS on API Gateway
- Consider adding authentication via Cognito or Lambda authorizers
- Implement WAF for additional security
- Use private subnets for ECS tasks
- Follow the principle of least privilege for IAM roles
- For POST endpoints, consider:
  - Input validation to prevent injection attacks
  - Rate limiting to prevent abuse
  - Request size limits to prevent denial of service
  - JSON schema validation for stronger type checking

## Development Workflow

Here's a recommended development workflow:

1. **Local Development**: Deploy to LocalStack for rapid development and testing
2. **Dev Environment**: Deploy to a dev AWS environment for integration testing
3. **Staging Environment**: Deploy to a staging environment that mimics production
4. **Production Environment**: Deploy to production after thorough testing

This workflow allows you to catch issues early in the development process and ensures smoother deployments to production.
