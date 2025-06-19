# Fix Service Unavailable Issue

Your deployment succeeded, but the service needs environment variables to start properly.

## Current Status
- ✅ Build: Successful (f92b1ccd-4419-432c-a13d-787edbcf6d7e)
- ✅ Deploy: Completed to `interviewmaster` service
- ❌ Service: Unavailable (missing environment variables)

## Fix Steps

### 1. Set Environment Variables in Google Cloud Console

Go to: [Cloud Run Console](https://console.cloud.google.com/run) → Select `interviewmaster` → Edit & Deploy New Revision → Variables & Secrets

Add these variables:
```
DATABASE_URL=postgresql://talentiq-user:NKbk@1963@/talentiq?host=/cloudsql/talentiq-platform:us-central1:talentiq-db
SESSION_SECRET=talentiq-secure-session-key-2024-production
FLASK_ENV=production
PYTHONUNBUFFERED=1
```

### 2. Configure Cloud SQL Connection

In the same edit screen:
- Go to "Connections" tab
- Add Cloud SQL connection: `talentiq-platform:us-central1:talentiq-db`

### 3. Verify Service Settings

Ensure these settings:
- Port: 8080
- Memory: 1 GiB
- CPU: 1
- Min instances: 0
- Max instances: 10
- Request timeout: 300 seconds

## Service URL
After setting environment variables, your service will be available at:
https://interviewmaster-602384951874.us-central1.run.app

## Alternative: Command Line Fix

If you have gcloud CLI configured:
```bash
gcloud run services update interviewmaster \
  --region us-central1 \
  --set-env-vars "DATABASE_URL=postgresql://talentiq-user:NKbk@1963@/talentiq?host=/cloudsql/talentiq-platform:us-central1:talentiq-db,SESSION_SECRET=talentiq-secure-session-key-2024-production,FLASK_ENV=production,PYTHONUNBUFFERED=1" \
  --set-cloudsql-instances "talentiq-platform:us-central1:talentiq-db"
```