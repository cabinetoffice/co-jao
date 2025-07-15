#!/bin/bash
set -e  # Exit on error

# Colors for terminal output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Enhanced AWS Terraform API Gateway + ECS Deployment Script${NC}"
echo -e "====================================================================="

# Default values
AWS_REGION="eu-west-2"
APP_NAME="jao"
ENV="dev"
IMAGE_TAG="latest"
SKIP_BACKEND=false
SKIP_FRONTEND=false
SKIP_TERRAFORM=false
SKIP_SERVICE_UPDATE=false
FORCE_IMPORT=false
SKIP_VPC=false
SKIP_CLOUDWATCH=true
SKIP_IAM_ROLES=false
EXISTING_VPC_ID=""
EXISTING_BACKEND_LOG_GROUP=""
EXISTING_FRONTEND_LOG_GROUP=""
SKIP_EXISTING=false
VPC_ID_VALIDATED=false

# Function to validate VPC ID
validate_vpc_id() {
    local vpc_id="$1"

    if [ -z "$vpc_id" ]; then
        echo -e "${YELLOW}No VPC ID provided for validation.${NC}"
        return 1
    fi

    echo -e "${YELLOW}Validating VPC ID: ${vpc_id}...${NC}"
    if aws ec2 describe-vpcs --vpc-ids "${vpc_id}" --region "${AWS_REGION}" &>/dev/null; then
        echo -e "${GREEN}VPC ID ${vpc_id} is valid.${NC}"
        VPC_ID_VALIDATED=true
        return 0
    else
        echo -e "${RED}Error: VPC ID ${vpc_id} is invalid or not accessible.${NC}"
        echo -e "${YELLOW}You must provide a valid VPC ID when using --skip-vpc${NC}"
        return 1
    fi
}

# Function to list available VPCs
list_available_vpcs() {
    echo -e "${YELLOW}Available VPCs in ${AWS_REGION}:${NC}"
    aws ec2 describe-vpcs --region ${AWS_REGION} --query 'Vpcs[*].[VpcId,Tags[?Key==`Name`].Value | [0],CidrBlock,IsDefault]' --output table || {
        echo -e "${RED}Failed to list VPCs. Check your AWS credentials.${NC}"
    }
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --region)
      AWS_REGION="$2"
      shift 2
      ;;
    --app-name)
      APP_NAME="$2"
      shift 2
      ;;
    --env)
      ENV="$2"
      shift 2
      ;;
    --tag)
      IMAGE_TAG="$2"
      shift 2
      ;;
    --skip-backend)
      SKIP_BACKEND=true
      shift
      ;;
    --skip-frontend)
      SKIP_FRONTEND=true
      shift
      ;;
    --skip-terraform)
      SKIP_TERRAFORM=true
      shift
      ;;
    --skip-service-update)
      SKIP_SERVICE_UPDATE=true
      shift
      ;;
    --force-import)
      FORCE_IMPORT=true
      shift
      ;;
    --skip-vpc)
      SKIP_VPC=true
      echo -e "${RED}WARNING: --skip-vpc MUST be used with --existing-vpc-id vpc-xxxxxxxx${NC}"
      echo -e "${RED}Deployment will FAIL without a valid VPC ID when skipping VPC creation${NC}"
      list_available_vpcs
      shift
      ;;
    --skip-cloudwatch)
      SKIP_CLOUDWATCH=true
      echo -e "${YELLOW}Note: When using --skip-cloudwatch, you can specify existing log groups with:${NC}"
      echo -e "${BLUE}    --backend-log-group NAME --frontend-log-group NAME${NC}"
      shift
      ;;
    --backend-log-group)
      EXISTING_BACKEND_LOG_GROUP="$2"
      shift 2
      ;;
    --frontend-log-group)
      EXISTING_FRONTEND_LOG_GROUP="$2"
      shift 2
      ;;
    --skip-iam-roles)
      SKIP_IAM_ROLES=true
      shift
      ;;
    --existing-vpc-id)
      EXISTING_VPC_ID="$2"
      if [ -z "$EXISTING_VPC_ID" ]; then
        echo -e "${RED}Error: Missing VPC ID for --existing-vpc-id option.${NC}"
        exit 1
      fi
      shift 2
      ;;
    --skip-existing)
      SKIP_EXISTING=true
      SKIP_VPC=true
      SKIP_CLOUDWATCH=true
      SKIP_IAM_ROLES=true
      shift
      ;;
    --help)
      echo -e "${BLUE}Usage:${NC} $0 [OPTIONS]"
      echo -e "${BLUE}Options:${NC}"
      echo "  --region REGION            AWS region (default: eu-west-2)"
      echo "  --app-name NAME            Application name (default: jao)"
      echo "  --env ENV                  Environment (default: dev)"
      echo "  --tag TAG                  Docker image tag (default: latest)"
      echo "  --skip-backend             Skip building and pushing backend Docker image"
      echo "  --skip-frontend            Skip building and pushing frontend Docker image"
      echo "  --skip-terraform           Skip Terraform deployment"
      echo "  --skip-service-update      Skip ECS service update"
      echo "  --force-import             Force import of existing ECR repositories"
      echo "  --skip-vpc                 Skip VPC creation (use with --existing-vpc-id)"
      echo "  --skip-cloudwatch          Skip CloudWatch log groups creation"
      echo "  --backend-log-group NAME   Specify existing backend CloudWatch log group name"
      echo "  --frontend-log-group NAME  Specify existing frontend CloudWatch log group name"
      echo "  --skip-iam-roles           Skip IAM roles creation"
      echo "  --existing-vpc-id ID       VPC ID to use if skipping VPC creation"
      echo "  --skip-existing            Skip creating resources that already exist"
      echo "  --help                     Display this help message"
      exit 0
      ;;
    *)
      echo -e "${RED}Unknown argument: $1${NC}"
      echo -e "Run '$0 --help' for usage."
      exit 1
      ;;
  esac
done

# Check required tools
echo -e "\n${GREEN}Checking required tools...${NC}"
command -v aws >/dev/null 2>&1 || { echo -e "${RED}Error: AWS CLI is required but not installed.${NC}"; exit 1; }
command -v docker >/dev/null 2>&1 || { echo -e "${RED}Error: Docker is required but not installed.${NC}"; exit 1; }
if ! $SKIP_TERRAFORM; then
    command -v terraform >/dev/null 2>&1 || { echo -e "${RED}Error: Terraform is required but not installed.${NC}"; exit 1; }
fi

# Get current directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
BACKEND_DIR="${SCRIPT_DIR}/jao-backend"
FRONTEND_DIR="${SCRIPT_DIR}/jao-web"
SCHEMAS_DIR="${SCRIPT_DIR}/jao-backend-schemas"
IAC_DIR="${SCRIPT_DIR}/iac"

# Get AWS account ID
echo -e "\n${GREEN}Getting AWS account ID...${NC}"
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query 'Account' --output text)
if [ -z "$AWS_ACCOUNT_ID" ]; then
    echo -e "${RED}Error: Could not get AWS account ID. Make sure you're logged in.${NC}"
    exit 1
fi

# Log in to ECR
echo -e "\n${GREEN}Logging in to ECR...${NC}"
aws ecr get-login-password --region "${AWS_REGION}" | docker login --username AWS --password-stdin "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

# Backend deployment
if [ "$SKIP_BACKEND" = false ]; then
    echo -e "\n${GREEN}Deploying backend application...${NC}"

    # Set backend ECR repository name and URI
    BACKEND_REPO_NAME="${APP_NAME}-${ENV}"
    BACKEND_ECR_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${BACKEND_REPO_NAME}"

    # Check if repository exists
    echo -e "${YELLOW}Checking if backend ECR repository exists...${NC}"
    if ! aws ecr describe-repositories --repository-names "${BACKEND_REPO_NAME}" --region "${AWS_REGION}" &>/dev/null; then
        echo -e "${YELLOW}Repository ${BACKEND_REPO_NAME} does not exist. Creating...${NC}"
        aws ecr create-repository --repository-name "${BACKEND_REPO_NAME}" --region "${AWS_REGION}"
    else
        echo -e "${GREEN}Repository ${BACKEND_REPO_NAME} already exists. Using existing repository.${NC}"
    fi

    # Build and push backend Docker image
    echo -e "${GREEN}Building backend Docker image...${NC}"
    # Build from the project root with the specific Dockerfile
    cd "${SCRIPT_DIR}"
    echo -e "${BLUE}Using build context: ${SCRIPT_DIR}${NC}"
    echo -e "${BLUE}Using Dockerfile: ${BACKEND_DIR}/Dockerfile${NC}"

    # Run build with more verbose output and specific build args
    if ! docker build \
        --build-arg POETRY_VERSION=1.8.3 \
        --build-arg ENV=dev \
        --progress=plain \
        --platform=linux/amd64 \
        -t "${BACKEND_REPO_NAME}:${IMAGE_TAG}" \
        -f "${BACKEND_DIR}/Dockerfile" .; then
        echo -e "${RED}Error: Backend Docker build failed.${NC}"
        echo -e "${YELLOW}Tip: The error might be related to pip install or poetry. Check that your Python version is compatible with the dependencies.${NC}"
        echo -e "${YELLOW}Additional troubleshooting:${NC}"
        echo -e "1. Check if jao-backend-schemas can be built independently"
        echo -e "2. Verify that Python 3.12 is compatible with all dependencies"
        echo -e "3. Check for network issues that might prevent package downloads"
        echo -e "4. Try running 'docker system prune' to clean up Docker cache"
        echo -e "5. Inspect the error messages carefully for specific package issues"

        # Ask if user wants to continue despite the error
        read -p "Continue with deployment despite backend build failure? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo -e "${RED}Deployment aborted.${NC}"
            exit 1
        else
            echo -e "${YELLOW}Continuing with deployment without backend updates.${NC}"
            SKIP_BACKEND=true
        fi
    fi

    echo -e "${GREEN}Tagging backend Docker image...${NC}"
    docker tag "${BACKEND_REPO_NAME}:${IMAGE_TAG}" "${BACKEND_ECR_URI}:${IMAGE_TAG}"

    echo -e "${GREEN}Pushing backend Docker image to ECR...${NC}"
    docker push "${BACKEND_ECR_URI}:${IMAGE_TAG}"

    echo -e "${BLUE}Successfully pushed backend image: ${BACKEND_ECR_URI}:${IMAGE_TAG}${NC}"
fi

# Frontend deployment
if [ "$SKIP_FRONTEND" = false ]; then
    echo -e "\n${GREEN}Deploying frontend application...${NC}"

    # Set frontend ECR repository name and URI
    FRONTEND_REPO_NAME="${APP_NAME}-frontend-${ENV}"
    FRONTEND_ECR_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${FRONTEND_REPO_NAME}"

    # Check if repository exists
    echo -e "${YELLOW}Checking if frontend ECR repository exists...${NC}"
    if ! aws ecr describe-repositories --repository-names "${FRONTEND_REPO_NAME}" --region "${AWS_REGION}" &>/dev/null; then
        echo -e "${YELLOW}Repository ${FRONTEND_REPO_NAME} does not exist. Creating...${NC}"
        aws ecr create-repository --repository-name "${FRONTEND_REPO_NAME}" --region "${AWS_REGION}"
    else
        echo -e "${GREEN}Repository ${FRONTEND_REPO_NAME} already exists. Using existing repository.${NC}"
    fi

    # Build and push frontend Docker image
    echo -e "${GREEN}Building frontend Docker image...${NC}"
    # Build from the project root with the specific Dockerfile
    cd "${SCRIPT_DIR}"
    echo -e "${BLUE}Using build context: ${SCRIPT_DIR}${NC}"
    echo -e "${BLUE}Using Dockerfile: ${FRONTEND_DIR}/Dockerfile${NC}"

    # Run build with more verbose output and build args
    if ! docker build \
        --build-arg POETRY_VERSION=1.8.3 \
        --build-arg ENV=dev \
        --progress=plain \
        --platform=linux/amd64 \
        -t "${FRONTEND_REPO_NAME}:${IMAGE_TAG}" \
        -f "${FRONTEND_DIR}/Dockerfile" .; then
        echo -e "${RED}Error: Frontend Docker build failed.${NC}"
        echo -e "${YELLOW}Tip: The error might be related to npm install or build process. Check your package.json and Dockerfile.${NC}"
        echo -e "${YELLOW}Additional troubleshooting:${NC}"
        echo -e "1. Check if node_modules can be installed manually"
        echo -e "2. Verify that your frontend build process works locally"
        echo -e "3. Check for network issues that might prevent package downloads"
        echo -e "4. Run 'npm cache clean --force' if npm dependencies are failing"
        echo -e "5. Try with a specific Node.js version if compatibility issues occur"

        # Ask if user wants to continue despite the error
        read -p "Continue with deployment despite frontend build failure? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo -e "${RED}Deployment aborted.${NC}"
            exit 1
        else
            echo -e "${YELLOW}Continuing with deployment without frontend updates.${NC}"
            SKIP_FRONTEND=true
        fi
    fi

    echo -e "${GREEN}Tagging frontend Docker image...${NC}"
    docker tag "${FRONTEND_REPO_NAME}:${IMAGE_TAG}" "${FRONTEND_ECR_URI}:${IMAGE_TAG}"

    echo -e "${GREEN}Pushing frontend Docker image to ECR...${NC}"
    docker push "${FRONTEND_ECR_URI}:${IMAGE_TAG}"

    echo -e "${BLUE}Successfully pushed frontend image: ${FRONTEND_ECR_URI}:${IMAGE_TAG}${NC}"
fi

# Run Terraform if not skipped
if [ "$SKIP_TERRAFORM" = false ]; then
    echo -e "\n${GREEN}Running Terraform...${NC}"
    cd "${IAC_DIR}"

    # Initialize Terraform with local state
    echo -e "${BLUE}Initializing Terraform with local state...${NC}"
    if ! terraform init -reconfigure; then
        echo -e "${RED}Failed to initialize Terraform!${NC}"
        echo -e "${YELLOW}Check your AWS credentials and configuration.${NC}"
        exit 1
    fi

    echo -e "${YELLOW}Planning Terraform changes...${NC}"

    # Get AWS account ID for ECR repository URLs
    AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query 'Account' --output text)

    # Check if repositories already exist and set variables accordingly
    SKIP_ECR_CREATION=false
    if aws ecr describe-repositories --repository-names "${BACKEND_REPO_NAME}" --region "${AWS_REGION}" &>/dev/null &&
       aws ecr describe-repositories --repository-names "${FRONTEND_REPO_NAME}" --region "${AWS_REGION}" &>/dev/null; then
        echo -e "${GREEN}Both ECR repositories already exist. Setting skip_ecr_creation=true...${NC}"
        SKIP_ECR_CREATION=true
    fi

    # Create temporary plan variables file
    cat > terraform.tfvars.json <<EOF
{
  "skip_ecr_creation": ${SKIP_ECR_CREATION},
  "aws_account_id": "${AWS_ACCOUNT_ID}",
  "image_tag": "${IMAGE_TAG}",
  "skip_vpc_creation": ${SKIP_VPC},
  "skip_vpc_validation": true,
  "skip_cloudwatch_creation": ${SKIP_CLOUDWATCH},
  "skip_iam_role_creation": ${SKIP_IAM_ROLES},
  "skip_s3_bucket_creation": ${SKIP_EXISTING}
EOF

    # Add log group names if provided
    if [ -n "${EXISTING_BACKEND_LOG_GROUP}" ]; then
      echo ',
  "existing_backend_log_group": "'"${EXISTING_BACKEND_LOG_GROUP}"'"' >> terraform.tfvars.json
    fi

    if [ -n "${EXISTING_FRONTEND_LOG_GROUP}" ]; then
      echo ',
  "existing_frontend_log_group": "'"${EXISTING_FRONTEND_LOG_GROUP}"'"' >> terraform.tfvars.json
    fi

    # Close the JSON object
    echo "
}" >> terraform.tfvars.json

    # Check VPC settings
    if [ "${SKIP_VPC}" = true ]; then
      if [ -n "${EXISTING_VPC_ID}" ]; then
        # Validate the VPC ID
        if ! validate_vpc_id "${EXISTING_VPC_ID}"; then
          echo -e "${RED}Error: Invalid VPC ID specified. Please provide a valid VPC ID.${NC}"
          list_available_vpcs

          echo -e "${RED}CRITICAL: Using --skip-vpc without a valid VPC ID will fail.${NC}"
          read -p "Disable VPC skipping and create a new VPC instead? (recommended) (y/n) " -n 1 -r
          echo
          if [[ $REPLY =~ ^[Yy]$ ]]; then
            echo -e "${GREEN}Smart choice! Creating a new VPC instead.${NC}"
            SKIP_VPC=false
          else
            echo -e "${RED}WARNING: Continuing with an invalid VPC ID. Deployment will likely fail.${NC}"
            echo -e "${YELLOW}To fix this error when it occurs, run this script with:${NC}"
            echo -e "${BLUE}    $0 --skip-vpc --existing-vpc-id YOUR_VALID_VPC_ID${NC}"
          fi
        else
          # Remove the closing brace
          sed -i '' -e '$ s/}$/,/' terraform.tfvars.json
          # Add VPC ID and closing brace
          echo "  \"existing_vpc_id\": \"${EXISTING_VPC_ID}\"" >> terraform.tfvars.json
          echo "}" >> terraform.tfvars.json
          echo -e "${GREEN}Using existing VPC: ${EXISTING_VPC_ID}${NC}"
        fi
      else
        echo -e "${RED}ERROR: --skip-vpc was specified without a VPC ID.${NC}"
        echo -e "${RED}This configuration will fail. VPC skipping requires a valid VPC ID.${NC}"
        list_available_vpcs

        echo -e "${YELLOW}Choose an option:${NC}"
        echo -e "1) Disable VPC skipping (create a new VPC) - recommended"
        echo -e "2) Choose a VPC ID from the list above"
        echo -e "3) Continue anyway (will likely fail)"
        read -p "Enter choice (1-3): " vpc_choice

        case $vpc_choice in
          1)
            echo -e "${GREEN}Smart choice! Creating a new VPC instead.${NC}"
            SKIP_VPC=false
            ;;
          2)
            read -p "Enter VPC ID from the list above: " chosen_vpc_id
            if validate_vpc_id "${chosen_vpc_id}"; then
              EXISTING_VPC_ID="${chosen_vpc_id}"
              # Remove the closing brace
              sed -i '' -e '$ s/}$/,/' terraform.tfvars.json
              # Add VPC ID and closing brace
              echo "  \"existing_vpc_id\": \"${EXISTING_VPC_ID}\"" >> terraform.tfvars.json
              echo "}" >> terraform.tfvars.json
              echo -e "${GREEN}Using existing VPC: ${EXISTING_VPC_ID}${NC}"
            else
              echo -e "${RED}Invalid VPC ID. Creating a new VPC instead.${NC}"
              SKIP_VPC=false
            fi
            ;;
          *)
            echo -e "${RED}WARNING: Continuing without a VPC ID. Deployment will likely fail.${NC}"
            echo -e "${YELLOW}To fix this error when it occurs, run this script with:${NC}"
            echo -e "${BLUE}    $0 --skip-vpc --existing-vpc-id YOUR_VALID_VPC_ID${NC}"
            ;;
        esac
      fi
    fi

    terraform plan -var-file=terraform.tfvars -out=tfplan

    echo -e "${YELLOW}Applying Terraform changes...${NC}"
    if ! terraform apply tfplan; then
        echo -e "${RED}Terraform apply failed!${NC}"
        echo -e "${YELLOW}If you're seeing 'resource already exists' errors, try running this script with:${NC}"
        echo -e "${BLUE}    $0 --skip-existing --skip-cloudwatch --skip-iam-roles${NC}"

        echo -e "${YELLOW}If you're seeing CloudWatch log group errors:${NC}"
        echo -e "${BLUE}    $0 --skip-cloudwatch${NC}"
        echo -e "${YELLOW}Or specify existing log groups:${NC}"
        echo -e "${BLUE}    $0 --skip-cloudwatch --backend-log-group /ecs/jao-dev --frontend-log-group /ecs/jao-frontend-dev${NC}"

        echo -e "${RED}IMPORTANT: If you're seeing VPC errors:${NC}"
        echo -e "${YELLOW}1. First list your VPCs:${NC}"
        echo -e "${BLUE}    aws ec2 describe-vpcs --region ${AWS_REGION} --query 'Vpcs[*].[VpcId,Tags[?Key==\`Name\`].Value | [0],CidrBlock,IsDefault]' --output table${NC}"
        echo -e "${YELLOW}2. Then use a valid VPC ID:${NC}"
        echo -e "${BLUE}    $0 --skip-vpc --existing-vpc-id vpc-xxxxxxxx${NC}"
        echo -e "${RED}WARNING: NEVER use --skip-vpc without --existing-vpc-id${NC}"
        echo -e "${YELLOW}See co/jao-work/co-jao/RESOURCE_ERRORS.md for more details.${NC}"

        # Ask if user wants to continue despite the error
        read -p "Continue with deployment despite Terraform errors? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo -e "${RED}Deployment aborted.${NC}"
            exit 1
        else
            echo -e "${YELLOW}Continuing despite Terraform errors.${NC}"
        fi
    fi

    # Clean up temporary variables file
    rm -f terraform.tfvars.json

    cd "${SCRIPT_DIR}"
fi

# Update ECS services if not skipped
if [ "$SKIP_SERVICE_UPDATE" = false ]; then
    echo -e "\n${GREEN}Updating ECS services...${NC}"
# Update ECS services with new images
echo -e "\n${GREEN}Updating ECS services with new Docker images...${NC}"

# Extract service and cluster names from Terraform output
BACKEND_SERVICE_NAME="${APP_NAME}-${ENV}-api-service"
BACKEND_CLUSTER_NAME="${APP_NAME}-${ENV}-cluster"
BACKEND_SERVICE_WORKER_NAME="${APP_NAME}-${ENV}-worker-service"
BACKEND_SERVICE_BEAT_NAME="${APP_NAME}-${ENV}-beat-service"
FRONTEND_SERVICE_NAME="${APP_NAME}-frontend-${ENV}-service"
FRONTEND_CLUSTER_NAME="${APP_NAME}-frontend-${ENV}-cluster"

# Function to check if ECS service exists and is in ACTIVE state
check_service_status() {
    local service_name="$1"
    local cluster_name="$2"
    local max_attempts=30
    local attempt=1

    echo -e "${YELLOW}Checking if service ${service_name} exists and is ACTIVE...${NC}"

    # First check if service exists
    local service_exists=$(aws ecs describe-services --services "${service_name}" --cluster "${cluster_name}" --region "${AWS_REGION}" --query 'length(services)' --output text 2>/dev/null || echo "0")

    if [ "$service_exists" = "0" ]; then
        echo -e "${RED}Service ${service_name} does not exist - needs to be created by Terraform${NC}"
        return 2  # Special return code for missing service
    fi

    while [ $attempt -le $max_attempts ]; do
        local status=$(aws ecs describe-services --services "${service_name}" --cluster "${cluster_name}" --region "${AWS_REGION}" --query 'services[0].status' --output text 2>/dev/null || echo "NOT_FOUND")

        if [ "$status" = "ACTIVE" ]; then
            echo -e "${GREEN}Service ${service_name} is ACTIVE${NC}"
            return 0
        elif [ "$status" = "NOT_FOUND" ]; then
            echo -e "${YELLOW}Service ${service_name} not found${NC}"
            return 1
        else
            echo -e "${YELLOW}Service ${service_name} status: ${status} (attempt ${attempt}/${max_attempts})${NC}"
            sleep 10
            attempt=$((attempt + 1))
        fi
    done

    echo -e "${RED}Service ${service_name} did not become ACTIVE after ${max_attempts} attempts${NC}"
    return 1
}

# Function to update ECS service with retry logic
update_ecs_service() {
    local service_name="$1"
    local cluster_name="$2"
    local service_type="$3"
    local max_retries=3
    local retry=1

    echo -e "${BLUE}Updating ${service_type} ECS service: ${service_name} in cluster: ${cluster_name}${NC}"

    # Check if service exists and is ACTIVE
    check_service_status "${service_name}" "${cluster_name}"
    local status_result=$?

    if [ $status_result -eq 2 ]; then
        echo -e "${RED}Service ${service_name} does not exist!${NC}"
        echo -e "${YELLOW}This usually means:${NC}"
        echo -e "${YELLOW}1. Services were deleted manually${NC}"
        echo -e "${YELLOW}2. Terraform needs to recreate them${NC}"
        echo -e "${YELLOW}3. Infrastructure deployment is required${NC}"
        echo ""
        echo -e "${BLUE}To fix this, run: ./deploy.sh --skip-service-update${NC}"
        echo -e "${BLUE}This will recreate the services via Terraform${NC}"
        return 2
    elif [ $status_result -ne 0 ]; then
        echo -e "${YELLOW}Service ${service_name} is not ready for update, skipping...${NC}"
        return 1
    fi

    while [ $retry -le $max_retries ]; do
        echo -e "${YELLOW}Update attempt ${retry}/${max_retries} for ${service_name}...${NC}"

        if aws ecs update-service --force-new-deployment --service "${service_name}" --cluster "${cluster_name}" --region "${AWS_REGION}" >/dev/null 2>&1; then
            echo -e "${GREEN}${service_type} service update initiated successfully.${NC}"
            return 0
        else
            local error_output=$(aws ecs update-service --force-new-deployment --service "${service_name}" --cluster "${cluster_name}" --region "${AWS_REGION}" 2>&1 || true)

            if [[ "$error_output" == *"ServiceNotActiveException"* ]]; then
                echo -e "${YELLOW}Service not active, waiting 30 seconds before retry...${NC}"
                sleep 30
            elif [[ "$error_output" == *"ServiceNotFoundException"* ]]; then
                echo -e "${RED}Service ${service_name} not found - it may have been deleted${NC}"
                echo -e "${YELLOW}Run: ./deploy.sh --skip-service-update to recreate services${NC}"
                return 2
            else
                echo -e "${RED}Error updating service: ${error_output}${NC}"
                sleep 10
            fi

            retry=$((retry + 1))
        fi
    done

    echo -e "${RED}Failed to update ${service_type} service after ${max_retries} attempts${NC}"
    return 1
}

# Track if any services need to be recreated
services_missing=false

if [ "$SKIP_BACKEND" = false ]; then
    update_ecs_service "${BACKEND_SERVICE_NAME}" "${BACKEND_CLUSTER_NAME}" "backend API"
    if [ $? -eq 2 ]; then services_missing=true; fi

    update_ecs_service "${BACKEND_SERVICE_WORKER_NAME}" "${BACKEND_CLUSTER_NAME}" "backend worker"
    if [ $? -eq 2 ]; then services_missing=true; fi

    update_ecs_service "${BACKEND_SERVICE_BEAT_NAME}" "${BACKEND_CLUSTER_NAME}" "backend beat"
    if [ $? -eq 2 ]; then services_missing=true; fi
fi

if [ "$SKIP_FRONTEND" = false ]; then
    update_ecs_service "${FRONTEND_SERVICE_NAME}" "${FRONTEND_CLUSTER_NAME}" "frontend"
    if [ $? -eq 2 ]; then services_missing=true; fi
fi

# If services are missing, provide helpful instructions
if [ "$services_missing" = true ]; then
    echo ""
    echo -e "${RED}⚠️  IMPORTANT: Some ECS services are missing!${NC}"
    echo -e "${YELLOW}This happened because services were deleted manually.${NC}"
    echo ""
    echo -e "${BLUE}To recreate the services:${NC}"
    echo -e "${BLUE}1. Run: ./deploy.sh --skip-service-update${NC}"
    echo -e "${BLUE}2. Wait for Terraform to recreate services${NC}"
    echo -e "${BLUE}3. Then run: ./deploy.sh (normal deployment)${NC}"
    echo ""
    echo -e "${YELLOW}Or run this one command to fix everything:${NC}"
    echo -e "${GREEN}./deploy.sh --skip-service-update && sleep 60 && ./deploy.sh${NC}"
fi

fi

# Get URLs and display them
if [ "$SKIP_TERRAFORM" = false ]; then
    echo -e "\n${GREEN}Getting deployment URLs...${NC}"
    cd "${IAC_DIR}"

    # Get URLs
    API_URL=$(terraform output -raw api_gateway_url 2>/dev/null)
    BACKEND_URL=$(terraform output -raw backend_load_balancer_dns 2>/dev/null)
    FRONTEND_URL=$(terraform output -raw frontend_load_balancer_dns 2>/dev/null)

    # Display URLs
    echo -e "\n${YELLOW}Deployment URLs:${NC}"
    if [ -n "$API_URL" ]; then
        echo -e "${BLUE}API Gateway URL:${NC} ${API_URL}"
    fi

    if [ -n "$BACKEND_URL" ]; then
        echo -e "${BLUE}Backend Load Balancer:${NC} http://${BACKEND_URL}"
    fi

    if [ -n "$FRONTEND_URL" ]; then
        echo -e "${BLUE}Frontend Load Balancer:${NC} http://${FRONTEND_URL}"
    fi

    # Display test commands
    if [ -n "$API_URL" ]; then
        echo -e "\n${YELLOW}Test commands for API endpoints:${NC}"
        echo -e "curl \"${API_URL}health\""
        echo -e "curl \"${API_URL}api/hello\""
    fi

    cd "${SCRIPT_DIR}"

    # Display API key information if applicable
    echo -e "\n${YELLOW}API Access Information:${NC}"
    echo -e "The API is secured with API keys. You can view and manage API keys in the AWS Console."
    echo -e "Usage plans have been created for different consumer types (frontend, partners, public)."
    echo -e "To use the API, add the 'x-api-key' header to your requests with the appropriate API key."
fi

# Post-deployment tasks
# if [ "$SKIP_SERVICE_UPDATE" = false ]; then
#     echo -e "\n${GREEN}Running post-deployment tasks...${NC}"

#     # Wait for service to stabilize before running management commands
#     echo -e "${YELLOW}Waiting for services to stabilize...${NC}"
#     sleep 120

#     # Get the running task ARN for the backend service
#     echo -e "${YELLOW}Getting backend task ARN...${NC}"
#     CLUSTER_NAME="${APP_NAME}-${ENV}-cluster"
#     SERVICE_NAME="${APP_NAME}-${ENV}-api-service"

#     TASK_ARN=$(aws ecs list-tasks \
#         --cluster "${CLUSTER_NAME}" \
#         --service-name "${SERVICE_NAME}" \
#         --region "${AWS_REGION}" \
#         --query 'taskArns[0]' \
#         --output text 2>/dev/null || echo "")

#     if [ -n "$TASK_ARN" ] && [ "$TASK_ARN" != "None" ] && [ "$TASK_ARN" != "null" ]; then



#         echo -e "${GREEN}Found backend task: ${TASK_ARN}${NC}"

#         # Run update_vacancies command
#         echo -e "${YELLOW}Running update_vacancies management command...${NC}"

#         if aws ecs execute-command \
#             --cluster "${CLUSTER_NAME}" \
#             --task "${TASK_ARN}" \
#             --container "${APP_NAME}" \
#             --interactive \
#             --command "poetry run celery -A jao_backend.common.celery worker --loglevel=INFO" \
#             --region "${AWS_REGION}" 2>/dev/null; then
#             echo -e "${GREEN}✅ update_vacancies command completed successfully${NC}"
#         else
#             echo -e "${YELLOW}⚠️ update_vacancies command failed or ECS exec not available${NC}"
#             echo -e "${BLUE}To run manually:${NC}"
#             echo -e "aws ecs execute-command --cluster ${CLUSTER_NAME} --task ${TASK_ARN} --container ${APP_NAME}-backend --interactive --command 'python src/manage.py update_vacancies --no-wait' --region ${AWS_REGION}"
#         fi

#         if aws ecs execute-command \
#             --cluster "${CLUSTER_NAME}" \
#             --task "${TASK_ARN}" \
#             --container "${APP_NAME}" \
#             --interactive \
#             --command "poetry run python src/manage.py update_vacancies --no-wait" \
#             --region "${AWS_REGION}" 2>/dev/null; then
#             echo -e "${GREEN}✅ update_vacancies command completed successfully${NC}"
#         else
#             echo -e "${YELLOW}⚠️ update_vacancies command failed or ECS exec not available${NC}"
#             echo -e "${BLUE}To run manually:${NC}"
#             echo -e "aws ecs execute-command --cluster ${CLUSTER_NAME} --task ${TASK_ARN} --container ${APP_NAME}-backend --interactive --command 'python src/manage.py update_vacancies --no-wait' --region ${AWS_REGION}"
#         fi

#     else
#         echo -e "${YELLOW}⚠️ Could not find running backend task${NC}"
#         echo -e "${BLUE}To run update_vacancies manually after deployment:${NC}"
#         echo -e "1. Get task ARN: aws ecs list-tasks --cluster ${CLUSTER_NAME} --service-name ${SERVICE_NAME} --region ${AWS_REGION}"
#         echo -e "2. Run command: aws ecs execute-command --cluster ${CLUSTER_NAME} --task TASK_ARN --container ${APP_NAME}-backend --interactive --command 'python src/manage.py update_vacancies --no-wait' --region ${AWS_REGION}"
#     fi
# else
#     echo -e "\n${YELLOW}Service updates were skipped - post-deployment tasks not executed${NC}"
# fi

# Final steps and validation
echo -e "\n${GREEN}Deployment completed!${NC}"
echo -e "${BLUE}Deployment summary:${NC}"
if [ "$SKIP_BACKEND" = true ]; then
    echo -e "Backend deployment: ${YELLOW}SKIPPED${NC}"
else
    echo -e "Backend deployment: ${GREEN}COMPLETED${NC}"
fi
if [ "$SKIP_FRONTEND" = true ]; then
    echo -e "Frontend deployment: ${YELLOW}SKIPPED${NC}"
else
    echo -e "Frontend deployment: ${GREEN}COMPLETED${NC}"
fi
if [ "$SKIP_TERRAFORM" = true ]; then
    echo -e "Terraform deployment: ${YELLOW}SKIPPED${NC}"
else
    echo -e "Terraform deployment: ${GREEN}COMPLETED${NC}"
fi
if [ "$SKIP_SERVICE_UPDATE" = true ]; then
    echo -e "Service updates: ${YELLOW}SKIPPED${NC}"
else
    echo -e "Service updates: ${GREEN}COMPLETED${NC}"
fi
if [ "$SKIP_EXISTING" = true ] || [ "$SKIP_VPC" = true ] || [ "$SKIP_CLOUDWATCH" = true ] || [ "$SKIP_IAM_ROLES" = true ]; then
    echo -e "Resource skipping: ${YELLOW}ENABLED${NC}"
else
    echo -e "Resource skipping: ${GREEN}DISABLED${NC}"
fi
echo -e "${YELLOW}Important notes:${NC}"
echo -e "1. The backend API now has enhanced monitoring and throttling for third-party consumers"
echo -e "2. Different usage plans are in place for frontend (20%), partners (30%), and public (50%) traffic"
echo -e "3. If you encounter 'resource already exists' errors, use one of these options:"
echo -e "   ${BLUE}--skip-existing${NC}             Skip all resources that commonly conflict"
echo -e "   ${BLUE}--skip-cloudwatch${NC}           Skip CloudWatch log groups creation"
echo -e "   ${BLUE}--skip-iam-roles${NC}            Skip IAM roles creation"
echo -e ""
echo -e "   ${RED}IMPORTANT: For VPC errors, use BOTH options together:${NC}"
echo -e "   ${BLUE}--skip-vpc --existing-vpc-id vpc-xxx${NC}"
echo -e ""
echo -e "   Find your VPC IDs with: ${BLUE}aws ec2 describe-vpcs${NC}"
echo -e "   ${RED}NEVER use --skip-vpc without --existing-vpc-id${NC}"
echo -e "4. For CloudWatch log group errors, use:"
echo -e "   ${BLUE}--skip-cloudwatch${NC}                   Skip CloudWatch log groups creation"
echo -e "   ${BLUE}--backend-log-group NAME${NC}            Use existing backend log group"
echo -e "   ${BLUE}--frontend-log-group NAME${NC}           Use existing frontend log group"
echo -e "5. See RESOURCE_ERRORS.md for detailed troubleshooting guidance"
echo -e "6. The frontend application connects to the backend through the API Gateway"
echo -e "7. Both services have their own ECS clusters for independent scaling"
echo -e "8. The shared schema files are used by both frontend and backend for consistency"
echo -e "\n${GREEN}If you experience any issues:${NC}"
echo -e "1. Check CloudWatch dashboards for API Gateway, Backend, and Frontend metrics"
echo -e "2. Verify the ECS tasks are running with correct images"
echo -e "3. Check that the frontend can access the backend API via the API Gateway"
echo -e "4. For Docker build issues:"
echo -e "   - Run 'docker system prune' to clean up unused resources"
echo -e "   - Try building with 'docker build --no-cache' to avoid using cached layers"
echo -e "   - Verify connectivity to package repositories (PyPI, NPM)"
echo -e "   - Check that the schemas package can be built independently"
echo -e "   - Run 'docker builder prune' to remove all build cache"
echo -e "   - Examine the Dockerfile to ensure the build stages are correct"
echo -e "   - Try adding '--network=host' if network connectivity is the issue"
