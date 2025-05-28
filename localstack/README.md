# LocalStack Development Environment

This directory contains the necessary configuration and scripts to run the API infrastructure locally using LocalStack, a cloud service emulator that runs in a Docker container.

## Overview

LocalStack allows you to develop and test your AWS cloud applications locally without incurring AWS costs or requiring internet connectivity to AWS services. This implementation supports both API Gateway v1 (REST API) and API Gateway v2 (HTTP API) depending on LocalStack capabilities.

## Prerequisites

- Docker and Docker Compose
- Terraform (v1.0+)
- AWS CLI
- Python 3 (for testing scripts)

## Directory Structure

- `docker-compose.yml` - Docker Compose configuration for LocalStack and app containers
- `localstack.tf` - Terraform provider configuration for LocalStack
- `localstack_main.tf` - Infrastructure as code specifically for LocalStack environment
- `run.sh` - Main script to start and configure the LocalStack environment
- `debug.sh` - Script to help debug issues with the LocalStack setup
- `fix-apigw.sh` - Script to fix API Gateway configuration issues

## Getting Started

1. Run the main script to set up the LocalStack environment:

   ```
   cd terraform-api-ecs/localstack
   chmod +x run.sh
   ./run.sh
   ```

2. This script will:
   - Start LocalStack in a Docker container
   - Create a LocalStack-specific Terraform configuration
   - Apply the Terraform configuration to LocalStack
   - Start the API container
   - Test the endpoints

## Script Options

The `run.sh` script supports several command line options:

- `--clean` - Force removal of all LocalStack containers and volumes for a fresh start
- `--skip-test` - Skip endpoint testing after deployment
- `--help` - Show help message

Example:
```
./run.sh --clean
```

## Troubleshooting

If you encounter issues with the LocalStack deployment:

1. Check LocalStack container logs:
   ```
   docker logs localstack
   ```

2. Run the debug script to get information about the API Gateway setup:
   ```
   ./debug.sh
   ```

3. If API Gateway endpoints are not working, try running the fix script:
   ```
   ./fix-apigw.sh
   ```

## Testing API Endpoints

You can test the API endpoints with curl:

### With API Gateway v2 (HTTP API)
```bash
# Get the API ID
API_ID=$(aws --endpoint-url=http://localhost:4566 apigatewayv2 get-apis --query "Items[0].ApiId" --output text)

# Test endpoints
curl http://localhost:4566/apis/$API_ID/health
curl http://localhost:4566/apis/$API_ID/api/hello
curl -X POST -H "Content-Type: application/json" -d '{"test":"data"}' http://localhost:4566/apis/$API_ID/api/data
```

### With API Gateway v1 (REST API)
```bash
# Get the API ID
API_ID=$(aws --endpoint-url=http://localhost:4566 apigateway get-rest-apis --query "items[0].id" --output text)

# Test endpoints
curl http://localhost:4566/restapis/$API_ID/local/_user_request_/health
curl http://localhost:4566/restapis/$API_ID/local/_user_request_/api/hello
curl -X POST -H "Content-Type: application/json" -d '{"test":"data"}' http://localhost:4566/restapis/$API_ID/local/_user_request_/api/data
```

### Direct Container Access
```bash
curl http://localhost:5000/health
curl http://localhost:5000/api/hello
curl -X POST -H "Content-Type: application/json" -d '{"test":"data"}' http://localhost:5000/api/data
```

## Cleaning Up

To stop and remove all LocalStack containers:

```bash
docker-compose -f docker-compose.yml down -v
```