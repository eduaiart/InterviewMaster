# TalentIQ - Google Cloud Deployment Guide

## Files to Upload to GitHub

### Core Application Files:
- `main.py` - Entry point
- `app.py` - Flask configuration
- `routes.py` - All routes and handlers
- `models.py` - Database models
- `ai_service.py` - OpenAI integration
- `calendar_service.py` - Google Calendar integration

### Templates Folder (complete):
- `templates/landing.html` - Professional landing page
- `templates/base.html` - Base template with TalentIQ branding
- `templates/login.html` - Login page
- `templates/register.html` - Registration page
- `templates/dashboard.html` - User dashboard
- `templates/interview_builder.html` - Interview creation
- `templates/interview_interface.html` - Interview interface
- `templates/chat_interview.html` - Chat interview
- `templates/schedule_dashboard.html` - Scheduling system
- All other HTML templates in templates folder

### Static Files Folder (complete):
- `static/logo.svg` - TalentIQ logo
- `static/css/` - All CSS files
- `static/js/` - All JavaScript files

### Configuration Files:
- `pyproject.toml` - Python dependencies
- `Dockerfile` - Google Cloud deployment
- `cloudbuild.yaml` - Automated deployment
- `app.yaml` - App Engine config
- `README.md` - Documentation
- `.gitignore` - Git ignore rules

## Google Cloud Setup Steps:

### 1. Create Google Cloud Project
```bash
# Install Google Cloud CLI first
# Then create project
gcloud projects create talentiq-platform-123
gcloud config set project talentiq-platform-123
```

### 2. Enable Required APIs
```bash
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable sqladmin.googleapis.com
```

### 3. Create Cloud SQL Database
```bash
gcloud sql instances create talentiq-db \
  --database-version=POSTGRES_14 \
  --tier=db-f1-micro \
  --region=us-central1

gcloud sql databases create talentiq --instance=talentiq-db
gcloud sql users create talentiq-user --instance=talentiq-db --password=YOUR_PASSWORD
```

### 4. Deploy to Cloud Run
```bash
# From your project directory with all files
gcloud run deploy talentiq \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --port 8080 \
  --memory 1Gi \
  --cpu 1
```

### 5. Set Environment Variables
```bash
gcloud run services update talentiq \
  --region us-central1 \
  --set-env-vars="DATABASE_URL=postgresql://talentiq-user:YOUR_PASSWORD@/talentiq?host=/cloudsql/PROJECT_ID:us-central1:talentiq-db,OPENAI_API_KEY=your_openai_key,SESSION_SECRET=your_session_secret"
```

### 6. Configure Custom Domain
```bash
gcloud run domain-mappings create \
  --service talentiq \
  --domain talentiq.eduaiart.com \
  --region us-central1
```

## Environment Variables Needed:
- `DATABASE_URL` - PostgreSQL connection string
- `OPENAI_API_KEY` - Your OpenAI API key
- `SESSION_SECRET` - Random secret key for sessions
- `SENDGRID_API_KEY` - Email service (optional)
- `TWILIO_ACCOUNT_SID` - SMS service (optional)
- `TWILIO_AUTH_TOKEN` - SMS service (optional)
- `TWILIO_PHONE_NUMBER` - SMS service (optional)
- `GOOGLE_CLIENT_ID` - Calendar integration (optional)
- `GOOGLE_CLIENT_SECRET` - Calendar integration (optional)

## Estimated Monthly Costs:
- Cloud Run: $5-15 (pay per use)
- Cloud SQL: $7-25 (small instance)
- Storage: $1-5
- **Total: $13-45/month**

## Alternative: Direct Upload Method
1. Download/copy all project files locally
2. Create GitHub repository manually
3. Upload files via GitHub web interface
4. Connect repository to Google Cloud Build for automatic deployment