import datetime
from flask import Blueprint, render_template, url_for, flash, redirect, request
from flask_login import login_user, current_user, logout_user, login_required
from app import db
from app.models import Event, Student, User, UserRole, Registration
from app.forms import EventForm, RegistrationForm, LoginForm, ContactForm, StudentRegistrationForm

main = Blueprint('main', __name__)
auth = Blueprint('auth', __name__)

@main.route('/teacher/event/new', methods=['GET', 'POST'])
@login_required
def create_event():
    if not current_user.is_teacher():
        flash('Access denied. Teachers only.', 'danger')
        return redirect(url_for('main.dashboard_redirect'))
    
    form = EventForm()
    if form.validate_on_submit():
        event = Event(
            title=form.title.data,
            description=form.description.data,
            start_time=form.start_time.data,
            end_time=form.end_time.data,
            location=form.location.data,
            teacher_id=current_user.id
        )
        db.session.add(event)
        db.session.commit()
        flash('Event created successfully!', 'success')
        return redirect(url_for('main.teacher_dashboard'))
    
    return render_template('create_event.html', title='Create Event', form=form)

@main.route('/teacher/events/past')
@login_required
def past_events():
    if not current_user.is_teacher():
        flash('Access denied. Teachers only.', 'danger')
        return redirect(url_for('main.dashboard_redirect'))
    
    events = Event.query.filter(
        Event.teacher_id == current_user.id,
        Event.end_time < datetime.utcnow()
    ).order_by(Event.start_time.desc()).all()
    
    return render_template('past_events.html', title='Past Events', events=events)
@auth.route('/register/student', methods=['GET', 'POST'])
def register_student():
    form = StudentRegistrationForm()
    if form.validate_on_submit():
        # Create user first
        user = User(
            username=form.username.data,
            email=form.email.data,
            role='student',
            student_id=form.student_id.data,
            year_level=form.year_level.data
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful!', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('register_student.html', form=form)
@main.route('/teacher/events/upcoming')
@login_required
def upcoming_events():
    if not current_user.is_teacher():
        flash('Access denied. Teachers only.', 'danger')
        return redirect(url_for('main.dashboard_redirect'))
    
    events = Event.query.filter(
        Event.teacher_id == current_user.id,
        Event.end_time >= datetime.datetime.now()
    ).order_by(Event.start_time.asc()).all()
    
    return render_template('upcoming_events.html', title='Upcoming Events', events=events)
@main.route('/')
@main.route('/home')
def home():
    return render_template('home.html')

@main.route('/about')
def about():
    return render_template('about.html', title='About')

@main.route('/contact', methods=['GET', 'POST'])
def contact():
    form = ContactForm()
    if form.validate_on_submit():
        # Here you would typically handle the form submission
        # For example, send an email or save to database
        flash('Your message has been sent! We will get back to you soon.', 'success')
        return redirect(url_for('main.contact'))
    return render_template('contact.html', title='Contact', form=form)

@main.route('/dashboard')
@main.route('/dashboard')
@login_required
def dashboard_redirect():
    if current_user.is_teacher():
        return redirect(url_for('main.teacher_dashboard'))
    return redirect(url_for('main.student_dashboard'))

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard_redirect'))
    
    form = RegistrationForm()
    if form.validate_on_submit():  # Changed from form.validate()
        try:
            print(f"Form Data - Role: {form.role.data}, Student ID: {form.student_id.data}, Year Level: {form.year_level.data}")
            
            user = User(
                username=form.username.data,
                email=form.email.data,
                role=form.role.data
            )
            
            if form.role.data == 'student':
                user.student_id = form.student_id.data
                user.year_level = form.year_level.data
                print(f"Creating student with ID: {user.student_id} and Year Level: {user.year_level}")
            else:
                user.subject = form.subject.data
                user.department = form.department.data
                
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            flash('Registration successful! You can now log in.', 'success')
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            db.session.rollback()
            print(f"Error during registration: {str(e)}")  # Debug print
            flash(f'An error occurred during registration: {str(e)}', 'danger')
    else:
        print("Form validation errors:", form.errors)  # Debug print
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{field}: {error}', 'danger')
    
    return render_template('register.html', title='Register', form=form)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard_redirect'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            if user.role == form.role.data:
                if user.is_teacher() and not (user.subject and user.department):
                    flash('Teacher profile is incomplete. Please contact admin.', 'danger')
                else:
                    login_user(user, remember=form.remember.data)
                    next_page = request.args.get('next')
                    if user.is_teacher():
                        return redirect(next_page) if next_page else redirect(url_for('main.teacher_dashboard'))
                    else:
                        return redirect(next_page) if next_page else redirect(url_for('main.student_dashboard'))
            else:
                flash('Please select the correct role for your account.', 'danger')
        else:
            flash('Invalid email or password.', 'danger')
    
    return render_template('login.html', title='Login', form=form)

@main.route('/teacher/dashboard')
@login_required
def teacher_dashboard():
    if not current_user.is_teacher():
        flash('Access denied. Teachers only.', 'danger')
        return redirect(url_for('main.dashboard_redirect'))
    
    # Get all events for the teacher
    all_events = Event.query.filter(Event.teacher_id == current_user.id).all()
    
    # Get upcoming events
    upcoming_events = Event.query.filter(
        Event.teacher_id == current_user.id,
        Event.end_time >= datetime.datetime.now()
    ).order_by(Event.start_time.asc()).limit(5).all()
    
    # Calculate stats
    upcoming_count = len(upcoming_events)
    
    # Calculate total hours from event durations
    total_hours = 0
    for event in all_events:
        duration = event.end_time - event.start_time
        hours = duration.total_seconds() / 3600
        total_hours += hours
    
    return render_template('dashboard_teacher.html', 
                         title='Teacher Dashboard',
                         upcoming_events=upcoming_events,
                         upcoming_count=upcoming_count,
                         total_hours=round(total_hours, 1))
@main.route('/student/dashboard')
@login_required
def student_dashboard():
    if not current_user.is_student():
        flash('Access denied. Students only.', 'danger')
        return redirect(url_for('main.dashboard_redirect'))
    
    # Get all available events
    available_events = Event.query.filter(
        Event.end_time >= datetime.datetime.now()
    ).order_by(Event.start_time.asc()).all()
    
    # Get student's registered events
    registered_events = Event.query.join(Registration).filter(
        Registration.student_id == current_user.id
    ).all()
    
    return render_template('dashboard_student.html', 
                         available_events=available_events,
                         registered_events=registered_events)
    return render_template('dashboard_student.html', title='Student Dashboard')

@auth.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('main.home'))

@main.route('/event/<int:event_id>/register', methods=['POST'])
@login_required
def register_event(event_id):
    if not current_user.is_student():
        flash('Only students can register for events.', 'danger')
        return redirect(url_for('main.dashboard_redirect'))
    
    event = Event.query.get_or_404(event_id)
    
    # Check if already registered
    existing_registration = Registration.query.filter_by(
        student_id=current_user.id,
        event_id=event_id
    ).first()
    
    if existing_registration:
        flash('You are already registered for this event.', 'warning')
    else:
        registration = Registration(
            student_id=current_user.id,
            event_id=event_id
        )
        db.session.add(registration)
        db.session.commit()
        flash('Successfully registered for the event!', 'success')
    
    return redirect(url_for('main.student_dashboard')) 