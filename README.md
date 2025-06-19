# TalentIQ - AI-Powered Interview Platform

## Overview
TalentIQ is a comprehensive AI-powered interview platform that revolutionizes recruitment through intelligent, automated candidate assessment and comprehensive management tools.

## Features

### Core Functionality
- **AI-Powered Interview Generation**: Automatically generate relevant interview questions based on job descriptions
- **Multiple Interview Formats**: Support for text-based, video, and real-time chat interviews
- **Intelligent Scoring**: AI-driven candidate evaluation with detailed feedback
- **Interview Scheduling**: Integrated calendar management with Google Calendar sync
- **Role-Based Access**: Separate interfaces for recruiters and candidates

### Advanced Features
- **Video Analysis**: AI-powered behavioral analysis of video interviews
- **Real-time Chat Interviews**: Interactive AI-assisted interview sessions
- **Comprehensive Analytics**: Detailed candidate performance metrics
- **Team Management**: Enterprise-grade collaboration tools
- **Integration Support**: Webhook and ATS system connectivity

## Technology Stack

- **Backend**: Flask (Python)
- **Database**: PostgreSQL with SQLAlchemy ORM
- **AI Integration**: OpenAI GPT-4o for intelligent analysis
- **Calendar**: Google Calendar API
- **Deployment**: Google Cloud Run with automated CI/CD
- **Authentication**: Flask-Login with role-based access control

## Live Demo

**Production URL**: https://talentiq-platform-602384951874.us-central1.run.app/

## Quick Start

### For Recruiters
1. Register as a recruiter
2. Create interview templates with job descriptions
3. Generate AI-powered questions
4. Schedule interviews with candidates
5. Review AI-generated analysis and scores

### For Candidates
1. Register as a candidate
2. Take assigned interviews
3. Choose from multiple interview formats
4. Receive instant feedback
5. Schedule follow-up interviews

## Installation

### Prerequisites
- Python 3.11+
- PostgreSQL database
- OpenAI API key
- Google Calendar API credentials

### Environment Variables
```
DATABASE_URL=postgresql://user:password@host:port/database
SESSION_SECRET=your_secure_session_key
OPENAI_API_KEY=your_openai_api_key
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
```

### Local Development
```bash
# Clone repository
git clone https://github.com/eduaiart/talentiq-platform.git
cd talentiq-platform

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export DATABASE_URL="your_database_url"
export SESSION_SECRET="your_session_secret"

# Run application
python main.py
```

## Deployment

### Google Cloud Run
1. Connect GitHub repository to Google Cloud Build
2. Configure environment variables in Cloud Run
3. Deploy using provided Dockerfile and cloudbuild.yaml

### Docker
```bash
docker build -t talentiq-platform .
docker run -p 8080:8080 talentiq-platform
```

## API Integration

### Webhook Support
- Interview completion notifications
- Score updates
- Schedule changes

### ATS Integration
- Candidate data synchronization
- Interview results export
- Bulk operations support

## Security Features

- Secure authentication with password hashing
- Role-based access control
- SQL injection protection
- CSRF protection
- Secure session management

## Performance

- Automatic database connection pooling
- Optimized SQL queries
- Container-based deployment
- Horizontal scaling support

## Support

For technical support or questions, contact the development team or refer to the deployment documentation.

## License

Proprietary software - All rights reserved