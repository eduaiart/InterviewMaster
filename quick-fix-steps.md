# Quick Fix for TalentIQ Service

## Add These Environment Variables to Cloud Run:

1. **Go to Cloud Run Service**
   - Cloud Run → Services → talentiq
   - Click "Edit & deploy new revision"
   - Scroll to "Variables & Secrets"

2. **Add These Variables:**

```
DATABASE_URL = postgresql://postgres:YOUR_DB_PASSWORD@YOUR_DB_PUBLIC_IP:5432/postgres
SESSION_SECRET = talentiq2025secretkey123456789abc
```

3. **Get Your Database IP:**
   - Go to SQL → talentiq-db → Overview
   - Copy Public IP address
   - Use the password you created during database setup

4. **Deploy the revision**

Once these variables are added, your TalentIQ service will start successfully and be accessible at the Cloud Run URL.