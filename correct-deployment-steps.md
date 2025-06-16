# Correct TalentIQ Deployment Steps

## Delete Current Service and Start Fresh

### 1. Delete Current Service
- Go to Cloud Run → Services
- Click the 3 dots next to `talentiq` → Delete
- Confirm deletion

### 2. Create New Service (Repository-Connected)
- Click "Create Service"
- Select "Continuously deploy new revisions from a source repository"
- Click "Set up with Cloud Build"

### 3. Repository Settings
```
Repository provider: GitHub
Repository: eduaiart/talentiq-platform  
Branch: ^main$
Build type: Dockerfile
```

### 4. Service Settings
```
Service name: talentiq
Region: us-central1 (same as database)
Authentication: Allow unauthenticated invocations
Container port: 8080
Memory: 1 GiB
CPU: 1
```

### 5. After Deployment - Add Environment Variables
Click service → Edit & deploy new revision → Variables & Secrets tab:

```
DATABASE_URL = postgresql://postgres:YOUR_PASSWORD@YOUR_DB_IP:5432/postgres
OPENAI_API_KEY = your_openai_api_key
SESSION_SECRET = any_random_32_character_string
```

### 6. Get Database IP
- Go to SQL → talentiq-db → Overview
- Copy the Public IP address (34.69.xxx.xxx)
- Use this in the DATABASE_URL above

## Why This Will Work
- Uses your actual TalentIQ code from GitHub
- Builds with your custom Dockerfile
- Connects to your PostgreSQL database
- Enables AI features with OpenAI integration

Your TalentIQ platform will then be fully functional at the generated Cloud Run URL.