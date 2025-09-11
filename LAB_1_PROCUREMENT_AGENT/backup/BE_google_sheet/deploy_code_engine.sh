#!/usr/bin/env bash
# Deploy or update the Code Engine application with the latest image

# Load environment variables from .env file
set -a
source .env
set +a

# --- CONFIG ---
APP_NAME="be-procurement-agent"
IMAGE_PATH="us.icr.io/itz-watson-apps-ni5wa0hd-cr/be-procurement-agent:latest"
REGISTRY_SECRET="ibmcloud"
PORT=8000
CPU=2
MEMORY=8G
ENV_SECRET_NAME="$APP_NAME"

# --- IBM Cloud CLI Project/Resource Group Setup ---
if [ -z "$IBM_CLOUD_RG" ]; then
  echo "Error: IBM_CLOUD_RG environment variable is not set."
  exit 1
fi
if [ -z "$IBM_CLOUD_PROJECT" ]; then
  echo "Error: IBM_CLOUD_PROJECT environment variable is not set."
  exit 1
fi
ibmcloud target -g "$IBM_CLOUD_RG"
ibmcloud ce project select --id "$IBM_CLOUD_PROJECT"

# --- Deploy or Update Application ---
application_exists=$(ibmcloud ce application list --output json | jq -r ".items[] | select(.metadata.name == \"${APP_NAME}\") | .metadata.name")

if [ "$application_exists" == "$APP_NAME" ]; then
  echo "Updating existing application..."
  ibmcloud ce application update \
    --name $APP_NAME \
    --cpu $CPU \
    --memory $MEMORY \
    --min-scale 1 \
    --env-from-secret $ENV_SECRET_NAME \
    --image $IMAGE_PATH \
    --port $PORT \
    --registry-secret $REGISTRY_SECRET \
    --wait-timeout 12000 \
    --timeout 600 \
    --probe-ready type=tcp \
    --probe-ready port=$PORT
else
  echo "Creating new application..."
  ibmcloud ce application create \
    --name $APP_NAME \
    --cpu $CPU \
    --memory $MEMORY \
    --min-scale 1 \
    --env-from-secret $ENV_SECRET_NAME \
    --image $IMAGE_PATH \
    --port $PORT \
    --registry-secret $REGISTRY_SECRET \
    --wait-timeout 12000 \
    --timeout 600 \
    --probe-ready type=tcp \
    --probe-ready port=$PORT
fi

echo "Deployment complete!"
