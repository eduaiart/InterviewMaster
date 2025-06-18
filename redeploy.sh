#!/bin/bash

# Quick redeploy script for Google Cloud Run
# Fixes the Python import errors in your current deployment

PROJECT_ID="talentiq-platform"
SERVICE_NAME="talentiq-platform1"
REGION="us-central1"

echo "Redeploying TalentIQ with fixes..."

# Build and deploy using Cloud Build
gcloud builds submit --config cloudbuild.yaml --project=$PROJECT_ID

echo "Deployment complete. Service URL:"
gcloud run services describe $SERVICE_NAME --region=$REGION --format='value(status.url)'

echo "Testing health endpoint..."
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region=$REGION --format='value(status.url)')
curl -f "$SERVICE_URL/health" || echo "Health check failed - check environment variables"

echo "Check logs with: gcloud run services logs read $SERVICE_NAME --region=$REGION"