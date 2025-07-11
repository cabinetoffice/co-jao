#!/bin/bash

# JAO Update Vacancies Script
# This script runs the update_vacancies Django management command on the ECS backend container

set -e  # Exit on error

# Colors for terminal output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
AWS_REGION="eu-west-2"
APP_NAME="jao"
ENV="dev"
CLUSTER_NAME="${APP_NAME}-${ENV}-cluster"
SERVICE_NAME="${APP_NAME}-${ENV}-service"
CONTAINER_NAME="${APP_NAME}-backend"
COMMAND="poetry run python src/manage.py update_vacancies --no-wait"
USE_POETRY=true

echo -e "${BLUE}JAO Update Vacancies Script${NC}"
echo -e "================================="

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --region REGION        AWS region (default: ${AWS_REGION})"
    echo "  --env ENV              Environment (default: ${ENV})"
    echo "  --cluster CLUSTER      ECS cluster name (default: auto-generated)"
    echo "  --service SERVICE      ECS service name (default: auto-generated)"
    echo "  --container CONTAINER  Container name (default: ${CONTAINER_NAME})"
    echo "  --command COMMAND      Command to run (default: update_vacancies)"
    echo "  --wait                 Run with wait (removes --no-wait flag)"
    echo "  --no-poetry            Don't use poetry run prefix"
    echo "  --dry-run              Show what would be executed without running"
    echo "  --shell                Open interactive shell instead"
    echo "  --help                 Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                                    # Run with defaults"
    echo "  $0 --env prod                         # Run in production"
    echo "  $0 --wait                            # Run with wait"
    echo "  $0 --shell                           # Open Django shell"
    echo "  $0 --no-poetry                      # Run without poetry"
    echo "  $0 --dry-run                         # Preview command"
    echo "  $0 --command \"poetry run python src/manage.py collectstatic --noinput\""
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --region)
            AWS_REGION="$2"
            shift 2
            ;;
        --env)
            ENV="$2"
            CLUSTER_NAME="${APP_NAME}-${ENV}-cluster"
            SERVICE_NAME="${APP_NAME}-${ENV}-service"
            shift 2
            ;;
        --cluster)
            CLUSTER_NAME="$2"
            shift 2
            ;;
        --service)
            SERVICE_NAME="$2"
            shift 2
            ;;
        --container)
            CONTAINER_NAME="$2"
            shift 2
            ;;
        --command)
            COMMAND="$2"
            USE_POETRY=false
            shift 2
            ;;
        --wait)
            COMMAND="poetry run python src/manage.py update_vacancies"
            shift
            ;;
        --no-poetry)
            USE_POETRY=false
            COMMAND="python src/manage.py update_vacancies --no-wait"
            shift
            ;;
        --shell)
            COMMAND="poetry run python src/manage.py shell"
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --help)
            show_usage
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown argument: $1${NC}"
            echo -e "Run '$0 --help' for usage."
            exit 1
            ;;
    esac
done

echo -e "Configuration:"
echo -e "  Region: ${BLUE}${AWS_REGION}${NC}"
echo -e "  Environment: ${BLUE}${ENV}${NC}"
echo -e "  Cluster: ${BLUE}${CLUSTER_NAME}${NC}"
echo -e "  Service: ${BLUE}${SERVICE_NAME}${NC}"
echo -e "  Container: ${BLUE}${CONTAINER_NAME}${NC}"
echo -e "  Command: ${BLUE}${COMMAND}${NC}"
echo -e "  Use Poetry: ${BLUE}${USE_POETRY}${NC}"
echo ""

# Check if AWS CLI is available
if ! command -v aws &> /dev/null; then
    echo -e "${RED}Error: AWS CLI is not installed or not in PATH${NC}"
    echo -e "Install it with: pip install awscli"
    exit 1
fi

# Check AWS credentials
echo -e "${YELLOW}Checking AWS credentials...${NC}"
if ! aws sts get-caller-identity --region "${AWS_REGION}" >/dev/null 2>&1; then
    echo -e "${RED}Error: AWS credentials not configured or invalid${NC}"
    echo -e "Configure with: aws configure"
    exit 1
fi

# Get AWS account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --region "${AWS_REGION}" --query 'Account' --output text 2>/dev/null)
echo -e "${GREEN}✓ AWS credentials valid (Account: ${AWS_ACCOUNT_ID})${NC}"

# Check if cluster exists
echo -e "${YELLOW}Checking if ECS cluster exists...${NC}"
if aws ecs describe-clusters --clusters "${CLUSTER_NAME}" --region "${AWS_REGION}" --query 'clusters[0].status' --output text 2>/dev/null | grep -q "ACTIVE"; then
    echo -e "${GREEN}✓ Cluster '${CLUSTER_NAME}' is active${NC}"
else
    echo -e "${RED}Error: Cluster '${CLUSTER_NAME}' not found or not active${NC}"
    echo -e "${YELLOW}Available clusters:${NC}"
    aws ecs list-clusters --region "${AWS_REGION}" --query 'clusterArns[]' --output table 2>/dev/null || echo "No clusters found"
    exit 1
fi

# Check if service exists and find the actual service name
echo -e "${YELLOW}Checking if ECS service exists...${NC}"
ACTUAL_SERVICE_NAME=""

# Try different possible service names
for possible_service in "${SERVICE_NAME}" "${APP_NAME}-${ENV}-api-service" "${APP_NAME}-api-service" "${APP_NAME}-service"; do
    if aws ecs describe-services --cluster "${CLUSTER_NAME}" --services "${possible_service}" --region "${AWS_REGION}" --query 'services[0].status' --output text 2>/dev/null | grep -q "ACTIVE"; then
        ACTUAL_SERVICE_NAME="${possible_service}"
        echo -e "${GREEN}✓ Service '${possible_service}' is active${NC}"
        break
    fi
done

if [ -z "$ACTUAL_SERVICE_NAME" ]; then
    echo -e "${RED}Error: Could not find an active service${NC}"
    echo -e "${YELLOW}Available services in cluster '${CLUSTER_NAME}':${NC}"
    aws ecs list-services --cluster "${CLUSTER_NAME}" --region "${AWS_REGION}" --query 'serviceArns[]' --output table 2>/dev/null || echo "No services found"
    exit 1
fi

# Get running task ARN
echo -e "${YELLOW}Finding running task...${NC}"
TASK_ARN=$(aws ecs list-tasks \
    --cluster "${CLUSTER_NAME}" \
    --service-name "${ACTUAL_SERVICE_NAME}" \
    --region "${AWS_REGION}" \
    --query 'taskArns[0]' \
    --output text 2>/dev/null)

if [ -z "$TASK_ARN" ] || [ "$TASK_ARN" = "None" ] || [ "$TASK_ARN" = "null" ]; then
    echo -e "${RED}Error: No running tasks found for service '${ACTUAL_SERVICE_NAME}'${NC}"
    echo -e "${YELLOW}Service might be scaling up or experiencing issues${NC}"

    # Show service details
    echo -e "\n${YELLOW}Service status:${NC}"
    aws ecs describe-services \
        --cluster "${CLUSTER_NAME}" \
        --services "${ACTUAL_SERVICE_NAME}" \
        --region "${AWS_REGION}" \
        --query 'services[0].{Status:status,Running:runningCount,Desired:desiredCount,Pending:pendingCount}' \
        --output table 2>/dev/null || echo "Could not get service status"

    exit 1
fi

echo -e "${GREEN}✓ Found running task: ${TASK_ARN}${NC}"

# Check if ECS exec is enabled
echo -e "${YELLOW}Checking if ECS exec is enabled...${NC}"
EXEC_ENABLED=$(aws ecs describe-services \
    --cluster "${CLUSTER_NAME}" \
    --services "${ACTUAL_SERVICE_NAME}" \
    --region "${AWS_REGION}" \
    --query 'services[0].enableExecuteCommand' \
    --output text 2>/dev/null)

if [ "$EXEC_ENABLED" != "True" ]; then
    echo -e "${YELLOW}⚠️ ECS exec is not enabled for this service${NC}"
    echo -e "${BLUE}To enable ECS exec, run:${NC}"
    echo -e "aws ecs update-service --cluster ${CLUSTER_NAME} --service ${ACTUAL_SERVICE_NAME} --enable-execute-command --region ${AWS_REGION}"
    echo ""
    echo -e "${YELLOW}Attempting to run command anyway...${NC}"
else
    echo -e "${GREEN}✓ ECS exec is enabled${NC}"
fi

# Check container name
echo -e "${YELLOW}Verifying container name...${NC}"
AVAILABLE_CONTAINERS=$(aws ecs describe-task-definition \
    --task-definition $(aws ecs describe-tasks --cluster "${CLUSTER_NAME}" --tasks "${TASK_ARN}" --region "${AWS_REGION}" --query 'tasks[0].taskDefinitionArn' --output text) \
    --region "${AWS_REGION}" \
    --query 'taskDefinition.containerDefinitions[].name' \
    --output text 2>/dev/null)

if echo "$AVAILABLE_CONTAINERS" | grep -q "$CONTAINER_NAME"; then
    echo -e "${GREEN}✓ Container '${CONTAINER_NAME}' found${NC}"
else
    echo -e "${YELLOW}⚠️ Container '${CONTAINER_NAME}' not found. Available containers:${NC}"
    echo "$AVAILABLE_CONTAINERS" | tr '\t' '\n' | sed 's/^/  - /'

    # Try to find the backend container
    BACKEND_CONTAINER=$(echo "$AVAILABLE_CONTAINERS" | tr '\t' '\n' | grep -E "(backend|api|web)" | head -1)
    if [ -n "$BACKEND_CONTAINER" ]; then
        echo -e "${YELLOW}Using container: ${BACKEND_CONTAINER}${NC}"
        CONTAINER_NAME="$BACKEND_CONTAINER"
    else
        echo -e "${RED}Could not find a suitable backend container${NC}"
        exit 1
    fi
fi

# Show what will be executed
echo -e "\n${BLUE}Command to execute:${NC}"
echo -e "aws ecs execute-command \\"
echo -e "  --cluster \"${CLUSTER_NAME}\" \\"
echo -e "  --task \"${TASK_ARN}\" \\"
echo -e "  --container \"${CONTAINER_NAME}\" \\"
echo -e "  --interactive \\"
echo -e "  --command \"${COMMAND}\" \\"
echo -e "  --region \"${AWS_REGION}\""

if [ "$DRY_RUN" = true ]; then
    echo -e "\n${YELLOW}Dry run mode - command not executed${NC}"
    echo -e "\n${BLUE}Additional debugging info:${NC}"
    echo -e "Service: ${ACTUAL_SERVICE_NAME}"
    echo -e "Available containers: ${AVAILABLE_CONTAINERS}"
    exit 0
fi

echo ""
read -p "Do you want to execute this command? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Command execution cancelled${NC}"
    exit 0
fi

# Execute the command
echo -e "\n${GREEN}Executing command...${NC}"
echo -e "${YELLOW}Note: This will open an interactive session. Press Ctrl+C to exit if needed.${NC}"
echo ""

if aws ecs execute-command \
    --cluster "${CLUSTER_NAME}" \
    --task "${TASK_ARN}" \
    --container "${CONTAINER_NAME}" \
    --interactive \
    --command "${COMMAND}" \
    --region "${AWS_REGION}"; then
    echo -e "\n${GREEN}✅ Command executed successfully${NC}"
else
    echo -e "\n${RED}❌ Command execution failed${NC}"
    echo -e "${YELLOW}Common issues:${NC}"
    echo -e "1. ECS exec not enabled on the service"
    echo -e "2. Container not found or not running"
    echo -e "3. Command syntax error"
    echo -e "4. Missing dependencies (try with --no-poetry)"
    echo -e "5. AWS permissions insufficient"
    echo -e "6. Network connectivity issues"
    echo ""
    echo -e "${BLUE}To debug:${NC}"
    echo -e "1. Check task status: aws ecs describe-tasks --cluster ${CLUSTER_NAME} --tasks ${TASK_ARN} --region ${AWS_REGION}"
    echo -e "2. Check container logs: aws logs tail /ecs/${APP_NAME}-${ENV}-backend --follow --region ${AWS_REGION}"
    echo -e "3. Try with shell: $0 --shell"
    echo -e "4. Try without poetry: $0 --no-poetry"
    exit 1
fi

echo -e "\n${BLUE}Script completed${NC}"
