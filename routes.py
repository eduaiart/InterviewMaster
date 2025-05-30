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

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500
