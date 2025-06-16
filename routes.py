import json
import logging
import os
from datetime import datetime, timedelta
from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from app import app, db
from models import User, Interview, InterviewResponse, Question, VideoRecording, TeamMember, IntegrationSettings, AuditLog, InterviewSchedule, AvailabilitySlot, ScheduleNotification
from ai_service import generate_interview_questions, score_interview_responses, analyze_video_interview
from calendar_service import CalendarService

@app.route('/')
def index():
    """Landing page - shows different content based on user role"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('landing.html')

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

@app.route('/analytics/advanced')
@login_required
def advanced_analytics():
    """Advanced analytics dashboard with filtering and charts"""
    if current_user.role != 'recruiter':
        flash('Access denied. Only recruiters can view advanced analytics.', 'error')
        return redirect(url_for('dashboard'))
    
    # Get filter parameters
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    min_score = request.args.get('min_score', type=float)
    max_score = request.args.get('max_score', type=float)
    
    # Base query for recruiter's interviews
    base_query = InterviewResponse.query.join(Interview).filter(
        Interview.recruiter_id == current_user.id
    )
    
    # Apply filters
    if start_date:
        base_query = base_query.filter(InterviewResponse.completed_at >= start_date)
    if end_date:
        base_query = base_query.filter(InterviewResponse.completed_at <= end_date)
    if min_score is not None:
        base_query = base_query.filter(InterviewResponse.ai_score >= min_score)
    if max_score is not None:
        base_query = base_query.filter(InterviewResponse.ai_score <= max_score)
    
    responses = base_query.order_by(InterviewResponse.completed_at.desc()).all()
    
    # Calculate statistics
    total_candidates = len(set(r.candidate_id for r in responses))
    total_interviews = Interview.query.filter_by(recruiter_id=current_user.id, is_active=True).count()
    avg_score = sum(r.ai_score for r in responses) / len(responses) if responses else 0
    time_responses = [r for r in responses if r.time_taken_minutes]
    avg_time = sum(r.time_taken_minutes for r in time_responses) / len(time_responses) if time_responses else 0
    
    # Score distribution for chart
    score_ranges = [0, 0, 0, 0, 0]  # 0-20, 21-40, 41-60, 61-80, 81-100
    for response in responses:
        score = response.ai_score
        if score <= 20:
            score_ranges[0] += 1
        elif score <= 40:
            score_ranges[1] += 1
        elif score <= 60:
            score_ranges[2] += 1
        elif score <= 80:
            score_ranges[3] += 1
        else:
            score_ranges[4] += 1
    
    # Trend data (last 7 days)
    from datetime import datetime, timedelta
    trend_labels = []
    trend_data = []
    for i in range(6, -1, -1):
        date = datetime.now().date() - timedelta(days=i)
        trend_labels.append(date.strftime('%m/%d'))
        count = len([r for r in responses if r.completed_at.date() == date])
        trend_data.append(count)
    
    return render_template('advanced_analytics.html',
                         responses=responses,
                         total_candidates=total_candidates,
                         total_interviews=total_interviews,
                         avg_score=avg_score,
                         avg_time=avg_time,
                         score_distribution=score_ranges,
                         trend_labels=trend_labels,
                         trend_data=trend_data)

@app.route('/candidate/<int:candidate_id>/profile')
@login_required
def candidate_profile(candidate_id):
    """Detailed candidate profile for recruiters"""
    if current_user.role != 'recruiter':
        flash('Access denied. Only recruiters can view candidate profiles.', 'error')
        return redirect(url_for('dashboard'))
    
    candidate = User.query.get_or_404(candidate_id)
    if candidate.role != 'candidate':
        flash('Invalid candidate ID.', 'error')
        return redirect(url_for('dashboard'))
    
    # Get responses for interviews created by current recruiter
    responses = InterviewResponse.query.join(Interview).filter(
        Interview.recruiter_id == current_user.id,
        InterviewResponse.candidate_id == candidate_id
    ).order_by(InterviewResponse.completed_at.desc()).all()
    
    if not responses:
        flash('No interview data found for this candidate.', 'error')
        return redirect(url_for('dashboard'))
    
    # Calculate statistics
    avg_score = sum(r.ai_score for r in responses) / len(responses)
    video_recordings = VideoRecording.query.join(Interview).filter(
        Interview.recruiter_id == current_user.id,
        VideoRecording.candidate_id == candidate_id
    ).all()
    
    # Skills breakdown (mock data based on AI feedback)
    skills_breakdown = {
        'technical_skills': avg_score * 0.9,
        'communication': avg_score * 1.1,
        'problem_solving': avg_score * 0.95,
        'cultural_fit': avg_score * 1.05
    }
    
    # Performance data for chart
    performance_dates = [r.completed_at.strftime('%m/%d') for r in responses]
    performance_scores = [r.ai_score for r in responses]
    
    # Communication analysis
    communication_strengths = [
        "Clear articulation of ideas",
        "Professional presentation",
        "Confident delivery"
    ]
    communication_improvements = [
        "Expand on technical details",
        "Use more specific examples",
        "Improve response structure"
    ]
    
    return render_template('candidate_profile.html',
                         candidate=candidate,
                         responses=responses,
                         avg_score=avg_score,
                         video_recordings=video_recordings,
                         skills_breakdown=skills_breakdown,
                         performance_dates=performance_dates,
                         performance_scores=performance_scores,
                         communication_strengths=communication_strengths,
                         communication_improvements=communication_improvements)

@app.route('/compare_candidates', methods=['POST'])
@login_required
def compare_candidates():
    """Compare multiple candidates side by side"""
    if current_user.role != 'recruiter':
        return jsonify({'error': 'Access denied'}), 403
    
    data = request.get_json()
    response_ids = data.get('response_ids', [])
    
    if len(response_ids) < 2:
        return jsonify({'error': 'Need at least 2 candidates to compare'}), 400
    
    responses = InterviewResponse.query.join(Interview).filter(
        InterviewResponse.id.in_(response_ids),
        Interview.recruiter_id == current_user.id
    ).all()
    
    comparison_html = render_template('comparison_table.html', responses=responses)
    return jsonify({'html': comparison_html})

@app.route('/bulk_action', methods=['POST'])
@login_required
def bulk_action():
    """Handle bulk actions on interview responses"""
    if current_user.role != 'recruiter':
        return jsonify({'error': 'Access denied'}), 403
    
    data = request.get_json()
    action = data.get('action')
    response_ids = data.get('response_ids', [])
    
    try:
        responses = InterviewResponse.query.join(Interview).filter(
            InterviewResponse.id.in_(response_ids),
            Interview.recruiter_id == current_user.id
        ).all()
        
        if action == 'delete':
            for response in responses:
                db.session.delete(response)
            db.session.commit()
            return jsonify({'success': True, 'message': f'Deleted {len(responses)} responses'})
        
        return jsonify({'error': 'Invalid action'}), 400
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Bulk action error: {e}")
        return jsonify({'error': 'Action failed'}), 500

@app.route('/export_report', methods=['POST'])
@login_required
def export_report():
    """Export analytics report in various formats"""
    if current_user.role != 'recruiter':
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard'))
    
    format_type = request.form.get('format', 'pdf')
    
    # Get filtered data
    responses = InterviewResponse.query.join(Interview).filter(
        Interview.recruiter_id == current_user.id
    ).all()
    
    if format_type == 'pdf':
        # Generate PDF report
        from io import BytesIO
        from flask import make_response
        
        # Create a simple text report for now
        report_content = f"Interview Analytics Report\n"
        report_content += f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        report_content += f"Total Responses: {len(responses)}\n"
        
        for response in responses:
            report_content += f"\nCandidate: {response.candidate.username}\n"
            report_content += f"Interview: {response.interview.title}\n"
            report_content += f"Score: {response.ai_score:.1f}%\n"
            report_content += f"Date: {response.completed_at.strftime('%Y-%m-%d')}\n"
            report_content += "---\n"
        
        response = make_response(report_content)
        response.headers['Content-Type'] = 'text/plain'
        response.headers['Content-Disposition'] = 'attachment; filename=analytics_report.txt'
        return response
    
    flash('Export format not supported yet.', 'warning')
    return redirect(url_for('advanced_analytics'))

@app.route('/team/management')
@login_required
def team_management():
    """Team management dashboard for enterprise users"""
    if current_user.role not in ['admin', 'recruiter']:
        flash('Access denied. Insufficient permissions.', 'error')
        return redirect(url_for('dashboard'))
    
    # Get team members (mock organization_id = 1 for demo)
    organization_id = 1
    team_members = []
    
    # Get all recruiters as team members
    recruiters = User.query.filter_by(role='recruiter').all()
    for recruiter in recruiters:
        # Calculate stats for each recruiter
        interviews_count = Interview.query.filter_by(recruiter_id=recruiter.id).count()
        responses = InterviewResponse.query.join(Interview).filter(
            Interview.recruiter_id == recruiter.id
        ).all()
        responses_count = len(responses)
        avg_score = sum(r.ai_score for r in responses) / len(responses) if responses else 0
        
        # Create team member object
        member_data = type('obj', (object,), {
            'id': recruiter.id,
            'username': recruiter.username,
            'email': recruiter.email,
            'role': recruiter.role,
            'interviews_count': interviews_count,
            'responses_count': responses_count,
            'avg_score': avg_score,
            'is_active': True,
            'last_active': recruiter.created_at
        })()
        
        team_members.append(member_data)
    
    # Calculate team statistics
    total_interviews = sum(m.interviews_count for m in team_members)
    team_avg_score = sum(m.avg_score for m in team_members) / len(team_members) if team_members else 0
    active_members = len([m for m in team_members if m.is_active])
    
    return render_template('team_management.html',
                         team_members=team_members,
                         total_interviews=total_interviews,
                         team_avg_score=team_avg_score,
                         active_members=active_members)

@app.route('/api/test_webhook', methods=['POST'])
@login_required
def test_webhook():
    """Test webhook connectivity"""
    if current_user.role not in ['admin', 'recruiter']:
        return jsonify({'error': 'Access denied'}), 403
    
    data = request.get_json()
    webhook_url = data.get('webhook_url')
    webhook_type = data.get('webhook_type')
    
    try:
        import requests
        
        # Create test payload
        test_payload = {
            'test': True,
            'type': webhook_type,
            'timestamp': datetime.now().isoformat(),
            'data': {
                'interview_id': 1,
                'candidate_name': 'Test Candidate',
                'score': 85.5
            }
        }
        
        response = requests.post(webhook_url, json=test_payload, timeout=10)
        
        if response.status_code == 200:
            return jsonify({'success': True, 'message': 'Webhook test successful'})
        else:
            return jsonify({'success': False, 'error': f'HTTP {response.status_code}'})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/test_ats', methods=['POST'])
@login_required
def test_ats_connection():
    """Test ATS integration connectivity"""
    if current_user.role not in ['admin', 'recruiter']:
        return jsonify({'error': 'Access denied'}), 403
    
    data = request.get_json()
    provider = data.get('provider')
    api_key = data.get('api_key')
    
    # For demo purposes, simulate ATS connection test
    if provider and api_key:
        # In real implementation, this would test actual ATS APIs
        if len(api_key) > 10:  # Basic validation
            return jsonify({'success': True, 'message': f'{provider.title()} connection successful'})
        else:
            return jsonify({'success': False, 'error': 'Invalid API key format'})
    
    return jsonify({'success': False, 'error': 'Missing provider or API key'})

@app.route('/api/save_integration_settings', methods=['POST'])
@login_required
def save_integration_settings():
    """Save integration settings"""
    if current_user.role not in ['admin', 'recruiter']:
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        settings = request.get_json()
        organization_id = 1  # Mock organization ID
        
        # Save each setting
        for key, value in settings.items():
            if value:  # Only save non-empty values
                setting = IntegrationSettings.query.filter_by(
                    organization_id=organization_id,
                    setting_type='integration',
                    setting_key=key
                ).first()
                
                if setting:
                    setting.setting_value = value
                    setting.updated_at = datetime.now()
                else:
                    setting = IntegrationSettings(
                        organization_id=organization_id,
                        setting_type='integration',
                        setting_key=key,
                        setting_value=value,
                        is_encrypted=(key == 'ats_api_key')
                    )
                    db.session.add(setting)
        
        # Log the action
        audit_log = AuditLog(
            user_id=current_user.id,
            action='update_integration_settings',
            resource_type='settings',
            details=json.dumps({'settings_updated': list(settings.keys())}),
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        db.session.add(audit_log)
        
        db.session.commit()
        return jsonify({'success': True})
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error saving integration settings: {e}")
        return jsonify({'success': False, 'error': 'Failed to save settings'})

@app.route('/api/add_team_member', methods=['POST'])
@login_required
def add_team_member():
    """Add a new team member"""
    if current_user.role != 'admin':
        return jsonify({'error': 'Access denied. Admin privileges required'}), 403
    
    try:
        data = request.get_json()
        email = data.get('email')
        role = data.get('role')
        permissions = data.get('permissions', [])
        
        # Check if user already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            return jsonify({'success': False, 'error': 'User already exists'})
        
        # Create new user (in real app, this would send invitation email)
        new_user = User(
            username=email.split('@')[0],
            email=email,
            password_hash=generate_password_hash('temp_password'),
            role=role
        )
        db.session.add(new_user)
        db.session.flush()  # Get the user ID
        
        # Create team membership
        team_member = TeamMember(
            user_id=new_user.id,
            organization_id=1,
            role=role,
            permissions=json.dumps(permissions),
            added_by=current_user.id
        )
        db.session.add(team_member)
        
        # Log the action
        audit_log = AuditLog(
            user_id=current_user.id,
            action='add_team_member',
            resource_type='user',
            resource_id=new_user.id,
            details=json.dumps({'email': email, 'role': role})
        )
        db.session.add(audit_log)
        
        db.session.commit()
        return jsonify({'success': True, 'message': 'Team member added successfully'})
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error adding team member: {e}")
        return jsonify({'success': False, 'error': 'Failed to add team member'})

@app.route('/api/get_member_details/<int:member_id>')
@login_required
def get_member_details(member_id):
    """Get detailed information about a team member"""
    if current_user.role not in ['admin', 'recruiter']:
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        member = User.query.get_or_404(member_id)
        if member.role != 'recruiter':
            return jsonify({'error': 'Invalid member ID'}), 404
        
        # Get member statistics
        interviews_count = Interview.query.filter_by(recruiter_id=member.id).count()
        responses = InterviewResponse.query.join(Interview).filter(
            Interview.recruiter_id == member.id
        ).all()
        
        member_details = {
            'id': member.id,
            'username': member.username,
            'email': member.email,
            'role': member.role,
            'created_at': member.created_at.strftime('%Y-%m-%d'),
            'interviews_count': interviews_count,
            'responses_count': len(responses),
            'avg_score': sum(r.ai_score for r in responses) / len(responses) if responses else 0,
            'recent_activity': [
                {
                    'type': 'interview_created',
                    'title': interview.title,
                    'date': interview.created_at.strftime('%Y-%m-%d')
                }
                for interview in Interview.query.filter_by(recruiter_id=member.id).order_by(Interview.created_at.desc()).limit(5)
            ]
        }
        
        html_content = f"""
        <div class="member-details">
            <div class="row">
                <div class="col-md-6">
                    <h6>Basic Information</h6>
                    <p><strong>Username:</strong> {member_details['username']}</p>
                    <p><strong>Email:</strong> {member_details['email']}</p>
                    <p><strong>Role:</strong> {member_details['role'].title()}</p>
                    <p><strong>Joined:</strong> {member_details['created_at']}</p>
                </div>
                <div class="col-md-6">
                    <h6>Statistics</h6>
                    <p><strong>Interviews Created:</strong> {member_details['interviews_count']}</p>
                    <p><strong>Total Responses:</strong> {member_details['responses_count']}</p>
                    <p><strong>Average Score:</strong> {member_details['avg_score']:.1f}%</p>
                </div>
            </div>
            <div class="row mt-3">
                <div class="col-12">
                    <h6>Recent Activity</h6>
                    <ul class="list-group">
                        {''.join([f'<li class="list-group-item"><small>{activity["date"]}</small> - Created interview: {activity["title"]}</li>' for activity in member_details['recent_activity']])}
                    </ul>
                </div>
            </div>
        </div>
        """
        
        return jsonify({'html': html_content})
        
    except Exception as e:
        logging.error(f"Error getting member details: {e}")
        return jsonify({'error': 'Failed to load member details'}), 500

@app.route('/api/update_member_role', methods=['POST'])
@login_required
def update_member_role():
    """Update a team member's role"""
    if current_user.role != 'admin':
        return jsonify({'error': 'Access denied. Admin privileges required'}), 403
    
    try:
        data = request.get_json()
        member_id = data.get('member_id')
        new_role = data.get('new_role')
        
        if new_role not in ['recruiter', 'admin', 'viewer']:
            return jsonify({'success': False, 'error': 'Invalid role'})
        
        member = User.query.get_or_404(member_id)
        old_role = member.role
        member.role = new_role
        
        # Log the action
        audit_log = AuditLog(
            user_id=current_user.id,
            action='update_member_role',
            resource_type='user',
            resource_id=member_id,
            details=json.dumps({'old_role': old_role, 'new_role': new_role})
        )
        db.session.add(audit_log)
        
        db.session.commit()
        return jsonify({'success': True, 'message': f'Role updated to {new_role}'})
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error updating member role: {e}")
        return jsonify({'success': False, 'error': 'Failed to update role'})

@app.route('/api/toggle_member_status', methods=['POST'])
@login_required
def toggle_member_status():
    """Toggle a team member's active status"""
    if current_user.role != 'admin':
        return jsonify({'error': 'Access denied. Admin privileges required'}), 403
    
    try:
        data = request.get_json()
        member_id = data.get('member_id')
        
        # For demo purposes, we'll simulate status toggle
        # In real implementation, this would update a team_member table
        return jsonify({'success': True, 'message': 'Member status updated'})
        
    except Exception as e:
        logging.error(f"Error toggling member status: {e}")
        return jsonify({'success': False, 'error': 'Failed to update status'})

@app.route('/api/export_team_report')
@login_required
def export_team_report():
    """Export team performance report"""
    if current_user.role not in ['admin', 'recruiter']:
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        from flask import make_response
        
        # Get team data
        recruiters = User.query.filter_by(role='recruiter').all()
        
        report_content = f"Team Performance Report\n"
        report_content += f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        
        for recruiter in recruiters:
            interviews_count = Interview.query.filter_by(recruiter_id=recruiter.id).count()
            responses = InterviewResponse.query.join(Interview).filter(
                Interview.recruiter_id == recruiter.id
            ).all()
            avg_score = sum(r.ai_score for r in responses) / len(responses) if responses else 0
            
            report_content += f"Member: {recruiter.username}\n"
            report_content += f"Email: {recruiter.email}\n"
            report_content += f"Interviews Created: {interviews_count}\n"
            report_content += f"Total Responses: {len(responses)}\n"
            report_content += f"Average Score: {avg_score:.1f}%\n"
            report_content += "---\n"
        
        response = make_response(report_content)
        response.headers['Content-Type'] = 'text/plain'
        response.headers['Content-Disposition'] = 'attachment; filename=team_report.txt'
        return response
        
    except Exception as e:
        logging.error(f"Error exporting team report: {e}")
        flash('Failed to export team report.', 'error')
        return redirect(url_for('team_management'))

@app.route('/pricing')
def pricing():
    """Pricing page with subscription plans"""
    return render_template('pricing.html')

@app.route('/settings')
@login_required
def settings():
    """User settings and profile management"""
    return render_template('settings.html', user=current_user)

@app.route('/settings/update', methods=['POST'])
@login_required
def update_settings():
    """Update user profile settings"""
    try:
        # Get form data
        username = request.form.get('username')
        email = request.form.get('email')
        
        # Basic validation
        if not username or not email:
            flash('Username and email are required.', 'error')
            return redirect(url_for('settings'))
        
        # Check if username/email already exists (excluding current user)
        existing_user = User.query.filter(
            (User.username == username) | (User.email == email),
            User.id != current_user.id
        ).first()
        
        if existing_user:
            flash('Username or email already in use.', 'error')
            return redirect(url_for('settings'))
        
        # Update user profile
        current_user.username = username
        current_user.email = email
        
        # Log the action
        audit_log = AuditLog(
            user_id=current_user.id,
            action='update_profile',
            resource_type='user',
            resource_id=current_user.id,
            details=json.dumps({'username': username, 'email': email}),
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        db.session.add(audit_log)
        
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error updating profile: {e}")
        flash('Failed to update profile. Please try again.', 'error')
    
    return redirect(url_for('settings'))

@app.route('/interview/<int:interview_id>/chat')
@login_required
def chat_interview(interview_id):
    """Chat-based interview interface for candidates"""
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
    return render_template('chat_interview.html', interview=interview, questions=questions)

@app.route('/interview/<int:interview_id>/chat/submit', methods=['POST'])
@login_required
def submit_chat_interview(interview_id):
    """Submit chat interview responses with real-time AI analysis"""
    if current_user.role != 'candidate':
        return jsonify({'error': 'Access denied'}), 403
    
    interview = Interview.query.get_or_404(interview_id)
    
    # Check if already completed
    existing_response = InterviewResponse.query.filter_by(
        interview_id=interview_id, 
        candidate_id=current_user.id
    ).first()
    
    if existing_response:
        return jsonify({'error': 'Interview already completed'}), 400
    
    try:
        data = request.get_json()
        responses = data.get('responses', [])
        time_taken = data.get('time_taken', 0)
        
        # Format responses for storage
        formatted_answers = {}
        for i, response in enumerate(responses):
            formatted_answers[str(i)] = {
                'question': response.get('question', ''),
                'answer': response.get('answer', ''),
                'timestamp': response.get('timestamp', ''),
                'response_type': 'chat'
            }
        
        # Perform AI analysis on chat responses
        score, feedback = score_interview_responses(formatted_answers, interview.job_description)
        
        # Generate instant feedback for chat format
        instant_feedback = generate_instant_chat_feedback(responses)
        
        # Save response
        response = InterviewResponse(
            interview_id=interview_id,
            candidate_id=current_user.id,
            answers=json.dumps(formatted_answers),
            ai_score=score,
            ai_feedback=feedback,
            time_taken_minutes=int(time_taken) if time_taken else None
        )
        
        db.session.add(response)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'score': score,
            'feedback': instant_feedback,
            'response_id': response.id
        })
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Chat interview submission error: {e}")
        return jsonify({'error': 'Failed to submit interview'}), 500

def generate_instant_chat_feedback(responses):
    """Generate instant feedback for chat interviews using AI analysis"""
    try:
        from openai import OpenAI
        import os
        
        client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        
        # Combine all responses for analysis
        combined_text = " ".join([resp.get('answer', '') for resp in responses])
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "You are an AI interview analyst. Provide brief, encouraging instant feedback for a candidate who just completed a chat interview. Focus on communication style, personality traits, and overall impression. Keep it positive and constructive, around 2-3 sentences."
                },
                {
                    "role": "user", 
                    "content": f"Analyze these interview responses and provide instant feedback: {combined_text[:1000]}"
                }
            ],
            max_tokens=150,
            temperature=0.7
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        logging.error(f"Error generating instant feedback: {e}")
        return "Thank you for completing the interview! Your responses show good communication skills and thoughtful answers. We'll be in touch soon with next steps."

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.route('/schedule')
@login_required
def schedule_dashboard():
    """Interview scheduling dashboard"""
    if current_user.role == 'recruiter':
        # Get interviews that need scheduling
        interviews = Interview.query.filter_by(recruiter_id=current_user.id).all()
        scheduled_interviews = InterviewSchedule.query.filter_by(recruiter_id=current_user.id).all()
        
        # Check if Google Calendar is connected
        calendar_setting = IntegrationSettings.query.filter_by(
            organization_id=current_user.id,
            setting_type='calendar',
            setting_key='google_credentials'
        ).first()
        calendar_connected = calendar_setting is not None
        
        return render_template('schedule_dashboard.html', 
                             interviews=interviews, 
                             scheduled_interviews=scheduled_interviews,
                             calendar_connected=calendar_connected)
    else:
        # Candidate view - show their scheduled interviews
        scheduled_interviews = InterviewSchedule.query.filter_by(candidate_id=current_user.id).all()
        availability_slots = AvailabilitySlot.query.filter_by(user_id=current_user.id).all()
        
        return render_template('candidate_schedule.html',
                             scheduled_interviews=scheduled_interviews,
                             availability_slots=availability_slots)

@app.route('/schedule/interview/<int:interview_id>')
@login_required
def schedule_interview(interview_id):
    """Schedule a specific interview"""
    if current_user.role != 'recruiter':
        flash('Access denied. Only recruiters can schedule interviews.', 'error')
        return redirect(url_for('dashboard'))
    
    interview = Interview.query.get_or_404(interview_id)
    if interview.recruiter_id != current_user.id:
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard'))
    
    # Get candidates who have completed this interview
    candidates = db.session.query(User).join(InterviewResponse).filter(
        InterviewResponse.interview_id == interview_id,
        User.role == 'candidate'
    ).all()
    
    return render_template('schedule_interview.html', interview=interview, candidates=candidates)

@app.route('/schedule/bulk')
@login_required
def bulk_schedule():
    """Bulk scheduling interface"""
    if current_user.role != 'recruiter':
        flash('Access denied. Only recruiters can schedule interviews.', 'error')
        return redirect(url_for('dashboard'))
    
    interviews = Interview.query.filter_by(recruiter_id=current_user.id).all()
    return render_template('bulk_schedule.html', interviews=interviews)

@app.route('/schedule/create', methods=['POST'])
@login_required
def create_schedule():
    """Create a new interview schedule"""
    if current_user.role != 'recruiter':
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        data = request.get_json() or request.form
        
        interview_id = data.get('interview_id')
        candidate_id = data.get('candidate_id')
        scheduled_datetime = datetime.fromisoformat(data.get('scheduled_datetime'))
        duration_minutes = int(data.get('duration_minutes', 60))
        time_zone = data.get('time_zone', 'UTC')
        notes = data.get('notes', '')
        
        # Check if interview exists and belongs to recruiter
        interview = Interview.query.get_or_404(interview_id)
        if interview.recruiter_id != current_user.id:
            return jsonify({'error': 'Access denied'}), 403
        
        # Check if candidate exists
        candidate = User.query.get_or_404(candidate_id)
        if candidate.role != 'candidate':
            return jsonify({'error': 'Invalid candidate'}), 400
        
        # Create schedule
        schedule = InterviewSchedule(
            interview_id=interview_id,
            candidate_id=candidate_id,
            recruiter_id=current_user.id,
            scheduled_datetime=scheduled_datetime,
            duration_minutes=duration_minutes,
            time_zone=time_zone,
            notes=notes
        )
        
        db.session.add(schedule)
        db.session.commit()
        
        # Create calendar event if credentials available
        from calendar_service import CalendarService
        calendar_service = CalendarService()
        
        # Schedule notifications
        schedule_notifications(schedule)
        
        return jsonify({
            'success': True,
            'schedule_id': schedule.id,
            'message': 'Interview scheduled successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error creating schedule: {e}")
        return jsonify({'error': 'Failed to create schedule'}), 500

@app.route('/schedule/<int:schedule_id>/update', methods=['POST'])
@login_required
def update_schedule(schedule_id):
    """Update an interview schedule"""
    schedule = InterviewSchedule.query.get_or_404(schedule_id)
    
    # Check permissions
    if current_user.role == 'recruiter' and schedule.recruiter_id != current_user.id:
        return jsonify({'error': 'Access denied'}), 403
    elif current_user.role == 'candidate' and schedule.candidate_id != current_user.id:
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        data = request.get_json() or request.form
        
        if 'status' in data:
            schedule.status = data['status']
        if 'scheduled_datetime' in data and current_user.role == 'recruiter':
            schedule.scheduled_datetime = datetime.fromisoformat(data['scheduled_datetime'])
        if 'notes' in data:
            schedule.notes = data['notes']
        
        schedule.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Schedule updated successfully'})
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error updating schedule: {e}")
        return jsonify({'error': 'Failed to update schedule'}), 500

@app.route('/availability')
@login_required
def manage_availability():
    """Manage user availability"""
    availability_slots = AvailabilitySlot.query.filter_by(user_id=current_user.id).all()
    return render_template('manage_availability.html', availability_slots=availability_slots)

@app.route('/availability/add', methods=['POST'])
@login_required
def add_availability():
    """Add availability slot"""
    try:
        data = request.get_json() or request.form
        
        slot = AvailabilitySlot(
            user_id=current_user.id,
            day_of_week=int(data['day_of_week']),
            start_time=datetime.strptime(data['start_time'], '%H:%M').time(),
            end_time=datetime.strptime(data['end_time'], '%H:%M').time(),
            time_zone=data.get('time_zone', 'UTC')
        )
        
        db.session.add(slot)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Availability added successfully'})
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error adding availability: {e}")
        return jsonify({'error': 'Failed to add availability'}), 500

def schedule_notifications(schedule):
    """Schedule email and SMS notifications for interview"""
    try:
        # Schedule reminder 24 hours before
        reminder_time = schedule.scheduled_datetime - timedelta(hours=24)
        
        # Email notification for candidate
        candidate_notification = ScheduleNotification(
            schedule_id=schedule.id,
            notification_type='email',
            recipient_id=schedule.candidate_id,
            send_at=reminder_time,
            message_content=f"Reminder: You have an interview scheduled for {schedule.scheduled_datetime.strftime('%Y-%m-%d %H:%M')}"
        )
        
        # Email notification for recruiter
        recruiter_notification = ScheduleNotification(
            schedule_id=schedule.id,
            notification_type='email',
            recipient_id=schedule.recruiter_id,
            send_at=reminder_time,
            message_content=f"Reminder: Interview with {schedule.candidate.username} scheduled for {schedule.scheduled_datetime.strftime('%Y-%m-%d %H:%M')}"
        )
        
        db.session.add(candidate_notification)
        db.session.add(recruiter_notification)
        db.session.commit()
        
    except Exception as e:
        logging.error(f"Error scheduling notifications: {e}")

@app.route('/calendar/connect')
@login_required
def connect_calendar():
    """Start Google Calendar OAuth flow"""
    calendar_service = CalendarService()
    redirect_uri = url_for('calendar_callback', _external=True)
    
    auth_url, state = calendar_service.get_authorization_url(redirect_uri)
    
    if auth_url:
        # Store state in session for security
        from flask import session
        session['calendar_oauth_state'] = state
        return redirect(auth_url)
    else:
        flash('Unable to connect to Google Calendar. Please try again.', 'error')
        return redirect(url_for('schedule_dashboard'))

@app.route('/calendar/callback')
@login_required
def calendar_callback():
    """Handle Google Calendar OAuth callback"""
    from flask import session
    
    code = request.args.get('code')
    state = request.args.get('state')
    stored_state = session.get('calendar_oauth_state')
    
    if not code or not state or state != stored_state:
        flash('Calendar authorization failed. Please try again.', 'error')
        return redirect(url_for('schedule_dashboard'))
    
    calendar_service = CalendarService()
    redirect_uri = url_for('calendar_callback', _external=True)
    
    credentials = calendar_service.exchange_code_for_token(code, state, redirect_uri)
    
    if credentials:
        # Store credentials in database for user
        try:
            # Convert credentials to JSON for storage
            creds_data = credentials.to_json() if hasattr(credentials, 'to_json') else {
                'token': getattr(credentials, 'token', None),
                'refresh_token': getattr(credentials, 'refresh_token', None),
                'token_uri': getattr(credentials, 'token_uri', None),
                'client_id': getattr(credentials, 'client_id', None),
                'client_secret': getattr(credentials, 'client_secret', None),
                'scopes': getattr(credentials, 'scopes', None)
            }
            
            # Store in integration settings
            existing_setting = IntegrationSettings.query.filter_by(
                organization_id=current_user.id,  # Using user_id as org_id for simplicity
                setting_type='calendar',
                setting_key='google_credentials'
            ).first()
            
            if existing_setting:
                existing_setting.setting_value = creds_data if isinstance(creds_data, str) else json.dumps(creds_data)
            else:
                calendar_setting = IntegrationSettings(
                    organization_id=current_user.id,
                    setting_type='calendar',
                    setting_key='google_credentials',
                    setting_value=creds_data if isinstance(creds_data, str) else json.dumps(creds_data)
                )
                db.session.add(calendar_setting)
            
            db.session.commit()
            flash('Google Calendar connected successfully!', 'success')
            
        except Exception as e:
            logging.error(f"Error storing calendar credentials: {e}")
            flash('Failed to save calendar connection. Please try again.', 'error')
    else:
        flash('Failed to connect to Google Calendar. Please try again.', 'error')
    
    return redirect(url_for('schedule_dashboard'))

@app.route('/calendar/disconnect', methods=['POST'])
@login_required
def disconnect_calendar():
    """Disconnect Google Calendar integration"""
    try:
        calendar_setting = IntegrationSettings.query.filter_by(
            organization_id=current_user.id,
            setting_type='calendar',
            setting_key='google_credentials'
        ).first()
        
        if calendar_setting:
            db.session.delete(calendar_setting)
            db.session.commit()
            flash('Google Calendar disconnected successfully.', 'success')
        else:
            flash('No calendar connection found.', 'info')
            
    except Exception as e:
        logging.error(f"Error disconnecting calendar: {e}")
        flash('Failed to disconnect calendar. Please try again.', 'error')
    
    return redirect(url_for('schedule_dashboard'))

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500
