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
echo -e "${BLUE}${BOLD}=== API Gateway v2 Configuration Fix ===${NC}"

# Configure AWS CLI for LocalStack
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_DEFAULT_REGION=eu-west-2
ENDPOINT="http://localhost:4566"

# Check if localstack is running
if ! curl -s $ENDPOINT/_localstack/health > /dev/null; then
  echo -e "${RED}LocalStack is not running. Please start it first.${NC}"
  exit 1
fi

echo -e "${YELLOW}Detecting API Gateway resources...${NC}"

# Try to get HTTP API Gateway (v2) APIs first
HTTP_API_ID=""
if API_LIST=$(aws --endpoint-url=$ENDPOINT apigatewayv2 get-apis 2>/dev/null); then
  HTTP_API_ID=$(echo "$API_LIST" | python3 -c "import sys, json; print(json.load(sys.stdin)['Items'][0]['ApiId'] if 'Items' in json.load(sys.stdin) and len(json.load(sys.stdin)['Items']) > 0 else '')" 2>/dev/null || echo "")

  if [ -n "$HTTP_API_ID" ]; then
    echo -e "${GREEN}Found HTTP API Gateway: $HTTP_API_ID${NC}"
  else
    echo -e "${YELLOW}No HTTP API Gateway found, will attempt to find REST API Gateway${NC}"
  fi
fi

# If no HTTP API (v2) found, try to get REST API Gateway (v1)
REST_API_ID=""
if [ -z "$HTTP_API_ID" ]; then
  if API_LIST=$(aws --endpoint-url=$ENDPOINT apigateway get-rest-apis 2>/dev/null); then
    REST_API_ID=$(echo "$API_LIST" | python3 -c "import sys, json; print(json.load(sys.stdin)['items'][0]['id'] if 'items' in json.load(sys.stdin) and len(json.load(sys.stdin)['items']) > 0 else '')" 2>/dev/null || echo "")

    if [ -n "$REST_API_ID" ]; then
      echo -e "${GREEN}Found REST API Gateway: $REST_API_ID${NC}"
    else
      echo -e "${RED}No API Gateway found at all${NC}"
      exit 1
    fi
  fi
fi

# Fix HTTP API Gateway (v2) if found
if [ -n "$HTTP_API_ID" ]; then
  echo -e "${YELLOW}Fixing HTTP API Gateway configuration...${NC}"

  # Get existing stages
  STAGES=$(aws --endpoint-url=$ENDPOINT apigatewayv2 get-stages --api-id $HTTP_API_ID 2>/dev/null || echo '{"Items": []}')
  STAGE_EXISTS=$(echo "$STAGES" | python3 -c "import sys, json; print('true' if any(stage['StageName'] == 'local' for stage in json.load(sys.stdin).get('Items', []) if 'StageName' in stage) else 'false')" 2>/dev/null || echo "false")

  # Create 'local' stage if it doesn't exist
  if [ "$STAGE_EXISTS" = "false" ]; then
    echo -e "${YELLOW}Creating 'local' stage...${NC}"
    aws --endpoint-url=$ENDPOINT apigatewayv2 create-stage \
      --api-id $HTTP_API_ID \
      --stage-name local \
      --auto-deploy \
      2>/dev/null || echo -e "${RED}Could not create stage${NC}"
  else
    echo -e "${GREEN}Stage 'local' already exists${NC}"
  fi

  # Check for routes
  ROUTES=$(aws --endpoint-url=$ENDPOINT apigatewayv2 get-routes --api-id $HTTP_API_ID 2>/dev/null || echo '{"Items": []}')
  ROUTE_COUNT=$(echo "$ROUTES" | python3 -c "import sys, json; print(len(json.load(sys.stdin).get('Items', [])))" 2>/dev/null || echo "0")

  if [ "$ROUTE_COUNT" -eq 0 ]; then
    echo -e "${YELLOW}No routes found. Creating default routes...${NC}"

    # Get VPC Link
    VPC_LINKS=$(aws --endpoint-url=$ENDPOINT apigatewayv2 get-vpc-links 2>/dev/null || echo '{"Items": []}')
    VPC_LINK_ID=$(echo "$VPC_LINKS" | python3 -c "import sys, json; print(json.load(sys.stdin)['Items'][0]['VpcLinkId'] if 'Items' in json.load(sys.stdin) and len(json.load(sys.stdin)['Items']) > 0 else '')" 2>/dev/null || echo "")

    if [ -n "$VPC_LINK_ID" ]; then
      echo -e "${GREEN}Found VPC Link: $VPC_LINK_ID${NC}"

      # Create an integration to the ALB
      echo -e "${YELLOW}Creating integration...${NC}"
      INTEGRATION_ID=$(aws --endpoint-url=$ENDPOINT apigatewayv2 create-integration \
        --api-id $HTTP_API_ID \
        --integration-type HTTP_PROXY \
        --integration-method ANY \
        --integration-uri http://localhost:5000 \
        --payload-format-version 1.0 \
        --connection-type VPC_LINK \
        --connection-id $VPC_LINK_ID \
        --timeout-in-millis 30000 \
        --query 'IntegrationId' --output text \
        2>/dev/null || echo "")

      if [ -n "$INTEGRATION_ID" ]; then
        echo -e "${GREEN}Created integration: $INTEGRATION_ID${NC}"

        # Create route for ANY /{proxy+}
        echo -e "${YELLOW}Creating proxy route...${NC}"
        aws --endpoint-url=$ENDPOINT apigatewayv2 create-route \
          --api-id $HTTP_API_ID \
          --route-key 'ANY /{proxy+}' \
          --target "integrations/$INTEGRATION_ID" \
          2>/dev/null || echo -e "${RED}Could not create proxy route${NC}"

        # Create route for GET /health
        echo -e "${YELLOW}Creating health route...${NC}"
        aws --endpoint-url=$ENDPOINT apigatewayv2 create-route \
          --api-id $HTTP_API_ID \
          --route-key 'GET /health' \
          --target "integrations/$INTEGRATION_ID" \
          2>/dev/null || echo -e "${RED}Could not create health route${NC}"

        # Create routes for API endpoints
        echo -e "${YELLOW}Creating API routes...${NC}"
        aws --endpoint-url=$ENDPOINT apigatewayv2 create-route \
          --api-id $HTTP_API_ID \
          --route-key 'GET /api/hello' \
          --target "integrations/$INTEGRATION_ID" \
          2>/dev/null || echo -e "${RED}Could not create hello route${NC}"

        aws --endpoint-url=$ENDPOINT apigatewayv2 create-route \
          --api-id $HTTP_API_ID \
          --route-key 'POST /api/data' \
          --target "integrations/$INTEGRATION_ID" \
          2>/dev/null || echo -e "${RED}Could not create data route${NC}"

        echo -e "${GREEN}Created all routes successfully${NC}"
      else
        echo -e "${RED}Could not create integration${NC}"
      fi
    else
      echo -e "${RED}No VPC Link found${NC}"
    fi
  else
    echo -e "${GREEN}Found $ROUTE_COUNT routes, no need to create more${NC}"
  fi

  # Deploy API (this may not be necessary, but doesn't hurt)
  echo -e "${YELLOW}Deploying API...${NC}"
  aws --endpoint-url=$ENDPOINT apigatewayv2 create-deployment \
    --api-id $HTTP_API_ID \
    --stage-name local \
    2>/dev/null || echo -e "${YELLOW}Deployment not created or not needed${NC}"

  echo -e "${GREEN}HTTP API Gateway fix complete!${NC}"
  echo -e "${GREEN}API URL: $ENDPOINT/apis/$HTTP_API_ID${NC}"
# Fix REST API Gateway (v1) if found and no HTTP API
elif [ -n "$REST_API_ID" ]; then
  echo -e "${YELLOW}Fixing REST API Gateway configuration...${NC}"

  # Check if we need to create a stage
  STAGES=$(aws --endpoint-url=$ENDPOINT apigateway get-stages --rest-api-id $REST_API_ID --query "item[*].stageName" --output text 2>/dev/null || echo "")

  # Create local stage if it doesn't exist
  if [[ ! $STAGES =~ "local" ]]; then
    echo -e "${YELLOW}Creating 'local' stage...${NC}"
    aws --endpoint-url=$ENDPOINT apigateway create-deployment \
      --rest-api-id $REST_API_ID \
      --stage-name local \
      --description "LocalStack deployment" \
      2>/dev/null || echo -e "${RED}Could not create deployment${NC}"
  else
    echo -e "${GREEN}Stage 'local' already exists${NC}"
  fi

  # Get resources for the API
  echo -e "${YELLOW}Getting API resources...${NC}"
  RESOURCES=$(aws --endpoint-url=$ENDPOINT apigateway get-resources --rest-api-id $REST_API_ID 2>/dev/null || echo '{"items": []}')

  # Get the root resource ID
  ROOT_ID=$(echo $RESOURCES | python3 -c "import sys, json; print([r['id'] for r in json.load(sys.stdin)['items'] if r.get('path', '') == '/'][0])" 2>/dev/null || echo "")

  if [ -n "$ROOT_ID" ]; then
    echo -e "${GREEN}Found root resource: $ROOT_ID${NC}"

    # Create a health resource if it doesn't exist
    HEALTH_ID=$(echo $RESOURCES | python3 -c "import sys, json; print([r['id'] for r in json.load(sys.stdin)['items'] if r.get('path', '') == '/health'][0] if any(r.get('path', '') == '/health' for r in json.load(sys.stdin)['items']) else '')" 2>/dev/null || echo "")

    if [ -z "$HEALTH_ID" ]; then
      echo -e "${YELLOW}Creating /health resource...${NC}"
      HEALTH_RESULT=$(aws --endpoint-url=$ENDPOINT apigateway create-resource \
        --rest-api-id $REST_API_ID \
        --parent-id $ROOT_ID \
        --path-part health \
        2>/dev/null || echo "")

      HEALTH_ID=$(echo $HEALTH_RESULT | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])" 2>/dev/null || echo "")

      if [ -n "$HEALTH_ID" ]; then
        echo -e "${GREEN}Created health resource: $HEALTH_ID${NC}"

        # Add GET method to health
        aws --endpoint-url=$ENDPOINT apigateway put-method \
          --rest-api-id $REST_API_ID \
          --resource-id $HEALTH_ID \
          --http-method GET \
          --authorization-type NONE \
          2>/dev/null || echo -e "${RED}Could not create GET method${NC}"

        # Add integration to health
        aws --endpoint-url=$ENDPOINT apigateway put-integration \
          --rest-api-id $REST_API_ID \
          --resource-id $HEALTH_ID \
          --http-method GET \
          --type HTTP_PROXY \
          --integration-http-method GET \
          --uri http://localhost:5000/health \
          2>/dev/null || echo -e "${RED}Could not create integration${NC}"
      fi
    else
      echo -e "${GREEN}Health resource already exists${NC}"
    fi

    # Create an API resource if it doesn't exist
    API_ID=$(echo $RESOURCES | python3 -c "import sys, json; print([r['id'] for r in json.load(sys.stdin)['items'] if r.get('path', '') == '/api'][0] if any(r.get('path', '') == '/api' for r in json.load(sys.stdin)['items']) else '')" 2>/dev/null || echo "")

    if [ -z "$API_ID" ]; then
      echo -e "${YELLOW}Creating /api resource...${NC}"
      API_RESULT=$(aws --endpoint-url=$ENDPOINT apigateway create-resource \
        --rest-api-id $REST_API_ID \
        --parent-id $ROOT_ID \
        --path-part api \
        2>/dev/null || echo "")

      API_ID=$(echo $API_RESULT | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])" 2>/dev/null || echo "")

      if [ -n "$API_ID" ]; then
        echo -e "${GREEN}Created API resource: $API_ID${NC}"

        # Create /api/hello resource
        echo -e "${YELLOW}Creating /api/hello resource...${NC}"
        HELLO_RESULT=$(aws --endpoint-url=$ENDPOINT apigateway create-resource \
          --rest-api-id $REST_API_ID \
          --parent-id $API_ID \
          --path-part hello \
          2>/dev/null || echo "")

        HELLO_ID=$(echo $HELLO_RESULT | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])" 2>/dev/null || echo "")

        if [ -n "$HELLO_ID" ]; then
          echo -e "${GREEN}Created hello resource: $HELLO_ID${NC}"

          # Add GET method to hello
          aws --endpoint-url=$ENDPOINT apigateway put-method \
            --rest-api-id $REST_API_ID \
            --resource-id $HELLO_ID \
            --http-method GET \
            --authorization-type NONE \
            2>/dev/null || echo -e "${RED}Could not create GET method${NC}"

          # Add integration to hello
          aws --endpoint-url=$ENDPOINT apigateway put-integration \
            --rest-api-id $REST_API_ID \
            --resource-id $HELLO_ID \
            --http-method GET \
            --type HTTP_PROXY \
            --integration-http-method GET \
            --uri http://localhost:5000/api/hello \
            2>/dev/null || echo -e "${RED}Could not create integration${NC}"
        fi

        # Create /api/data resource
        echo -e "${YELLOW}Creating /api/data resource...${NC}"
        DATA_RESULT=$(aws --endpoint-url=$ENDPOINT apigateway create-resource \
          --rest-api-id $REST_API_ID \
          --parent-id $API_ID \
          --path-part data \
          2>/dev/null || echo "")

        DATA_ID=$(echo $DATA_RESULT | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])" 2>/dev/null || echo "")

        if [ -n "$DATA_ID" ]; then
          echo -e "${GREEN}Created data resource: $DATA_ID${NC}"

          # Add POST method to data
          aws --endpoint-url=$ENDPOINT apigateway put-method \
            --rest-api-id $REST_API_ID \
            --resource-id $DATA_ID \
            --http-method POST \
            --authorization-type NONE \
            2>/dev/null || echo -e "${RED}Could not create POST method${NC}"

          # Add integration to data
          aws --endpoint-url=$ENDPOINT apigateway put-integration \
            --rest-api-id $REST_API_ID \
            --resource-id $DATA_ID \
            --http-method POST \
            --type HTTP_PROXY \
            --integration-http-method POST \
            --uri http://localhost:5000/api/data \
            2>/dev/null || echo -e "${RED}Could not create integration${NC}"
        fi
      fi
    else
      echo -e "${GREEN}API resource already exists${NC}"
    fi
  else
    echo -e "${RED}Could not find root resource for API${NC}"
  fi

  # Create a new deployment
  echo -e "${YELLOW}Creating new deployment...${NC}"
  aws --endpoint-url=$ENDPOINT apigateway create-deployment \
    --rest-api-id $REST_API_ID \
    --stage-name local \
    --description "Fixed deployment" \
    2>/dev/null || echo -e "${RED}Could not create deployment${NC}"

  echo -e "${GREEN}REST API Gateway fix complete!${NC}"
  echo -e "${GREEN}API URL: $ENDPOINT/restapis/$REST_API_ID/local/_user_request_${NC}"
else
  echo -e "${RED}No API Gateway found to fix${NC}"
  exit 1
fi

echo -e "\n${GREEN}${BOLD}API Gateway Configuration Fix Complete!${NC}"
echo -e "${YELLOW}Now you should be able to access the API endpoints.${NC}"
echo -e "Try running the tests with: ${BOLD}../localstack/run.sh${NC}"
