# TalentIQ - Google Cloud Deployment Guide

## Prerequisites

1. **Google Cloud Account**: Ensure you have a Google Cloud account with billing enabled
2. **Google Cloud CLI**: Install and configure the Google Cloud CLI
3. **Docker**: Install Docker for local testing (optional)
4. **PostgreSQL Database**: Set up Cloud SQL PostgreSQL instance

## Deployment Options

### Option 1: Google Cloud Run (Recommended)

#### Step 1: Setup Google Cloud Project
```bash
# Set your project ID
export PROJECT_ID="your-project-id"
gcloud config set project $PROJECT_ID

# Enable required APIs
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable sql-component.googleapis.com
gcloud services enable sqladmin.googleapis.com
```

#### Step 2: Create PostgreSQL Database
```bash
# Create Cloud SQL PostgreSQL instance
gcloud sql instances create talentiq-db \
  --database-version=POSTGRES_15 \
  --cpu=2 \
  --memory=4GB \
  --storage-type=SSD \
  --storage-size=20GB \
  --region=us-central1 \
  --backup-start-time=03:00 \
  --enable-bin-log \
  --authorized-networks=0.0.0.0/0

# Create database
gcloud sql databases create talentiq --instance=talentiq-db

# Create database user
gcloud sql users create talentiq-user \
  --instance=talentiq-db \
  --password=your-secure-password
```

#### Step 3: Set Environment Variables
```bash
# Get database connection string
export DATABASE_URL="postgresql://talentiq-user:your-secure-password@/talentiq?host=/cloudsql/PROJECT_ID:us-central1:talentiq-db"

# Set other required environment variables
export SESSION_SECRET="your-session-secret-key"
export OPENAI_API_KEY="your-openai-api-key"
export GOOGLE_CLIENT_ID="your-google-oauth-client-id"
export GOOGLE_CLIENT_SECRET="your-google-oauth-client-secret"
```

#### Step 4: Deploy to Cloud Run
```bash
# Build and deploy using Cloud Build
gcloud builds submit --config cloudbuild.yaml

# Or deploy directly
gcloud run deploy talentiq \
  --image gcr.io/$PROJECT_ID/talentiq:latest \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --port 8080 \
  --memory 2Gi \
  --cpu 2 \
  --min-instances 1 \
  --max-instances 100 \
  --set-env-vars DATABASE_URL="$DATABASE_URL" \
  --set-env-vars SESSION_SECRET="$SESSION_SECRET" \
  --set-env-vars OPENAI_API_KEY="$OPENAI_API_KEY" \
  --set-env-vars GOOGLE_CLIENT_ID="$GOOGLE_CLIENT_ID" \
  --set-env-vars GOOGLE_CLIENT_SECRET="$GOOGLE_CLIENT_SECRET" \
  --set-env-vars FLASK_ENV=production \
  --add-cloudsql-instances $PROJECT_ID:us-central1:talentiq-db
```

### Option 2: Google App Engine

#### Deploy to App Engine
```bash
# Deploy using app.yaml configuration
gcloud app deploy app.yaml

# Set environment variables
gcloud app deploy app.yaml --env-vars-file env_variables.yaml
```

#### Create env_variables.yaml
```yaml
env_variables:
  DATABASE_URL: "postgresql://talentiq-user:password@/talentiq?host=/cloudsql/PROJECT_ID:us-central1:talentiq-db"
  SESSION_SECRET: "your-session-secret"
  OPENAI_API_KEY: "your-openai-key"
  GOOGLE_CLIENT_ID: "your-google-client-id"
  GOOGLE_CLIENT_SECRET: "your-google-client-secret"
  FLASK_ENV: "production"
```

## Security Configuration

### 1. Enable Cloud Armor (Optional)
```bash
# Create security policy
gcloud compute security-policies create talentiq-security-policy \
  --description "Security policy for TalentIQ application"

# Add rate limiting rule
gcloud compute security-policies rules create 1000 \
  --security-policy talentiq-security-policy \
  --action "rate-based-ban" \
  --rate-limit-threshold-count 100 \
  --rate-limit-threshold-interval-sec 60 \
  --ban-duration-sec 600
```

### 2. Set Up SSL/TLS
Cloud Run and App Engine automatically provide SSL certificates. For custom domains:

```bash
# Map custom domain
gcloud run domain-mappings create \
  --service talentiq \
  --domain your-domain.com \
  --region us-central1
```

## Monitoring and Logging

### Enable Cloud Logging
```bash
# Cloud Run automatically logs to Cloud Logging
# View logs
gcloud logs read "resource.type=cloud_run_revision AND resource.labels.service_name=talentiq" --limit 50
```

### Set Up Alerts
```bash
# Create alert policy for high error rates
gcloud alpha monitoring policies create --policy-from-file=alert-policy.yaml
```

## Performance Optimization

### 1. Enable CDN
```bash
# Create Cloud CDN for static assets
gcloud compute backend-services create talentiq-backend \
  --global \
  --load-balancing-scheme=EXTERNAL \
  --protocol=HTTP
```

### 2. Configure Memcache/Redis
```bash
# Create Memorystore Redis instance
gcloud redis instances create talentiq-cache \
  --size=1 \
  --region=us-central1 \
  --redis-version=redis_6_x
```

## Database Migrations

### Run Database Migrations
```bash
# Connect to Cloud SQL
gcloud sql connect talentiq-db --user=talentiq-user

# Run migrations manually or via Cloud Run job
gcloud run jobs create talentiq-migrate \
  --image gcr.io/$PROJECT_ID/talentiq:latest \
  --command "python" \
  --args "migrations.py"
```

## Backup and Recovery

### Automated Backups
```bash
# Cloud SQL automatically creates backups
# Create manual backup
gcloud sql backups create \
  --instance=talentiq-db \
  --description="Pre-deployment backup"
```

### Disaster Recovery
```bash
# Create read replica
gcloud sql instances create talentiq-db-replica \
  --master-instance-name=talentiq-db \
  --region=us-east1
```

## Cost Optimization

### 1. Set Budget Alerts
```bash
# Create budget
gcloud billing budgets create \
  --billing-account=BILLING_ACCOUNT_ID \
  --display-name="TalentIQ Budget" \
  --budget-amount=100USD
```

### 2. Use Committed Use Discounts
```bash
# Purchase committed use discount for consistent workloads
gcloud compute commitments create talentiq-commitment \
  --plan=12-month \
  --resources=vcpu=2,memory=4GB
```

## Troubleshooting

### Common Issues

1. **Database Connection Issues**
   - Verify Cloud SQL instance is running
   - Check database credentials
   - Ensure Cloud Run has Cloud SQL connector enabled

2. **Memory Issues**
   - Increase memory allocation in Cloud Run
   - Optimize database queries
   - Implement caching

3. **Timeout Issues**
   - Increase timeout settings
   - Optimize long-running operations
   - Use background tasks for heavy operations

### Debug Commands
```bash
# View Cloud Run logs
gcloud run services logs read talentiq --region=us-central1

# Check service status
gcloud run services describe talentiq --region=us-central1

# Test health endpoint
curl https://your-service-url/health
```

## Environment Variables Checklist

- [ ] `DATABASE_URL` - PostgreSQL connection string
- [ ] `SESSION_SECRET` - Flask session secret key
- [ ] `OPENAI_API_KEY` - OpenAI API key for AI features
- [ ] `GOOGLE_CLIENT_ID` - Google OAuth client ID
- [ ] `GOOGLE_CLIENT_SECRET` - Google OAuth client secret
- [ ] `FLASK_ENV` - Set to 'production'
- [ ] `SENDGRID_API_KEY` - For email notifications (optional)
- [ ] `TWILIO_ACCOUNT_SID` - For SMS notifications (optional)
- [ ] `TWILIO_AUTH_TOKEN` - For SMS notifications (optional)
- [ ] `TWILIO_PHONE_NUMBER` - For SMS notifications (optional)

## Post-Deployment Verification

1. **Health Check**: Visit `/health` endpoint
2. **Database**: Verify database connection
3. **Authentication**: Test user registration/login
4. **AI Features**: Test interview question generation
5. **File Uploads**: Test video upload functionality
6. **Calendar Integration**: Test Google Calendar connection

## Maintenance

### Regular Tasks
- Monitor application performance
- Review error logs
- Update dependencies
- Backup database
- Monitor costs
- Security updates

### Scaling
- Monitor CPU and memory usage
- Adjust instance limits based on traffic
- Consider using Cloud Load Balancing for multiple regions
- Implement auto-scaling policies

## Support

For issues specific to Google Cloud services:
- [Google Cloud Support](https://cloud.google.com/support)
- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Cloud SQL Documentation](https://cloud.google.com/sql/docs)