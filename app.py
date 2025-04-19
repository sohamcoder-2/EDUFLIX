from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask import flash, redirect, url_for
import os
import re
# Initialize Flask app
app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Configure PostgreSQL database connection
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:admin@localhost/STUDYFLIX'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize SQLAlchemy
db = SQLAlchemy(app)

# ========================
# DATABASE MODELS
# ========================

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    role = db.Column(db.String(50), default='user')  # Default role is 'user'
    
class Video(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    url = db.Column(db.String(300), nullable=False)
    thumbnail_url = db.Column(db.String(300), nullable=True)  
    instructor = db.Column(db.String(100), nullable=False)  # New column for instructor
    duration = db.Column(db.String(50), nullable=True)  # New column for video duration
    views = db.Column(db.Integer, default=0)  # New column for views
    likes = db.Column(db.Integer, default=0)  # New column for likes
    category = db.Column(db.String(100), nullable=False)  # New column for category

class DownloadedVideo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    video_id = db.Column(db.Integer, db.ForeignKey('video.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())

    # Relationships
    user = db.relationship('User', backref='downloaded_videos')
    video = db.relationship('Video', backref='downloads')

class ViewedVideo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    video_id = db.Column(db.Integer, db.ForeignKey('video.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())
    last_played_time = db.Column(db.Float, default=0.0)  # Stores the last played time in seconds
    # Relationships
    user = db.relationship('User', backref='viewed_videos')
    video = db.relationship('Video', backref='viewers')

class LikedVideo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    video_id = db.Column(db.Integer, db.ForeignKey('video.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())

    # Relationships
    user = db.relationship('User', backref='liked_videos')
    video = db.relationship('Video', backref='likers')

class WatchLaterVideo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    video_id = db.Column(db.Integer, db.ForeignKey('video.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())

    # Relationships
    user = db.relationship('User', backref='watch_later_videos')
    video = db.relationship('Video', backref='watch_later_users')
# ========================
# ROUTES
# ========================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/signup_page')
def signup_page():
    return render_template('Signup.html')

@app.route('/signup', methods=['POST'])
def signup():
    name = request.form.get('namesignup')
    username = request.form.get('usernamesignup')
    password = request.form.get('passwordsignup')
    email = request.form.get('emailsignup')

    # Hash the password
    hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

    # Check if the username already exists
    existing_user = User.query.filter_by(username=username).first()
    if existing_user:
        return redirect(url_for('signup_page'))

    # Create a new user and add to the database
    new_user = User(name=name, username=username, password=hashed_password, email=email)
    db.session.add(new_user)
    db.session.commit()

    return redirect(url_for('index'))

@app.route('/login', methods=['POST'])
def login():
    username = request.form['usernamelogin']
    password = request.form['passwordlogin']

    # Query the user by username
    user = User.query.filter_by(username=username).first()

    # Verify the password
    if user and check_password_hash(user.password, password):
        session['user_id'] = user.id
        return jsonify({'message': 'Login successful', 'redirect': url_for('search_page')})
    else:
        return jsonify({'message': 'Invalid username or password'}), 401

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('index'))

@app.route('/search')
def search_page():
    query = request.args.get('q', '')
    category = request.args.get('category', 'All')  # Default to 'All' if no category is specified
    if category == 'All':
        if query:
            videos = Video.query.filter(Video.title.ilike(f'%{query}%')).order_by(func.random()).limit(12).all()
        else:
            videos = Video.query.order_by(func.random()).limit(12).all()
    elif category == 'Popular':
        if query:
            videos = Video.query.filter(Video.title.ilike(f'%{query}%')).order_by(Video.views.desc()).limit(12).all()
        else:
            videos = Video.query.order_by(Video.views.desc()).limit(12).all()
    else:
        if query:
            videos = Video.query.filter(
                Video.title.ilike(f'%{query}%'),
                Video.category == category
            ).limit(12).all()
        else:
            videos = Video.query.filter_by(category=category).limit(12).all()
    # Check if the user is logged in and retrieve the username
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        username = user.name if user else None
        role = user.role if user else None
    else:
        username = None
        role = None
    return render_template('SearchPage.html', videos=videos, query=query, category=category, username=username, role=role)

@app.route('/clear_history', methods=['POST'])
def clear_history():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'You must be logged in to clear history.'}), 401

    user_id = session['user_id']
    print(f"User ID: {user_id}")  # Debug print
    try:
        # Delete all viewed videos for the current user
        ViewedVideo.query.filter_by(user_id=user_id).delete()
        db.session.commit()
        return jsonify({'success': True, 'message': 'History cleared successfully.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Failed to clear history. Please try again.'}), 500
    


@app.route('/video/<int:video_id>')
def video_play(video_id):
    # Fetch the current video details from the database
    video = Video.query.get_or_404(video_id)
    
    # Fetch all videos except the current one
    recommended_videos = Video.query.filter(Video.id != video_id).order_by(func.random()).limit(5).all()
    
    # Check if the user is logged in
    if 'user_id' in session:
        user_id = session['user_id']
        # Check if the user has already viewed this video
        existing_view = ViewedVideo.query.filter_by(user_id=user_id, video_id=video_id).first()
        if not existing_view:
            # Increment the view count for the video
            video.views += 1
            db.session.add(ViewedVideo(user_id=user_id, video_id=video_id))
            db.session.commit()
    
    return render_template('videoplay.html', video=video, recommended_videos=recommended_videos)
@app.route('/download/<int:video_id>', methods=['POST'])
def download_video(video_id):
    if 'user_id' not in session:
        return jsonify({'message': 'You must be logged in to download videos.'}), 401

    user_id = session['user_id']
    video = Video.query.get_or_404(video_id)

    # Check if the video is already downloaded by the user
    existing_download = DownloadedVideo.query.filter_by(user_id=user_id, video_id=video_id).first()
    if existing_download:
        return jsonify({'message': 'Video already downloaded.'}), 400

    # Add the video to the user's downloaded list
    downloaded_video = DownloadedVideo(user_id=user_id, video_id=video_id)
    db.session.add(downloaded_video)
    db.session.commit()

    # Redirect to the downloaded_videos page after successful download
    return jsonify({
        'message': 'Video downloaded successfully.',
        'redirect': url_for('downloaded_videos')  # Redirect to the "Downloaded Videos" page
    })  
@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if 'user_id' not in session:
        return redirect(url_for('index'))  # Redirect to login if not authenticated

    user_id = session['user_id']
    user = User.query.get(user_id)

    if request.method == 'POST':
        # Retrieve form data
        new_username = request.form.get('new_username')
        new_email = request.form.get('new_email')
        new_password = request.form.get('new_password')

        # Validate and update username
        if new_username:
            existing_user = User.query.filter(User.username == new_username, User.id != user_id).first()
            if existing_user:
                flash('Username already exists.', 'error')
                return redirect(url_for('settings'))
            user.username = new_username

        # Validate and update email
        if new_email:
            if not re.match(r"[^@]+@[^@]+\.[^@]+", new_email):
                flash('Invalid email format.', 'error')
                return redirect(url_for('settings'))
            existing_user = User.query.filter(User.email == new_email, User.id != user_id).first()
            if existing_user:
                flash('Email already exists.', 'error')
                return redirect(url_for('settings'))
            user.email = new_email

        # Hash and update password
        if new_password:
            hashed_password = generate_password_hash(new_password, method='pbkdf2:sha256')
            user.password = hashed_password

        # Commit changes to the database
        db.session.commit()

        flash('Account details have been updated.', 'success')
        return redirect(url_for('settings'))

    return render_template('settings.html', user=user)


@app.route('/downloaded_videos')
def downloaded_videos():
    # Fetch the list of downloaded videos for the current user
    if 'user_id' in session:
        user_id = session['user_id']
        downloaded_videos = DownloadedVideo.query.filter_by(user_id=user_id).all()
        return render_template('downloaded_videos.html', videos=downloaded_videos)
    else:
        return redirect(url_for('index'))  # Redirect to login if not authenticated

@app.route('/watch_later_videos')
def watch_later_videos():
    if 'user_id' not in session:
        return redirect(url_for('index'))  # Redirect to login if not authenticated

    user_id = session['user_id']
    # Fetch the list of watch later videos for the current user
    watch_later_videos = WatchLaterVideo.query.filter_by(user_id=user_id).all()
    videos = [wl.video for wl in watch_later_videos]  # Extract the video objects

    return render_template('watch_later_videos.html', watch_later_videos=videos)

@app.route('/clear_watch_later', methods=['POST'])
def clear_watch_later():
    if 'user_id' not in session:
        return jsonify({'message': 'You must be logged in to clear the Watch Later list.'}), 401

    try:
        user_id = session['user_id']
        # Delete all watch later videos for the current user
        WatchLaterVideo.query.filter_by(user_id=user_id).delete()
        db.session.commit()

        return jsonify({'message': 'Watch Later list cleared successfully.'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'An error occurred while clearing the Watch Later list.'}), 500
    
# Configure upload folder
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['ALLOWED_EXTENSIONS'] = {'mp4', 'avi', 'mov'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

from functools import wraps

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('index'))  # Redirect to login if not authenticated
        user = User.query.get(session['user_id'])
        if user.role != 'admin':
            return redirect(url_for('index'))  # Redirect to home page for unauthorized users
        return f(*args, **kwargs)
    return decorated_function

@app.route('/upload_video', methods=['GET', 'POST'])
@admin_required
def upload_video():
    if request.method == 'POST':
        # Check if the post request has the file part
        if 'video' not in request.files:
            return redirect(request.url)
        video = request.files['video']
        thumbnail = request.files['thumbnail']
        if video.filename == '' or thumbnail.filename == '':
            return redirect(request.url)
        if video and allowed_file(video.filename):
            # Secure filenames
            video_filename = secure_filename(video.filename)
            thumbnail_filename = secure_filename(thumbnail.filename)
            # Save files
            video.save(os.path.join(app.config['UPLOAD_FOLDER'], video_filename))
            thumbnail.save(os.path.join(app.config['UPLOAD_FOLDER'], thumbnail_filename))
            # Extract form data
            title = request.form['title']
            instructor = request.form['instructor']
            subject = request.form['subject']
            duration = request.form['duration']  # Get the duration from the form
            description = request.form['description']
            # Save video details to the database
            new_video = Video(
                title=title,
                description=description,
                url=f"/static/uploads/{video_filename}",
                thumbnail_url=f"/static/uploads/{thumbnail_filename}",
                views=0,
                duration=duration,  # Save the duration
                instructor=instructor,
                category=subject  # Assuming subject is the category
            )
            db.session.add(new_video)
            db.session.commit()
            return redirect(url_for('search_page'))
    return render_template('uploadVideo.html')

@app.route('/history')
def history():
    if 'user_id' not in session:
        return redirect(url_for('index'))  # Redirect to login if not authenticated
    user_id = session['user_id']
    # Fetch the list of viewed videos for the current user
    viewed_videos = ViewedVideo.query.filter_by(user_id=user_id).all()
    videos = [vv.video for vv in viewed_videos]  # Extract the video objects
    return render_template('history.html', viewed_videos=viewed_videos)


@app.route('/like/<int:video_id>', methods=['POST'])
def like_video(video_id):
    if 'user_id' not in session:
        return jsonify({'message': 'You must be logged in to like videos.'}), 401

    user_id = session['user_id']
    video = Video.query.get_or_404(video_id)

    # Check if the user has already liked this video
    existing_like = LikedVideo.query.filter_by(user_id=user_id, video_id=video_id).first()
    if existing_like:
        return jsonify({'message': 'You have already liked this video.', 'likes': video.likes}), 400

    # Increment the likes count
    video.likes += 1

    # Record the like in the LikedVideo table
    liked_video = LikedVideo(user_id=user_id, video_id=video_id)
    db.session.add(liked_video)
    db.session.commit()

    return jsonify({
        'message': 'Video liked successfully.',
        'likes': video.likes  # Return the updated likes count
    })
@app.route('/watch_later/<int:video_id>', methods=['POST'])
def watch_later(video_id):
    if 'user_id' not in session:
        return jsonify({'message': 'You must be logged in to add videos to Watch Later.'}), 401

    user_id = session['user_id']
    video = Video.query.get_or_404(video_id)

    # Check if the video is already in the watch later list
    existing_watch_later = WatchLaterVideo.query.filter_by(user_id=user_id, video_id=video_id).first()
    if existing_watch_later:
        return jsonify({'message': 'Video is already in your Watch Later list.', 'status': 'exists'}), 400

    # Add the video to the user's watch later list
    watch_later_video = WatchLaterVideo(user_id=user_id, video_id=video_id)
    db.session.add(watch_later_video)
    db.session.commit()

    return jsonify({
        'message': 'Video added to Watch Later successfully.',
        'status': 'added'
    })
    
# ========================
# MAIN
# ========================

if __name__ == "__main__":
    with app.app_context():
        # Create all database tables if they don't exist
        db.create_all()
    app.run(debug=True)