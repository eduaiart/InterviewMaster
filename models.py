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
