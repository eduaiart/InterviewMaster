# Add Environment Variables to Cloud Run Service

## Go to Your Cloud Run Service:

1. **Navigate to**: Cloud Run → Services → talentiq
2. **Click**: "Edit & deploy new revision"
3. **Scroll to**: "Variables & Secrets" section
4. **Click**: "Add Variable" button

## Add These Variables:

### Variable 1: DATABASE_URL
```
Name: DATABASE_URL
Value: postgresql://neondb_owner:npg_9cD8wkGdenNm@ep-bold-water-a522j4kr.us-east-2.aws.neon.tech/neondb?sslmode=require
```

### Variable 2: SESSION_SECRET
```
Name: SESSION_SECRET
Value: talentiq_secure_key_2025_abcdef123456789
```

### Variable 3: OPENAI_API_KEY (Optional)
```
Name: OPENAI_API_KEY
Value: [your OpenAI API key if available]
```

## Deploy:
Click "Deploy" button at the bottom. Wait 2-3 minutes for the service to restart.

## Result:
Your TalentIQ application will be accessible at the Cloud Run URL with all features working.