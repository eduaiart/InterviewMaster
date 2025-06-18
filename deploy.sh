#!/bin/bash

# TalentIQ Google Cloud Deployment Script
# Usage: ./deploy.sh [project-id]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Functions
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if project ID is provided
if [ -z "$1" ]; then
    print_error "Please provide a Google Cloud project ID"
    echo "Usage: ./deploy.sh [project-id]"
    exit 1
fi

PROJECT_ID=$1
SERVICE_NAME="talentiq"
REGION="us-central1"

print_status "Starting deployment for project: $PROJECT_ID"

# Set project
print_status "Setting Google Cloud project..."
gcloud config set project $PROJECT_ID

# Enable required APIs
print_status "Enabling required Google Cloud APIs..."
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable sql-component.googleapis.com
gcloud services enable sqladmin.googleapis.com

# Check if Cloud SQL instance exists
print_status "Checking for existing Cloud SQL instance..."
if ! gcloud sql instances describe talentiq-db &>/dev/null; then
    print_warning "Cloud SQL instance 'talentiq-db' not found. Please create it manually:"
    echo ""
    echo "gcloud sql instances create talentiq-db \\"
    echo "  --database-version=POSTGRES_15 \\"
    echo "  --cpu=2 \\"
    echo "  --memory=4GB \\"
    echo "  --storage-type=SSD \\"
    echo "  --storage-size=20GB \\"
    echo "  --region=$REGION \\"
    echo "  --backup-start-time=03:00"
    echo ""
    echo "gcloud sql databases create talentiq --instance=talentiq-db"
    echo ""
    echo "gcloud sql users create talentiq-user \\"
    echo "  --instance=talentiq-db \\"
    echo "  --password=your-secure-password"
    echo ""
    read -p "Press Enter after creating the database or 'n' to continue without database setup: " continue_deploy
    if [ "$continue_deploy" = "n" ]; then
        print_warning "Continuing without database verification..."
    fi
else
    print_status "Cloud SQL instance found: talentiq-db"
fi

# Build and push container image
print_status "Building container image..."
IMAGE_TAG="gcr.io/$PROJECT_ID/$SERVICE_NAME:$(date +%Y%m%d-%H%M%S)"
docker build -t $IMAGE_TAG .

print_status "Pushing image to Google Container Registry..."
docker push $IMAGE_TAG

# Deploy to Cloud Run
print_status "Deploying to Cloud Run..."

# Check if required environment variables are set
if [ -z "$DATABASE_URL" ]; then
    print_warning "DATABASE_URL not set. Please set your environment variables:"
    echo "export DATABASE_URL='postgresql://user:password@/dbname?host=/cloudsql/$PROJECT_ID:$REGION:talentiq-db'"
    echo "export SESSION_SECRET='your-session-secret'"
    echo "export OPENAI_API_KEY='your-openai-key'"
    echo "export GOOGLE_CLIENT_ID='your-google-client-id'"
    echo "export GOOGLE_CLIENT_SECRET='your-google-client-secret'"
    read -p "Continue deployment? (y/N): " continue_without_env
    if [ "$continue_without_env" != "y" ]; then
        print_error "Deployment cancelled. Please set environment variables and try again."
        exit 1
    fi
fi

# Deploy with Cloud Build (recommended)
if [ -f "cloudbuild.yaml" ]; then
    print_status "Using Cloud Build for deployment..."
    gcloud builds submit --config cloudbuild.yaml
else
    # Direct deployment
    print_status "Deploying directly to Cloud Run..."
    gcloud run deploy $SERVICE_NAME \
        --image $IMAGE_TAG \
        --platform managed \
        --region $REGION \
        --allow-unauthenticated \
        --port 8080 \
        --memory 2Gi \
        --cpu 2 \
        --min-instances 1 \
        --max-instances 100 \
        --timeout 300 \
        --concurrency 80 \
        --execution-environment gen2 \
        ${DATABASE_URL:+--set-env-vars DATABASE_URL="$DATABASE_URL"} \
        ${SESSION_SECRET:+--set-env-vars SESSION_SECRET="$SESSION_SECRET"} \
        ${OPENAI_API_KEY:+--set-env-vars OPENAI_API_KEY="$OPENAI_API_KEY"} \
        ${GOOGLE_CLIENT_ID:+--set-env-vars GOOGLE_CLIENT_ID="$GOOGLE_CLIENT_ID"} \
        ${GOOGLE_CLIENT_SECRET:+--set-env-vars GOOGLE_CLIENT_SECRET="$GOOGLE_CLIENT_SECRET"} \
        --set-env-vars FLASK_ENV=production \
        --set-env-vars PYTHONUNBUFFERED=1 \
        --add-cloudsql-instances $PROJECT_ID:$REGION:talentiq-db
fi

# Get service URL
print_status "Getting service URL..."
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --platform managed --region $REGION --format 'value(status.url)')

print_status "Deployment completed successfully!"
echo ""
echo -e "${GREEN}Service URL:${NC} $SERVICE_URL"
echo -e "${GREEN}Health Check:${NC} $SERVICE_URL/health"
echo ""
print_status "Testing health endpoint..."
if curl -f "$SERVICE_URL/health" &>/dev/null; then
    print_status "Health check passed! Service is running correctly."
else
    print_warning "Health check failed. Please check the logs:"
    echo "gcloud run services logs read $SERVICE_NAME --region $REGION"
fi

print_status "Deployment summary:"
echo "- Project ID: $PROJECT_ID"
echo "- Service Name: $SERVICE_NAME"
echo "- Region: $REGION"
echo "- Image: $IMAGE_TAG"
echo "- URL: $SERVICE_URL"
echo ""
print_status "To view logs: gcloud run services logs read $SERVICE_NAME --region $REGION"
print_status "To update deployment: gcloud builds submit --config cloudbuild.yaml"