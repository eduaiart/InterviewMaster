# TalentIQ - AI-Powered Interview Platform

TalentIQ is a comprehensive AI-powered interview platform that revolutionizes recruitment through intelligent, automated candidate assessment and comprehensive management tools.

## Features

- **AI-Powered Chat Interviews**: Interactive conversations with candidates using advanced AI
- **Video Interview Analysis**: Record and analyze video interviews with behavioral insights
- **Smart Scheduling**: Automated interview scheduling with calendar integration
- **Advanced Analytics**: Comprehensive reporting and candidate comparison tools
- **Team Collaboration**: Multi-user support with role-based access control
- **ATS Integration**: Seamless integration with existing HR systems

## Tech Stack

- **Backend**: Flask (Python)
- **Database**: PostgreSQL
- **AI Integration**: OpenAI GPT-4
- **Frontend**: Bootstrap 5, Feather Icons
- **Deployment**: AWS App Runner ready

## Quick Start

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Set environment variables:
   - `DATABASE_URL`
   - `OPENAI_API_KEY`
   - `SESSION_SECRET`
4. Run: `python main.py`

## Environment Variables

```
DATABASE_URL=postgresql://user:password@host:port/database
OPENAI_API_KEY=your_openai_api_key
SESSION_SECRET=your_session_secret
SENDGRID_API_KEY=your_sendgrid_key (optional)
TWILIO_ACCOUNT_SID=your_twilio_sid (optional)
TWILIO_AUTH_TOKEN=your_twilio_token (optional)
TWILIO_PHONE_NUMBER=your_twilio_phone (optional)
GOOGLE_CLIENT_ID=your_google_client_id (optional)
GOOGLE_CLIENT_SECRET=your_google_client_secret (optional)
```

## Deployment

This application is configured for AWS App Runner deployment with automatic scaling and SSL certificates.

## License

All rights reserved - TalentIQ Platform