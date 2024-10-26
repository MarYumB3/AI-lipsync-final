from flask import Flask, render_template, request, redirect, url_for, flash, session, send_from_directory
from werkzeug.utils import secure_filename
from flask_login import login_required
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
import os
import subprocess
from pyngrok import ngrok
import threading

# Flask app configuration
app = Flask(__name__)
app.config['SECRET_KEY'] = '123456789'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['UPLOAD_FOLDER'] = 'data_user'
ALLOWED_EXTENSIONS = {'mp4', 'mp3'}

wav2lip_temp_dir = os.path.join('temp')
os.makedirs(wav2lip_temp_dir, exist_ok=True)

# Initialize extensions
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

# User model for database
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False, unique=True)
    password = db.Column(db.String(150), nullable=False)

# Helpers
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def process_media(username, video_path, audio_path, start_time, duration):
    output_dir = os.path.join(app.config['UPLOAD_FOLDER'], username, 'trim')
    os.makedirs(output_dir, exist_ok=True)

    # Define output paths
    trimmed_video = os.path.join(output_dir, f"{username}_trimmed_video.mp4")
    trimmed_audio = os.path.join(output_dir, f"{username}_trimmed_audio.mp3")

    # FFmpeg command to trim the video
    ffmpeg_video_cmd = [
        'ffmpeg', '-i', video_path, '-ss', start_time, '-t', duration, '-c', 'copy', trimmed_video, '-y'
    ]
    ffmpeg_audio_cmd = [
        'ffmpeg', '-i', audio_path, '-ss', start_time, '-t', duration, '-c', 'copy', trimmed_audio, '-y'
    ]

    try:
        # Run FFmpeg commands
        subprocess.run(ffmpeg_video_cmd, check=True)
        subprocess.run(ffmpeg_audio_cmd, check=True)
    except subprocess.CalledProcessError as e:
        print("Error processing media:", e)
        return None, None

    return trimmed_video, trimmed_audio

def perform_lip_sync(trimmed_video, trimmed_audio, output_video_path):
    try:
        subprocess.run(
            [
                'python', 'wav2lip/inference.py',
                '--checkpoint_path', 'wav2lip/checkpoints/wav2lip_gan.pth',
                '--face', trimmed_video,
                '--audio', trimmed_audio,
                '--outfile', output_video_path
            ],
            check=True
        )
    except subprocess.CalledProcessError as e:
        print("Error during Wav2Lip process:", e)
        return None
    return output_video_path

# Routes
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = bcrypt.generate_password_hash(request.form['password']).decode('utf-8')
        user = User(username=username, password=password)
        db.session.add(user)
        db.session.commit()
        flash('Account created successfully!', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and bcrypt.check_password_hash(user.password, password):
            session['username'] = username
            flash('Logged in successfully!', 'success')
            return redirect(url_for('home'))
        flash('Login Unsuccessful. Please check username and password', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    session.pop('username', None)
    flash('You have been logged out!', 'info')
    return redirect(url_for('home'))

@app.route('/lip-sync', methods=['GET', 'POST'])
@login_required
def lip_sync():
    if 'username' not in session:
        return redirect(url_for('login'))

    username = session['username']
    user_dir = os.path.join(app.config['UPLOAD_FOLDER'], username, 'temp')
    os.makedirs(user_dir, exist_ok=True)

    orignal_video_dir = os.path.join(app.config['UPLOAD_FOLDER'], username, 'original', 'video')
    orignal_audio_dir = os.path.join(app.config['UPLOAD_FOLDER'], username, 'original', 'audio')
    os.makedirs(orignal_video_dir, exist_ok=True)
    os.makedirs(orignal_audio_dir, exist_ok=True)


    if request.method == 'POST':
        start_time = request.form.get('start_time', '00:00:00')
        duration = request.form.get('duration', '10')

        video_file = request.files.get('video')
        audio_file = request.files.get('audio')

        if video_file and allowed_file(video_file.filename):
            video_path = os.path.join(user_dir, 'temp_uploaded_video.mp4')
            video_file.save(video_path)

            video_original_path = os.path.join(orignal_video_dir, video_file.filename)
            video_file.save(video_original_path)

        else:
            flash('Invalid video file format.', 'danger')
            return redirect(request.url)

        if audio_file and allowed_file(audio_file.filename):
            audio_path = os.path.join(user_dir, 'temp_uploaded_audio.mp3')
            audio_file.save(audio_path)
            
            audio_original_path = os.path.join(orignal_audio_dir, audio_file.filename)
            audio_file.save(audio_original_path)
            
        else:
            flash('Invalid audio file format.', 'danger')
            return redirect(request.url)

        trimmed_video, trimmed_audio = process_media(username, video_path, audio_path, start_time, duration)

        if trimmed_video and trimmed_audio:
            output_dir = os.path.join(app.config['UPLOAD_FOLDER'], username, 'output')
            os.makedirs(output_dir, exist_ok=True)
            output_video_path = os.path.join(output_dir, f"{username}_lip_sync_output.mp4")
            
            # Start lip-sync process in a new thread
            thread = threading.Thread(target=perform_lip_sync, args=(trimmed_video, trimmed_audio, output_video_path))
            thread.start()
            
            # Redirect to process page while lip-sync is processing
            return redirect(url_for('process'))
        else:
            flash('Error during media processing.', 'danger')

    return render_template('lip_sync.html')

@app.route('/process')
@login_required
def process():
    # In the template, you can use JavaScript to periodically check for lip-sync completion
    return render_template('process.html')

@app.route('/check-status')
@login_required
def check_status():
    """Endpoint to check if the output file exists (indicating completion)."""
    username = session.get('username')
    if not username:
        return {'status': 'not_logged_in'}

    output_video_path = os.path.join(app.config['UPLOAD_FOLDER'], username, 'output', f"{username}_lip_sync_output.mp4")
    if os.path.exists(output_video_path):
        return {'status': 'complete'}
    return {'status': 'processing'}

@app.route('/preview')
@login_required
def preview():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    username = session['username']
    output_video_filename = f"{username}_lip_sync_output.mp4"
    output_video_path = os.path.join(app.config['UPLOAD_FOLDER'], username, 'output', output_video_filename)
    
    return render_template('preview.html', video_path=output_video_path, filename=output_video_filename)

@app.route('/download/<path:filename>')
@login_required
def download_video(filename):
    username = session['username']
    output_video_path = os.path.join(app.config['UPLOAD_FOLDER'], username, 'output', filename)
    return send_from_directory(directory=os.path.dirname(output_video_path), path=os.path.basename(output_video_path), as_attachment=True)

# Error handling for 404
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

# Create the database tables if they do not exist
with app.app_context():
    db.create_all()

# Run the app
if __name__ == '__main__':

    # Kill any existing ngrok processes to reset before starting a new tunnel
    subprocess.call(['pkill', 'ngrok'])

    # Set your ngrok authentication token (replace with your actual token)
    NGROK_AUTH_TOKEN = os.getenv("NGROK_AUTH_TOKEN", "2nIgFxwsnemn7rVvBtVlDHOuR09_3C9tjbVFjwo8ujieqaLbr")
    ngrok.set_auth_token(NGROK_AUTH_TOKEN)

    # Define your reserved domain (replace with your actual domain)
    RESERVED_DOMAIN = os.getenv("NGROK_RESERVED_DOMAIN", "present-really-yeti.ngrok-free.app")

    # Open a tunnel with the reserved domain
    ngrok_tunnel = ngrok.connect(addr="5000", host_header="rewrite", domain=RESERVED_DOMAIN)
    app.logger.info("ngrok tunnel \"{}\" -> \"http://127.0.0.1:5000\"".format(ngrok_tunnel.public_url))


    app.run(debug=True)
