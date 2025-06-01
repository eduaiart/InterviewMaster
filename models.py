from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from app import db

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='candidate')  # 'recruiter' or 'candidate'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    interviews_created = db.relationship('Interview', backref='creator', lazy=True, foreign_keys='Interview.recruiter_id')
    interview_responses = db.relationship('InterviewResponse', backref='candidate', lazy=True)

class Interview(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    job_description = db.Column(db.Text, nullable=False)
    questions = db.Column(db.Text, nullable=False)  # JSON string of questions
    duration_minutes = db.Column(db.Integer, default=30)
    recruiter_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    responses = db.relationship('InterviewResponse', backref='interview', lazy=True)

class InterviewResponse(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    interview_id = db.Column(db.Integer, db.ForeignKey('interview.id'), nullable=False)
    candidate_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    answers = db.Column(db.Text, nullable=False)  # JSON string of answers
    ai_score = db.Column(db.Float, default=0.0)
    ai_feedback = db.Column(db.Text)
    completed_at = db.Column(db.DateTime, default=datetime.utcnow)
    time_taken_minutes = db.Column(db.Integer)
    
    # Composite unique constraint to prevent duplicate responses
    __table_args__ = (db.UniqueConstraint('interview_id', 'candidate_id', name='_interview_candidate_uc'),)

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    interview_id = db.Column(db.Integer, db.ForeignKey('interview.id'), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    question_type = db.Column(db.String(50), default='text')  # 'text', 'multiple_choice'
    order_index = db.Column(db.Integer, nullable=False)
    weight = db.Column(db.Float, default=1.0)
    expected_keywords = db.Column(db.Text)  # JSON string of expected keywords for scoring

class VideoRecording(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    interview_id = db.Column(db.Integer, db.ForeignKey('interview.id'), nullable=False)
    candidate_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer)
    duration_seconds = db.Column(db.Integer)
    ai_analysis = db.Column(db.Text)  # JSON string of AI analysis results
    confidence_score = db.Column(db.Float, default=0.0)
    communication_style = db.Column(db.Text)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    processed_at = db.Column(db.DateTime)
    
    # Relationships
    interview = db.relationship('Interview', backref='video_recordings')
    candidate = db.relationship('User', backref='video_recordings')

class TeamMember(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    organization_id = db.Column(db.Integer, nullable=False)  # For multi-tenant support
    role = db.Column(db.String(50), nullable=False, default='recruiter')  # admin, recruiter, viewer
    permissions = db.Column(db.Text)  # JSON string of permissions
    is_active = db.Column(db.Boolean, default=True)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    added_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    last_active = db.Column(db.DateTime)
    
    # Relationships
    user = db.relationship('User', foreign_keys=[user_id], backref='team_memberships')
    added_by_user = db.relationship('User', foreign_keys=[added_by])

class IntegrationSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, nullable=False)
    setting_type = db.Column(db.String(50), nullable=False)  # webhook, ats, etc.
    setting_key = db.Column(db.String(100), nullable=False)
    setting_value = db.Column(db.Text)
    is_encrypted = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (db.UniqueConstraint('organization_id', 'setting_type', 'setting_key', name='_org_setting_uc'),)

class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    action = db.Column(db.String(100), nullable=False)
    resource_type = db.Column(db.String(50), nullable=False)
    resource_id = db.Column(db.Integer)
    details = db.Column(db.Text)  # JSON string with additional details
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='audit_logs')

class InterviewSchedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    interview_id = db.Column(db.Integer, db.ForeignKey('interview.id'), nullable=False)
    candidate_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    recruiter_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    scheduled_datetime = db.Column(db.DateTime, nullable=False)
    duration_minutes = db.Column(db.Integer, default=60)
    status = db.Column(db.String(20), default='scheduled')  # scheduled, confirmed, completed, cancelled
    meeting_link = db.Column(db.String(500))  # For video interviews
    calendar_event_id = db.Column(db.String(255))  # Google Calendar event ID
    time_zone = db.Column(db.String(50), default='UTC')
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    interview = db.relationship('Interview', backref='schedules')
    candidate = db.relationship('User', foreign_keys=[candidate_id], backref='candidate_schedules')
    recruiter = db.relationship('User', foreign_keys=[recruiter_id], backref='recruiter_schedules')

class AvailabilitySlot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    day_of_week = db.Column(db.Integer, nullable=False)  # 0=Monday, 6=Sunday
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    time_zone = db.Column(db.String(50), default='UTC')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref='availability_slots')

class ScheduleNotification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    schedule_id = db.Column(db.Integer, db.ForeignKey('interview_schedule.id'), nullable=False)
    notification_type = db.Column(db.String(20), nullable=False)  # email, sms
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    send_at = db.Column(db.DateTime, nullable=False)
    sent_at = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='pending')  # pending, sent, failed
    message_content = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    schedule = db.relationship('InterviewSchedule', backref='notifications')
    recipient = db.relationship('User', backref='schedule_notifications')
