#!/bin/bash
set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Display header
echo -e "${BLUE}${BOLD}=== LocalStack API Test Runner ===${NC}"

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
  echo -e "${RED}Error: Python 3 is not installed.${NC}"
  exit 1
fi

# Install requirements if needed
echo -e "${YELLOW}Checking/installing required Python packages...${NC}"
pip install -r test-requirements.txt >/dev/null 2>&1 || {
  echo -e "${YELLOW}Installing required Python packages with pip3...${NC}"
  pip3 install -r test-requirements.txt >/dev/null 2>&1 || {
    echo -e "${RED}Failed to install required packages. Make sure pip is installed.${NC}"
    exit 1
  }
}

echo -e "${GREEN}Required packages installed!${NC}"

# Get API Gateway URL
API_URL="http://localhost:4566/"

# Check if API ID is specified as an argument
API_ID="*"
if [ -n "$1" ]; then
  API_ID="$1"
fi

# Run the test script
echo -e "${YELLOW}Running API tests...${NC}"
python3 test-localstack-api.py --url "$API_URL" --api-id "$API_ID"

# Check exit code
if [ $? -eq 0 ]; then
  echo -e "${GREEN}${BOLD}Tests completed successfully!${NC}"
else
  echo -e "${RED}${BOLD}Some tests failed. Check the output above for details.${NC}"
  exit 1
fi
