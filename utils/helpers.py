import os
import re
from werkzeug.utils import secure_filename
from config import Config

ALLOWED_EXTENSIONS = {'mp3', 'wav', 'mp4', 'mkv', 'mov', 'flv', 'aac', 'm4a'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_upload(file):
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        # Ensure unique filename to prevent overwrites (could append timestamp)
        filepath = os.path.join(Config.UPLOAD_FOLDER, filename)
        file.save(filepath)
        return filepath, filename
    return None, None

def format_timestamp(seconds):
    """Converts seconds to HH:MM:SS,mmm format for SRT."""
    millis = int((seconds - int(seconds)) * 1000)
    seconds = int(seconds)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:02}:{minutes:02}:{seconds:02},{millis:03}"
