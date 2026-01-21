import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev_key_secret')
    MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/ai_transcription_db')
    PORT = int(os.getenv('PORT', 5000))
    
    # AI Summarizer Settings
    SUMMARIZER_PROVIDER = os.getenv('SUMMARIZER_PROVIDER', 'ollama') # 'ollama' or 'gemini'
    OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'llama3.2')
    OLLAMA_URL = os.getenv('OLLAMA_URL', 'http://localhost:11434/api/generate')
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
    HF_TOKEN = os.getenv('HF_TOKEN', '')

    UPLOAD_FOLDER = os.path.join(os.getcwd(), 'static', 'uploads')
    MAX_CONTENT_LENGTH = 500 * 1024 * 1024  # 500 MB limit
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
