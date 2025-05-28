#!/bin/bash
set -eo pipefail

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Display header
echo -e "${BLUE}${BOLD}=== LocalStack API Gateway Deployment ===${NC}"

# Check for required tools
for cmd in docker docker-compose terraform aws python3; do
    if ! command -v $cmd &> /dev/null; then
        echo -e "${RED}Error: $cmd is required but not installed.${NC}"
        exit 1
    fi
done

# Parse arguments
CLEAN=false
SKIP_TEST=false

while [[ "$#" -gt 0 ]]; do
    case $1 in
        --clean) CLEAN=true ;;
        --skip-test) SKIP_TEST=true ;;
        --help)
            echo "Usage: $0 [options]"
            echo "Options:"
            echo "  --clean     Force removal of all LocalStack containers and volumes"
            echo "  --skip-test Skip endpoint testing after deployment"
            echo "  --help      Show this help message"
            exit 0
            ;;
        *) echo "Unknown parameter: $1"; exit 1 ;;
    esac
    shift
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

if [ "$CLEAN" = true ]; then
    echo -e "${YELLOW}Forcing clean environment...${NC}"
    docker-compose -f "$SCRIPT_DIR/docker-compose.yml" down -v 2>/dev/null || true
    docker ps -a | grep localstack | awk '{print $1}' | xargs -r docker rm -f 2>/dev/null || true
    docker volume ls | grep localstack | awk '{print $2}' | xargs -r docker volume rm 2>/dev/null || true
    find /tmp -name "localstack*" -type d -maxdepth 1 -exec rm -rf {} + 2>/dev/null || true
    rm -f "$SCRIPT_DIR/terraform.tfstate" "$SCRIPT_DIR/terraform.tfstate.backup" 2>/dev/null || true
    echo -e "${GREEN}Environment cleaned!${NC}"
fi

# Force remove any existing LocalStack containers
echo -e "${YELLOW}Cleaning up any existing LocalStack containers...${NC}"
docker ps -a | grep localstack | awk '{print $1}' | xargs -r docker rm -f >/dev/null 2>&1 || true
docker volume ls | grep localstack_data | awk '{print $2}' | xargs -r docker volume rm >/dev/null 2>&1 || true

# Start LocalStack with a fresh configuration
echo -e "${GREEN}Starting LocalStack...${NC}"
cd "$SCRIPT_DIR"
docker-compose -f docker-compose.yml up -d localstack

# Wait for LocalStack to be ready
echo -e "${YELLOW}Waiting for LocalStack to be ready...${NC}"
max_attempts=30
attempt=0

while [ $attempt -lt $max_attempts ]; do
  attempt=$((attempt+1))

  health_status=$(curl -s http://localhost:4566/_localstack/health 2>/dev/null)
  if [[ $health_status == *"\"ready\": true"* ]] || [[ $health_status == *"\"running\": true"* ]]; then
    echo -e "${GREEN}LocalStack is ready!${NC}"
    break
  fi

  if [ $attempt -eq $max_attempts ]; then
    echo -e "${RED}LocalStack failed to start after $max_attempts attempts.${NC}"
    docker logs localstack
    exit 1
  fi

  echo -e "${YELLOW}Waiting... ($attempt/$max_attempts)${NC}"
  sleep 2
done

# Create LocalStack tfvars file
echo -e "${GREEN}Creating Terraform configuration...${NC}"
cat > "$SCRIPT_DIR/local.tfvars" <<EOF
app_name = "localapi"
environment = "local"
aws_region = "eu-west-2"
localstack_enabled = true

vpc_cidr = "10.0.0.0/16"
availability_zones = ["eu-west-2a", "eu-west-2b"]
private_subnet_cidrs = ["10.0.1.0/24", "10.0.2.0/24"]
public_subnet_cidrs = ["10.0.101.0/24", "10.0.102.0/24"]

container_port = 5000
task_cpu = 256
task_memory = 512
desired_count = 1

environment_variables = {
  LOG_LEVEL = "INFO"
  API_ENV = "local"
  ENABLE_DEBUG = "true"
}
EOF

# Set up AWS CLI to work with LocalStack
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_DEFAULT_REGION=eu-west-2

# Initialize and apply Terraform directly in the localstack directory
echo -e "${GREEN}Initializing Terraform...${NC}"
terraform -chdir="$SCRIPT_DIR" init

echo -e "${GREEN}Applying Terraform configuration...${NC}"
terraform -chdir="$SCRIPT_DIR" apply -var-file=local.tfvars -auto-approve

# Start the API container
echo -e "${GREEN}Starting API container...${NC}"
docker-compose -f docker-compose.yml up -d app

# Wait for API container to be ready
echo -e "${YELLOW}Waiting for API container to be ready...${NC}"
max_attempts=15
attempt=0

while [ $attempt -lt $max_attempts ]; do
  attempt=$((attempt+1))

  if curl -s http://localhost:5000/health >/dev/null 2>&1; then
    echo -e "${GREEN}API container is ready!${NC}"
    break
  fi

  if [ $attempt -eq $max_attempts ]; then
    echo -e "${YELLOW}API container might not be ready, but continuing...${NC}"
  fi

  echo -e "${YELLOW}Waiting for API... ($attempt/$max_attempts)${NC}"
  sleep 2
done

# Query both API Gateway v1 and v2 APIs to identify which is being used
API_ID_V1=""
API_ID_V2=""

echo -e "${YELLOW}Detecting API Gateway resources...${NC}"
# Try to get API Gateway v1 (REST) APIs
if API_LIST_V1=$(aws --endpoint-url=http://localhost:4566 apigateway get-rest-apis 2>/dev/null); then
  API_ID_V1=$(echo "$API_LIST_V1" | grep -o '"id": "[^"]*' | head -1 | cut -d'"' -f4)
  if [ -n "$API_ID_V1" ]; then
    echo -e "${GREEN}Found REST API Gateway: $API_ID_V1${NC}"
  fi
fi

# Try to get API Gateway v2 (HTTP) APIs
if API_LIST_V2=$(aws --endpoint-url=http://localhost:4566 apigatewayv2 get-apis 2>/dev/null); then
  API_ID_V2=$(echo "$API_LIST_V2" | grep -o '"ApiId": "[^"]*' | head -1 | cut -d'"' -f4)
  if [ -n "$API_ID_V2" ]; then
    echo -e "${GREEN}Found HTTP API Gateway: $API_ID_V2${NC}"
  fi
fi

# Determine which API type to use for testing
if [ -n "$API_ID_V2" ]; then
  # If HTTP API (v2) is found, prefer it
  API_TYPE="v2"
  API_ID="$API_ID_V2"
  API_URL="http://localhost:4566/apis/${API_ID}"
  echo -e "${GREEN}Using HTTP API (ApiGatewayV2)${NC}"
elif [ -n "$API_ID_V1" ]; then
  # Fall back to REST API (v1)
  API_TYPE="v1"
  API_ID="$API_ID_V1"
  API_URL="http://localhost:4566/restapis/${API_ID}/local/_user_request_"
  echo -e "${GREEN}Using REST API (ApiGateway)${NC}"
else
  # If no APIs found, use a wildcard for v1 (more common with LocalStack)
  API_TYPE="v1"
  API_ID="*"
  API_URL="http://localhost:4566/restapis/*/local/_user_request_"
  echo -e "${YELLOW}No API ID found, using wildcard${NC}"
fi

# Install test requirements if needed
if [ ! "$SKIP_TEST" = true ]; then
  echo -e "${YELLOW}Checking test dependencies...${NC}"
  if [ -f "$PROJECT_ROOT/test-requirements.txt" ]; then
    pip3 install -r "$PROJECT_ROOT/test-requirements.txt" >/dev/null 2>&1 || {
      echo -e "${YELLOW}Some test dependencies could not be installed.${NC}"
    }
  fi
fi

# Display information
echo -e "${BLUE}${BOLD}=== Deployment Complete ===${NC}"
echo -e "${GREEN}API Gateway URL: $API_URL${NC}"
echo -e "${GREEN}API Endpoints:${NC}"
echo -e "  GET $API_URL/api/hello"
echo -e "  POST $API_URL/api/data"
echo -e "  GET $API_URL/health"
echo -e "  GET http://localhost:5000/health (Direct container access)"

# Test endpoints
if [ ! "$SKIP_TEST" = true ]; then
  echo -e "${YELLOW}Testing endpoints:${NC}"

  # Simplify testing if we know the API URL format
  echo -e "${YELLOW}Testing GET /health endpoint:${NC}"
  if curl -s "${API_URL}/health" | grep -q "healthy"; then
    echo -e "${GREEN}✅ Health endpoint working${NC}"
  else
    echo -e "${RED}❌ Health endpoint failed${NC}"
    echo -e "${YELLOW}Trying direct access to container...${NC}"
    curl -v "http://localhost:5000/health"
  fi

  echo -e "${YELLOW}Testing GET /api/hello endpoint:${NC}"
  if curl -s "${API_URL}/api/hello" | grep -q "message"; then
    echo -e "${GREEN}✅ Hello endpoint working${NC}"
  else
    echo -e "${RED}❌ Hello endpoint failed${NC}"
    echo -e "${YELLOW}Trying direct access to container...${NC}"
    curl -v "http://localhost:5000/api/hello"
  fi

  echo -e "${YELLOW}Testing POST /api/data endpoint:${NC}"
  if curl -s -X POST -H "Content-Type: application/json" -d '{"test":"data"}' "${API_URL}/api/data" | grep -q "success"; then
    echo -e "${GREEN}✅ Data endpoint working${NC}"
  else
    echo -e "${RED}❌ Data endpoint failed${NC}"
    echo -e "${YELLOW}Trying direct access to container...${NC}"
    curl -v -X POST -H "Content-Type: application/json" -d '{"test":"data"}' "http://localhost:5000/api/data"
  fi

  # Run the test script if available
  if [ -f "$PROJECT_ROOT/test-localstack-api.py" ]; then
    echo -e "${YELLOW}Running more comprehensive tests with test script...${NC}"
    cd "$PROJECT_ROOT"
    python3 test-localstack-api.py --url "http://localhost:4566/" --api-id "$API_ID" || {
      echo -e "${YELLOW}Some tests from the test script failed.${NC}"
    }
    cd "$SCRIPT_DIR"
  fi
fi

echo -e "\n${GREEN}${BOLD}=== LocalStack Environment Ready ===${NC}"
echo -e "${GREEN}Commands:${NC}"
echo -e "  View LocalStack logs:  ${YELLOW}docker logs localstack${NC}"
echo -e "  View API logs:         ${YELLOW}docker logs api-backend${NC}"
echo -e "  Stop environment:      ${YELLOW}docker-compose -f docker-compose.yml down -v${NC}"
echo -e "  Run tests:             ${YELLOW}cd $PROJECT_ROOT && python3 test-localstack-api.py --url http://localhost:4566/ --api-id $API_ID${NC}"
echo -e "  Debug API Gateway:     ${YELLOW}./debug.sh${NC}"
