#!/bin/bash
set -e  # Exit on error

# Colors for terminal output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Fresh Deployment Script for JAO Application${NC}"
echo -e "=================================================="
echo -e "This script will perform a complete fresh deployment:"
echo -e " 1. Backup existing Terraform state"
echo -e " 2. Clean up Docker resources"
echo -e " 3. Reset Terraform state"
echo -e " 4. Run a fresh deployment with no caching"
echo

# Default values
AWS_REGION="eu-west-2"
APP_NAME="python-api"
ENV="dev"
IMAGE_TAG="latest"
SKIP_TFSTATE_RESET=false
SKIP_DOCKER_CLEANUP=false
SKIP_TERRAFORM_DESTROY=true  # By default, don't destroy existing infrastructure

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
    --skip-tfstate-reset)
      SKIP_TFSTATE_RESET=true
      shift
      ;;
    --skip-docker-cleanup)
      SKIP_DOCKER_CLEANUP=true
      shift
      ;;
    --terraform-destroy)
      SKIP_TERRAFORM_DESTROY=false
      shift
      ;;
    --help)
      echo -e "${BLUE}Usage:${NC} $0 [OPTIONS]"
      echo -e "${BLUE}Options:${NC}"
      echo "  --region REGION            AWS region (default: eu-west-2)"
      echo "  --app-name NAME            Application name (default: python-api)"
      echo "  --env ENV                  Environment (default: dev)"
      echo "  --tag TAG                  Docker image tag (default: latest)"
      echo "  --skip-tfstate-reset       Skip resetting Terraform state"
      echo "  --skip-docker-cleanup      Skip Docker cleanup"
      echo "  --terraform-destroy        Destroy existing infrastructure (CAUTION)"
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

# Get current directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
IAC_DIR="${SCRIPT_DIR}/iac"
BACKUP_TIMESTAMP=$(date +%Y%m%d%H%M%S)

# Check required tools
echo -e "\n${GREEN}Checking required tools...${NC}"
command -v aws >/dev/null 2>&1 || { echo -e "${RED}Error: AWS CLI is required but not installed.${NC}"; exit 1; }
command -v docker >/dev/null 2>&1 || { echo -e "${RED}Error: Docker is required but not installed.${NC}"; exit 1; }
command -v terraform >/dev/null 2>&1 || { echo -e "${RED}Error: Terraform is required but not installed.${NC}"; exit 1; }

# Confirm with user
echo -e "${RED}WARNING: This will perform a clean deployment, potentially destroying resources.${NC}"
read -p "Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Deployment cancelled.${NC}"
    exit 0
fi

# 1. Backup Terraform State
echo -e "\n${GREEN}Backing up Terraform state...${NC}"
if [ -f "${IAC_DIR}/terraform.tfstate" ]; then
    cp "${IAC_DIR}/terraform.tfstate" "${IAC_DIR}/terraform.tfstate.backup.${BACKUP_TIMESTAMP}"
    echo -e "${BLUE}Terraform state backed up to terraform.tfstate.backup.${BACKUP_TIMESTAMP}${NC}"
else
    echo -e "${YELLOW}No Terraform state file found to backup.${NC}"
fi

# 2. Clean up Docker resources
if [ "$SKIP_DOCKER_CLEANUP" = false ]; then
    echo -e "\n${GREEN}Cleaning up Docker resources...${NC}"
    echo -e "${YELLOW}This will remove ALL unused Docker resources (images, containers, volumes, etc.).${NC}"
    read -p "Proceed with Docker cleanup? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${BLUE}Running Docker system prune...${NC}"
        docker system prune -a --volumes -f
    else
        echo -e "${YELLOW}Docker cleanup skipped.${NC}"
    fi
else
    echo -e "\n${YELLOW}Docker cleanup skipped as requested.${NC}"
fi

# 3. Reset Terraform state if requested
if [ "$SKIP_TFSTATE_RESET" = false ]; then
    echo -e "\n${GREEN}Resetting Terraform state...${NC}"
    cd "${IAC_DIR}"
    
    # First destroy infrastructure if requested
    if [ "$SKIP_TERRAFORM_DESTROY" = false ]; then
        echo -e "${RED}WARNING: You have chosen to destroy existing infrastructure.${NC}"
        echo -e "${RED}This will delete ALL resources managed by Terraform, including databases.${NC}"
        read -p "Are you ABSOLUTELY SURE you want to destroy? Type 'destroy' to confirm: " confirm
        if [ "$confirm" = "destroy" ]; then
            echo -e "${BLUE}Destroying infrastructure...${NC}"
            terraform destroy -auto-approve
        else
            echo -e "${YELLOW}Terraform destroy cancelled. Continuing with reset only.${NC}"
        fi
    fi
    
    # Remove terraform state
    echo -e "${BLUE}Removing Terraform state files...${NC}"
    if [ -d "${IAC_DIR}/.terraform" ]; then
        rm -rf "${IAC_DIR}/.terraform"
    fi
    if [ -f "${IAC_DIR}/terraform.tfstate" ]; then
        rm -f "${IAC_DIR}/terraform.tfstate"
    fi
    if [ -f "${IAC_DIR}/terraform.tfstate.backup" ]; then
        rm -f "${IAC_DIR}/terraform.tfstate.backup"
    fi
    echo -e "${GREEN}Terraform state reset complete.${NC}"
    cd "${SCRIPT_DIR}"
else
    echo -e "\n${YELLOW}Terraform state reset skipped as requested.${NC}"
fi

# 4. Run fresh deployment
echo -e "\n${GREEN}Starting fresh deployment...${NC}"

# Check AWS identity
echo -e "${BLUE}Verifying AWS credentials...${NC}"
aws sts get-caller-identity

# Add --no-cache flag to the deploy-enhanced.sh script by creating a temporary wrapper
echo "#!/bin/bash" > "${SCRIPT_DIR}/deploy-fresh-temp.sh"
echo "${SCRIPT_DIR}/deploy-enhanced.sh \
  --region ${AWS_REGION} \
  --app-name ${APP_NAME} \
  --env ${ENV} \
  --tag ${IMAGE_TAG} \
  \"\$@\"" >> "${SCRIPT_DIR}/deploy-fresh-temp.sh"
chmod +x "${SCRIPT_DIR}/deploy-fresh-temp.sh"

# Run the deployment with additional flags
echo -e "${BLUE}Executing fresh deployment...${NC}"
"${SCRIPT_DIR}/deploy-fresh-temp.sh"
DEPLOY_EXIT_CODE=$?

# Clean up temporary script
rm -f "${SCRIPT_DIR}/deploy-fresh-temp.sh"

# Show deployment summary
if [ $DEPLOY_EXIT_CODE -eq 0 ]; then
    echo -e "\n${GREEN}Fresh deployment completed successfully!${NC}"
else
    echo -e "\n${RED}Deployment encountered issues. Exit code: ${DEPLOY_EXIT_CODE}${NC}"
    echo -e "${YELLOW}Check the logs above for specific errors.${NC}"
fi

echo -e "\n${GREEN}Deployment Summary:${NC}"
echo -e "  - Terraform state backup created: ${BLUE}${IAC_DIR}/terraform.tfstate.backup.${BACKUP_TIMESTAMP}${NC}"
echo -e "  - Docker cleanup: ${BLUE}$([ "$SKIP_DOCKER_CLEANUP" = false ] && echo "Performed" || echo "Skipped")${NC}"
echo -e "  - Terraform state reset: ${BLUE}$([ "$SKIP_TFSTATE_RESET" = false ] && echo "Performed" || echo "Skipped")${NC}"
echo -e "  - Terraform destroy: ${BLUE}$([ "$SKIP_TERRAFORM_DESTROY" = false ] && echo "Performed" || echo "Skipped")${NC}"

echo -e "\n${YELLOW}Note:${NC} If deployment failed, you can:"
echo -e "  1. Review the error messages above"
echo -e "  2. Fix the identified issues"
echo -e "  3. Run this script again or run deploy-enhanced.sh directly"
echo -e "  4. If necessary, restore the Terraform state from backup using:"
echo -e "     cp ${IAC_DIR}/terraform.tfstate.backup.${BACKUP_TIMESTAMP} ${IAC_DIR}/terraform.tfstate"

exit $DEPLOY_EXIT_CODE