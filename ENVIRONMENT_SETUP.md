# Environment Variables Setup for Google Cloud Run

Based on the error logs, here are the exact environment variables you need to configure:

## Step 1: Set Required Variables in Google Cloud Console

Go to Google Cloud Console → Cloud Run → Select your service → Edit & Deploy New Revision → Variables & Secrets

### Essential Variables:
```
DATABASE_URL=postgresql://talentiq-user:YOUR_PASSWORD@/talentiq?host=/cloudsql/PROJECT_ID:us-central1:talentiq-db
SESSION_SECRET=your-32-character-random-string
FLASK_ENV=production
OPENAI_API_KEY=sk-your-openai-api-key
```

### Google OAuth (for Calendar):
```
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
```

## Step 2: Generate Required Values

### SESSION_SECRET
Generate a secure random string:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### DATABASE_URL Format
Replace these placeholders:
- `YOUR_PASSWORD`: Database user password you set
- `PROJECT_ID`: Your Google Cloud project ID
- Instance should be: `PROJECT_ID:us-central1:talentiq-db`

### OPENAI_API_KEY
Get from: https://platform.openai.com/api-keys

### Google OAuth Credentials
1. Go to Google Cloud Console → APIs & Services → Credentials
2. Create OAuth 2.0 Client ID
3. Application type: Web application
4. Authorized redirect URIs: `https://your-app-url/calendar/callback`

## Step 3: Deploy with Environment Variables

```bash
gcloud run deploy talentiq \
  --image gcr.io/PROJECT_ID/talentiq:latest \
  --set-env-vars DATABASE_URL="postgresql://talentiq-user:PASSWORD@/talentiq?host=/cloudsql/PROJECT_ID:us-central1:talentiq-db" \
  --set-env-vars SESSION_SECRET="your-generated-secret" \
  --set-env-vars FLASK_ENV="production" \
  --set-env-vars OPENAI_API_KEY="sk-your-key" \
  --set-env-vars GOOGLE_CLIENT_ID="your-client-id" \
  --set-env-vars GOOGLE_CLIENT_SECRET="your-client-secret" \
  --region us-central1 \
  --allow-unauthenticated \
  --add-cloudsql-instances PROJECT_ID:us-central1:talentiq-db
```

## Step 4: Verify Deployment

After setting variables, check:
1. Health endpoint: `https://your-app-url/health`
2. Application logs for any remaining errors
3. Database connectivity

The errors in your logs are likely due to missing environment variables, particularly DATABASE_URL and SESSION_SECRET.