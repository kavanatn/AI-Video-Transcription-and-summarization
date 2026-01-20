# Deploying AI-Summarize-Transcript

This guide provides instructions for deploying this application to the cloud.

## Prerequisites
- A MongoDB database (recommend [MongoDB Atlas](https://www.mongodb.com/cloud/atlas) for a free managed instance).
- (Optional) A [Google Gemini API Key](https://aistudio.google.com/) if you want to use Gemini instead of a local Ollama instance.

## Deployment Options

### 1. Render / Railway (Docker)
This project includes a `Dockerfile` and is ready for container-based platforms.

1. **Push to GitHub**: Push your code to a GitHub repository.
2. **Create New Web Service**: On Render or Railway, select your repository.
3. **Environment Variables**:
   - `MONGO_URI`: Your MongoDB connection string.
   - `SECRET_KEY`: A random string for Flask sessions.
   - `SUMMARIZER_PROVIDER`: Set to `gemini` (recommended for cloud).
   - `GEMINI_API_KEY`: Your Google Gemini API key.
4. **Deploy**: The platform will automatically build the Docker image and start the service.

### 2. Hugging Face Spaces
Hugging Face is an excellent free option for ML apps.

1. Create a new **Space** on Hugging Face.
2. Select **Docker** as the SDK.
3. Upload your files or sync with GitHub.
4. Set the **Secrets** in the Space settings (same variables as above).

## Local Development (with Docker)
If you want to test the container locally:
```bash
docker build -t ai-transcript .
docker run -p 5000:5000 -e MONGO_URI="your_mongodb_uri" ai-transcript
```

## Notes on Performance
- **Transcription**: The app uses `faster-whisper`, which is optimized but still CPU-intensive. Free tiers might be slow for long videos.
- **Summarization**: Using `gemini` is highly recommended for cloud deployment as it's an external API and doesn't consume server RAM/CPU.
