import json
import logging
import os
from datetime import datetime
from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from app import app, db
from models import User, Interview, InterviewResponse, Question, VideoRecording
from ai_service import generate_interview_questions, score_interview_responses, analyze_video_interview

@app.route('/')
def index():
    """Landing page - shows different content based on user role"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration with role selection"""
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']
        
        # Validate inputs
        if not username or not email or not password or not role:
            flash('All fields are required.', 'error')
            return render_template('register.html')
        
        if role not in ['recruiter', 'candidate']:
            flash('Invalid role selected.', 'error')
            return render_template('register.html')
        
        # Check if user already exists
        if User.query.filter_by(username=username).first():
            flash('Username already exists.', 'error')
            return render_template('register.html')
        
        if User.query.filter_by(email=email).first():
            flash('Email already exists.', 'error')
            return render_template('register.html')
        
        # Create new user
        password_hash = generate_password_hash(password)
        user = User(username=username, email=email, password_hash=password_hash, role=role)
        
        try:
            db.session.add(user)
            db.session.commit()
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            logging.error(f"Registration error: {e}")
            flash('Registration failed. Please try again.', 'error')
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            flash(f'Welcome back, {user.username}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password.', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    """User logout"""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    """Role-based dashboard"""
    if current_user.role == 'recruiter':
        # Recruiter dashboard - show interviews created and candidate analytics
        interviews = Interview.query.filter_by(recruiter_id=current_user.id).order_by(Interview.created_at.desc()).all()
        total_responses = sum(len(interview.responses) for interview in interviews)
        return render_template('dashboard.html', 
                             interviews=interviews, 
                             total_responses=total_responses,
                             user_role='recruiter')
    else:
        # Candidate dashboard - show available interviews and completed ones
        completed_responses = InterviewResponse.query.filter_by(candidate_id=current_user.id).all()
        completed_interview_ids = [r.interview_id for r in completed_responses]
        available_interviews = Interview.query.filter(
            Interview.is_active == True,
            ~Interview.id.in_(completed_interview_ids)
        ).all()
        
        return render_template('dashboard.html',
                             available_interviews=available_interviews,
                             completed_responses=completed_responses,
                             user_role='candidate')

@app.route('/interview/create', methods=['GET', 'POST'])
@login_required
def create_interview():
    """Interview builder for recruiters"""
    if current_user.role != 'recruiter':
        flash('Access denied. Only recruiters can create interviews.', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        title = request.form['title']
        job_description = request.form['job_description']
        duration = int(request.form['duration'])
        
        if not title or not job_description:
            flash('Title and job description are required.', 'error')
            return render_template('interview_builder.html')
        
        try:
            # Generate questions using AI
            questions = generate_interview_questions(job_description, title)
            
            # Create interview
            interview = Interview(
                title=title,
                job_description=job_description,
                questions=json.dumps(questions),
                duration_minutes=duration,
                recruiter_id=current_user.id
            )
            
            db.session.add(interview)
            db.session.commit()
            
            flash('Interview created successfully!', 'success')
            return redirect(url_for('dashboard'))
            
        except Exception as e:
            db.session.rollback()
            logging.error(f"Interview creation error: {e}")
            flash('Failed to create interview. Please check your OpenAI API configuration.', 'error')
    
    return render_template('interview_builder.html')

@app.route('/interview/<int:interview_id>')
@login_required
def interview_interface(interview_id):
    """Interview interface for candidates"""
    if current_user.role != 'candidate':
        flash('Access denied. Only candidates can take interviews.', 'error')
        return redirect(url_for('dashboard'))
    
    interview = Interview.query.get_or_404(interview_id)
    
    # Check if already completed
    existing_response = InterviewResponse.query.filter_by(
        interview_id=interview_id, 
        candidate_id=current_user.id
    ).first()
    
    if existing_response:
        flash('You have already completed this interview.', 'info')
        return redirect(url_for('interview_results', response_id=existing_response.id))
    
    questions = json.loads(interview.questions)
    return render_template('interview_interface.html', interview=interview, questions=questions)

@app.route('/interview/<int:interview_id>/submit', methods=['POST'])
@login_required
def submit_interview(interview_id):
    """Submit interview responses"""
    if current_user.role != 'candidate':
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard'))
    
    interview = Interview.query.get_or_404(interview_id)
    
    # Check if already completed
    existing_response = InterviewResponse.query.filter_by(
        interview_id=interview_id, 
        candidate_id=current_user.id
    ).first()
    
    if existing_response:
        flash('You have already completed this interview.', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        # Get answers from form
        answers = {}
        questions = json.loads(interview.questions)
        
        for i, question in enumerate(questions):
            answer_key = f'answer_{i}'
            answers[str(i)] = {
                'question': question['text'],
                'answer': request.form.get(answer_key, '').strip()
            }
        
        # Calculate time taken (in real implementation, this would be tracked client-side)
        time_taken = request.form.get('time_taken', 0)
        
        # Score the responses using AI
        score, feedback = score_interview_responses(answers, interview.job_description)
        
        # Save response
        response = InterviewResponse(
            interview_id=interview_id,
            candidate_id=current_user.id,
            answers=json.dumps(answers),
            ai_score=score,
            ai_feedback=feedback,
            time_taken_minutes=int(time_taken) if time_taken else None
        )
        
        db.session.add(response)
        db.session.commit()
        
        flash('Interview submitted successfully!', 'success')
        return redirect(url_for('interview_results', response_id=response.id))
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Interview submission error: {e}")
        flash('Failed to submit interview. Please try again.', 'error')
        return redirect(url_for('interview_interface', interview_id=interview_id))

@app.route('/interview/results/<int:response_id>')
@login_required
def interview_results(response_id):
    """Show interview results"""
    response = InterviewResponse.query.get_or_404(response_id)
    
    # Check permissions
    if (current_user.role == 'candidate' and response.candidate_id != current_user.id) or \
       (current_user.role == 'recruiter' and response.interview.recruiter_id != current_user.id):
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard'))
    
    answers = json.loads(response.answers)
    return render_template('interview_results.html', response=response, answers=answers)

@app.route('/candidates/<int:interview_id>')
@login_required
def candidate_analytics(interview_id):
    """Candidate analytics for recruiters"""
    if current_user.role != 'recruiter':
        flash('Access denied. Only recruiters can view analytics.', 'error')
        return redirect(url_for('dashboard'))
    
    interview = Interview.query.get_or_404(interview_id)
    
    # Check if recruiter owns this interview
    if interview.recruiter_id != current_user.id:
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard'))
    
    responses = InterviewResponse.query.filter_by(interview_id=interview_id).order_by(InterviewResponse.ai_score.desc()).all()
    
    # Calculate analytics
    if responses:
        avg_score = sum(r.ai_score for r in responses) / len(responses)
        # Fix division by zero for time calculation
        time_responses = [r for r in responses if r.time_taken_minutes]
        avg_time = sum(r.time_taken_minutes for r in time_responses) / len(time_responses) if time_responses else 0
    else:
        avg_score = 0
        avg_time = 0
    
    return render_template('candidate_analytics.html', 
                         interview=interview, 
                         responses=responses,
                         avg_score=avg_score,
                         avg_time=avg_time)

@app.route('/toggle_interview_status', methods=['POST'])
@login_required
def toggle_interview_status():
    """Toggle interview active/inactive status"""
    if current_user.role != 'recruiter':
        return jsonify({'error': 'Access denied. Only recruiters can modify interviews.'}), 403
    
    try:
        data = request.get_json()
        interview_id = data.get('interview_id')
        is_active = data.get('is_active')
        
        if interview_id is None or is_active is None:
            return jsonify({'error': 'Missing required data'}), 400
        
        interview = Interview.query.get_or_404(interview_id)
        
        # Check if recruiter owns this interview
        if interview.recruiter_id != current_user.id:
            return jsonify({'error': 'Access denied'}), 403
        
        # Update the status
        interview.is_active = is_active
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f"Interview {'activated' if is_active else 'deactivated'} successfully",
            'is_active': is_active
        })
        
    except Exception as e:
        logging.error(f"Error toggling interview status: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to update interview status'}), 500

@app.route('/upload_video_recording', methods=['POST'])
@login_required
def upload_video_recording():
    """Handle video recording upload and AI analysis"""
    try:
        if 'video' not in request.files:
            return jsonify({'error': 'No video file provided'}), 400
        
        video_file = request.files['video']
        interview_id = request.form.get('interview_id')
        candidate_id = request.form.get('candidate_id')
        
        if not video_file or not interview_id or not candidate_id:
            return jsonify({'error': 'Missing required data'}), 400
        
        # Verify permissions
        if current_user.id != int(candidate_id):
            return jsonify({'error': 'Access denied'}), 403
        
        # Create uploads directory if it doesn't exist
        upload_dir = os.path.join(app.root_path, 'uploads', 'videos')
        os.makedirs(upload_dir, exist_ok=True)
        
        # Generate secure filename
        filename = secure_filename(f"{candidate_id}_{interview_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.webm")
        file_path = os.path.join(upload_dir, filename)
        
        # Save the video file
        video_file.save(file_path)
        file_size = os.path.getsize(file_path)
        
        # Get interview context for AI analysis
        interview = Interview.query.get(interview_id)
        interview_context = f"Job: {interview.title}\n{interview.job_description[:200]}" if interview else None
        
        # Perform AI analysis
        ai_analysis = analyze_video_interview(file_path, interview_context)
        
        # Create database record
        video_recording = VideoRecording(
            interview_id=interview_id,
            candidate_id=candidate_id,
            filename=filename,
            file_path=file_path,
            file_size=file_size,
            ai_analysis=json.dumps(ai_analysis),
            confidence_score=ai_analysis.get('confidence', 0),
            communication_style=ai_analysis.get('communication_style', 'Standard'),
            processed_at=datetime.utcnow()
        )
        
        db.session.add(video_recording)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'ai_analysis': ai_analysis,
            'message': 'Video uploaded and analyzed successfully'
        })
        
    except Exception as e:
        logging.error(f"Error uploading video: {e}")
        db.session.rollback()
        return jsonify({'error': 'Upload failed'}), 500

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500
