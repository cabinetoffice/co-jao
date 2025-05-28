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
echo -e "${BLUE}${BOLD}=== LocalStack API Gateway Debug ===${NC}"

# Configure AWS CLI for LocalStack
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_DEFAULT_REGION=eu-west-2
ENDPOINT="http://localhost:4566"

# Check LocalStack health
echo -e "${YELLOW}Checking LocalStack health...${NC}"
HEALTH=$(curl -s $ENDPOINT/_localstack/health)
echo -e "${GREEN}LocalStack Health:${NC}"
echo $HEALTH | python3 -m json.tool 2>/dev/null || echo $HEALTH

# Detect which API types are present
echo -e "\n${YELLOW}Detecting API Gateway resources...${NC}"

# Try to get API Gateway v1 (REST) APIs
REST_APIS_FOUND=false
if REST_APIS=$(aws --endpoint-url=$ENDPOINT apigateway get-rest-apis 2>/dev/null); then
  echo -e "${GREEN}REST APIs found:${NC}"
  echo $REST_APIS | python3 -m json.tool 2>/dev/null || echo $REST_APIS
  REST_APIS_FOUND=true

  # Get first API ID
  REST_API_ID=$(echo $REST_APIS | python3 -c "import sys, json; print(json.load(sys.stdin)['items'][0]['id'] if len(json.load(sys.stdin)['items']) > 0 else 'none')" 2>/dev/null || echo "none")

  if [ "$REST_API_ID" != "none" ]; then
    echo -e "${GREEN}Using REST API ID: ${REST_API_ID}${NC}"

    # Get resources for the API
    echo -e "${YELLOW}Getting REST API resources...${NC}"
    RESOURCES=$(aws --endpoint-url=$ENDPOINT apigateway get-resources --rest-api-id $REST_API_ID 2>/dev/null || echo '{"items": []}')
    echo -e "${GREEN}API Resources:${NC}"
    echo $RESOURCES | python3 -m json.tool 2>/dev/null || echo $RESOURCES

    # List deployments
    echo -e "${YELLOW}Listing REST API deployments...${NC}"
    DEPLOYMENTS=$(aws --endpoint-url=$ENDPOINT apigateway get-deployments --rest-api-id $REST_API_ID 2>/dev/null || echo '{"items": []}')
    echo -e "${GREEN}API Deployments:${NC}"
    echo $DEPLOYMENTS | python3 -m json.tool 2>/dev/null || echo $DEPLOYMENTS

    # List stages
    echo -e "${YELLOW}Listing REST API stages...${NC}"
    STAGES=$(aws --endpoint-url=$ENDPOINT apigateway get-stages --rest-api-id $REST_API_ID 2>/dev/null || echo '{"item": []}')
    echo -e "${GREEN}API Stages:${NC}"
    echo $STAGES | python3 -m json.tool 2>/dev/null || echo $STAGES
  else
    echo -e "${RED}No REST API ID found${NC}"
  fi
else
  echo -e "${YELLOW}No REST APIs found${NC}"
fi

# Try to get API Gateway v2 (HTTP) APIs
HTTP_APIS_FOUND=false
if HTTP_APIS=$(aws --endpoint-url=$ENDPOINT apigatewayv2 get-apis 2>/dev/null); then
  echo -e "\n${GREEN}HTTP APIs found:${NC}"
  echo $HTTP_APIS | python3 -m json.tool 2>/dev/null || echo $HTTP_APIS
  HTTP_APIS_FOUND=true

  # Get first API ID
  HTTP_API_ID=$(echo $HTTP_APIS | python3 -c "import sys, json; print(json.load(sys.stdin)['Items'][0]['ApiId'] if len(json.load(sys.stdin)['Items']) > 0 else 'none')" 2>/dev/null || echo "none")

  if [ "$HTTP_API_ID" != "none" ]; then
    echo -e "${GREEN}Using HTTP API ID: ${HTTP_API_ID}${NC}"

    # Get routes for the API
    echo -e "${YELLOW}Getting HTTP API routes...${NC}"
    ROUTES=$(aws --endpoint-url=$ENDPOINT apigatewayv2 get-routes --api-id $HTTP_API_ID 2>/dev/null || echo '{"Items": []}')
    echo -e "${GREEN}API Routes:${NC}"
    echo $ROUTES | python3 -m json.tool 2>/dev/null || echo $ROUTES

    # Get integrations
    echo -e "${YELLOW}Getting HTTP API integrations...${NC}"
    INTEGRATIONS=$(aws --endpoint-url=$ENDPOINT apigatewayv2 get-integrations --api-id $HTTP_API_ID 2>/dev/null || echo '{"Items": []}')
    echo -e "${GREEN}API Integrations:${NC}"
    echo $INTEGRATIONS | python3 -m json.tool 2>/dev/null || echo $INTEGRATIONS

    # Get stages
    echo -e "${YELLOW}Getting HTTP API stages...${NC}"
    HTTP_STAGES=$(aws --endpoint-url=$ENDPOINT apigatewayv2 get-stages --api-id $HTTP_API_ID 2>/dev/null || echo '{"Items": []}')
    echo -e "${GREEN}API Stages:${NC}"
    echo $HTTP_STAGES | python3 -m json.tool 2>/dev/null || echo $HTTP_STAGES
  else
    echo -e "${RED}No HTTP API ID found${NC}"
  fi
else
  echo -e "${YELLOW}No HTTP APIs found${NC}"
fi

if [ "$REST_APIS_FOUND" = false ] && [ "$HTTP_APIS_FOUND" = false ]; then
  echo -e "${RED}Neither REST APIs nor HTTP APIs found in LocalStack${NC}"
fi

# Test direct access to the app container
echo -e "\n${BLUE}${BOLD}=== Testing Direct Container Access ===${NC}"
echo -e "${YELLOW}Testing health endpoint:${NC}"
curl -s http://localhost:5000/health | python3 -m json.tool 2>/dev/null || echo "Failed to access container health endpoint"

echo -e "\n${YELLOW}Testing hello endpoint:${NC}"
curl -s http://localhost:5000/api/hello | python3 -m json.tool 2>/dev/null || echo "Failed to access container hello endpoint"

# Check container logs for errors
echo -e "\n${BLUE}${BOLD}=== Container Logs (Last 10 lines) ===${NC}"
docker logs api-backend 2>&1 | tail -n 10

echo -e "\n${BLUE}${BOLD}=== LocalStack Logs (Last 10 error-related lines) ===${NC}"
docker logs localstack 2>&1 | grep -i "error\|exception" | tail -n 10

# VPC Link information (if available)
echo -e "\n${BLUE}${BOLD}=== VPC Link Information ===${NC}"
if [ "$HTTP_APIS_FOUND" = true ]; then
  VPC_LINKS=$(aws --endpoint-url=$ENDPOINT apigatewayv2 get-vpc-links 2>/dev/null || echo '{"Items": []}')
  echo -e "${GREEN}HTTP API VPC Links:${NC}"
  echo $VPC_LINKS | python3 -m json.tool 2>/dev/null || echo $VPC_LINKS
fi

# ECS information
echo -e "\n${BLUE}${BOLD}=== ECS Information ===${NC}"
CLUSTERS=$(aws --endpoint-url=$ENDPOINT ecs list-clusters 2>/dev/null || echo '{"clusterArns": []}')
echo -e "${GREEN}ECS Clusters:${NC}"
echo $CLUSTERS | python3 -m json.tool 2>/dev/null || echo $CLUSTERS

echo -e "\n${BLUE}${BOLD}=== Debug Information ===${NC}"
if [ "$REST_API_ID" != "none" ]; then
  echo -e "${YELLOW}REST API URL:${NC} $ENDPOINT/restapis/${REST_API_ID}/local/_user_request_/"
fi
if [ "$HTTP_API_ID" != "none" ]; then
  echo -e "${YELLOW}HTTP API URL:${NC} $ENDPOINT/apis/${HTTP_API_ID}/"
fi
echo -e "${YELLOW}Direct container URL:${NC} http://localhost:5000/"
echo -e "${YELLOW}LocalStack status:${NC} $ENDPOINT/_localstack/health"
