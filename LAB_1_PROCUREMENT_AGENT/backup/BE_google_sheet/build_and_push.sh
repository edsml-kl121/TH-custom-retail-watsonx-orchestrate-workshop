#!/usr/bin/env bash
# Build and push Docker image to IBM Cloud Container Registry (ICR)

# Load environment variables from BE/.env file
set -a
source .env
set +a

# --- CONFIG ---
IMAGE_NAME="be-procurement-agent:latest"       # e.g. be-procurement-agent:latest
ICR_NAMESPACE="itz-watson-apps-ni5wa0hd-cr"   # your actual namespace
ICR_REGION="us.icr.io"                        # e.g. us.icr.io
FULL_IMAGE_NAME="$ICR_REGION/$ICR_NAMESPACE/$IMAGE_NAME"

# --- IBM Cloud Login ---
if [ -z "$IBM_CLOUD_API_KEY" ]; then
	echo "Error: IBM_CLOUD_API_KEY environment variable is not set."
	exit 1
fi
ibmcloud login --apikey "$IBM_CLOUD_API_KEY" -r us-south
ibmcloud cr region-set us-south
ibmcloud cr login

# Using Podman instead of Docker
sudo podman login us.icr.io -u iamapikey -p "$IBM_CLOUD_API_KEY"

# --- Build Docker image ---
echo "Building Docker image: $FULL_IMAGE_NAME"
sudo podman build -t "$FULL_IMAGE_NAME" /home/phupa/TH-custom-retail-watsonx-orchestrate-workshop/LAB_1_PROCUREMENT_AGENT/backup/BE_google_sheet

# --- Push Docker image ---
echo "Pushing Docker image to ICR: $FULL_IMAGE_NAME"
sudo podman push "$FULL_IMAGE_NAME"

echo "Done!"
