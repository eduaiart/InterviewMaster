#!/bin/bash

# Fix Google Cloud Run deployment with proper environment variables
echo "Setting environment variables for interviewmaster service..."

gcloud run services update interviewmaster \
  --region us-central1 \
  --set-env-vars "DATABASE_URL=postgresql://talentiq-user:NKbk@1963@/talentiq?host=/cloudsql/talentiq-platform:us-central1:talentiq-db" \
  --set-env-vars "SESSION_SECRET=talentiq-secure-session-key-2024-production" \
  --set-env-vars "FLASK_ENV=production" \
  --set-env-vars "PYTHONUNBUFFERED=1" \
  --set-cloudsql-instances "talentiq-platform:us-central1:talentiq-db" \
  --port 8080 \
  --memory 1Gi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 10 \
  --timeout 300

echo "Deployment configuration updated. Service should be available at:"
echo "https://interviewmaster-602384951874.us-central1.run.app"