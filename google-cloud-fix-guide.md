# Fix TalentIQ Cloud Run Deployment

## Problem
Your current service is using a generic container instead of your TalentIQ application code from GitHub.

## Solution: Delete and Recreate Service

### Step 1: Delete Current Service
1. Go to Cloud Run → Services
2. Click on `talentiq` service
3. Click "Delete" button
4. Confirm deletion

### Step 2: Create New Service with GitHub Repository
1. Click "Create Service"
2. Select "Continuously deploy new revisions from a source repository"
3. Click "Set up with Cloud Build"

### Step 3: Repository Configuration
- Repository provider: GitHub
- Repository: eduaiart/talentiq-platform
- Branch: ^main$
- Build type: Dockerfile
- Source location: Dockerfile (in root directory)

### Step 4: Service Configuration
- Service name: talentiq
- Region: us-central1
- Allow unauthenticated invocations: YES
- Container port: 8080
- Memory: 1 GiB
- CPU: 1

### Step 5: Environment Variables (After Service Created)
Add these variables:
```
DATABASE_URL=postgresql://postgres:YOUR_DB_PASSWORD@YOUR_DB_IP:5432/postgres
OPENAI_API_KEY=your_openai_key
SESSION_SECRET=random_32_character_string
```

### Step 6: Get Database Connection Details
1. Go to SQL → talentiq-db → Overview
2. Copy Public IP address
3. Use password you created during database setup

## Expected Result
- Service will build using your Dockerfile
- TalentIQ application will be deployed
- URL will show your actual application, not "Service Unavailable"