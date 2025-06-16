# Cloud Run Environment Variables Setup

## Add These Variables to Your Cloud Run Service:

### 1. Go to Cloud Run Service
- Navigate to Cloud Run → Services → talentiq
- Click "Edit & deploy new revision"
- Find "Variables & Secrets" section

### 2. Add These Variables:

**DATABASE_URL**
```
postgresql://neondb_owner:npg_9cD8wkGdenNm@ep-bold-water-a522j4kr.us-east-2.aws.neon.tech/neondb?sslmode=require
```

**SESSION_SECRET**
```
talentiq_2025_secure_session_key_123456789abcdef
```

**OPENAI_API_KEY** (if you have it)
```
your_openai_api_key_here
```

### 3. Deploy the Revision
Click "Deploy" button and wait 2-3 minutes for the service to restart.

## Expected Result
Your TalentIQ service will start successfully and be accessible at:
`https://talentiq-platform-602384951874.us-central1.run.app/`

The application will show the TalentIQ landing page with proper branding, user registration, and all features functional.