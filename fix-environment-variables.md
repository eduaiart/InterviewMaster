# Fix TalentIQ Environment Variables

## Current Issue
Service fails to start with error: `RuntimeError: Either 'SQLALCHEMY_DATABASE_URI' or 'SQLALCHEMY_BINDS' must be set.`

## Solution Steps

### 1. Get Database Connection Details
1. Go to **SQL** in Google Cloud Console
2. Click on **talentiq-db**
3. Go to **Overview** tab
4. Copy the **Public IP address** (e.g., 34.69.xxx.xxx)
5. Note your database password from setup

### 2. Add Environment Variables
1. Go to **Cloud Run** → **Services** → **talentiq**
2. Click **"Edit & deploy new revision"**
3. Scroll to **"Variables & Secrets"** section
4. Click **"Add Variable"** for each:

**Required Variables:**
```
DATABASE_URL = postgresql://postgres:YOUR_PASSWORD@YOUR_DB_IP:5432/postgres
SESSION_SECRET = any_random_32_character_string_here
OPENAI_API_KEY = your_openai_api_key_if_available
```

### 3. Example Values
If your database IP is `34.69.123.456` and password is `mypassword`:
```
DATABASE_URL = postgresql://postgres:mypassword@34.69.123.456:5432/postgres
SESSION_SECRET = abcd1234efgh5678ijkl9012mnop3456
```

### 4. Deploy
1. Click **"Deploy"** button
2. Wait 2-3 minutes for deployment
3. Service will restart with proper database connection

## Expected Result
- Service will start successfully
- TalentIQ application will be accessible
- Database connection established
- All features functional