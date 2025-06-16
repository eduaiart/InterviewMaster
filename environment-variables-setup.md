# Environment Variables for TalentIQ Cloud Run

## Current Issue: Service Unavailable
Your TalentIQ service is failing because it cannot connect to the database. The error shows:
`RuntimeError: Either 'SQLALCHEMY_DATABASE_URI' or 'SQLALCHEMY_BINDS' must be set.`

## Fix: Add Environment Variables

### Step 1: Get Database Connection String
Your database is running at: `talentiq-db` instance
You need the Public IP address from: SQL → talentiq-db → Overview

### Step 2: Add Variables to Cloud Run
1. Go to Cloud Run → Services → talentiq
2. Click "Edit & deploy new revision"
3. Scroll to "Variables & Secrets" section
4. Add these variables:

**DATABASE_URL**
Format: `postgresql://postgres:YOUR_PASSWORD@PUBLIC_IP:5432/postgres`
Example: `postgresql://postgres:mypassword123@34.69.123.456:5432/postgres`

**SESSION_SECRET**
Any secure random string (32+ characters)
Example: `talentiq2025secretkey123456789abcdef`

**OPENAI_API_KEY** (optional for now)
Your OpenAI API key if you have one

### Step 3: Deploy
Click "Deploy" and wait 2-3 minutes

### Expected Result
- Service will start successfully
- URL will show TalentIQ application
- Database tables will be created automatically
- Application will be fully functional

## Database Connection Details Needed
- Public IP of your talentiq-db instance
- Password you set during database creation