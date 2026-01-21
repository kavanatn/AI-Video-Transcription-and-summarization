

# AI Transcription, Diarization & Summarization Tool

A local, privacy-focused web application that uses advanced AI models to transcribe, differentiate speakers (diarization), and summarize audio/video content.

## 📋 Prerequisites

Before setting up the project, ensure you have the following installed on your Windows system:

1.  **Python 3.10 or 3.11** (recommended)
    - [Download Python](https://www.python.org/downloads/)
    - **Check "Add Python to PATH"** during installation.
2.  **Microsoft Visual C++ Build Tools** (Required for some AI libraries)
    - [Download Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)
    - Install "Desktop development with C++" workload.
3.  **FFmpeg** (Required for audio processing)
    - [Download FFmpeg](https://ffmpeg.org/download.html)
    - Extract and add the `bin` folder to your **System PATH**.
    - Verify by opening CMD and typing: `ffmpeg -version`
4.  **MongoDB Community Server**
    - [Download MongoDB](https://www.mongodb.com/try/download/community)
    - Install as a Service.

## 🛠️ Installation Guide

1.  **Clone the Project**

    ```powershell
    cd "path\to\AI-summerizztion"
    ```

2.  **Create Virtual Environment**

    ```powershell
    python -m venv venv
    .\venv\Scripts\activate
    ```

3.  **Install Dependencies**

    ```powershell
    pip install -r requirements.txt
    ```

4.  **Enable GPU Support (Recommended)**
    To make transcription 10x-50x faster (requires NVIDIA GPU):

    ```powershell
    # Uninstall CPU torch first
    pip uninstall torch torchvision torchaudio -y

    # Install CUDA 11.8 version
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
    ```

5.  **Setup Authentication (Important)**

    **A. HuggingFace Token (For Diarization)**

    1.  Get a token from [Hugging Face](https://huggingface.co/settings/tokens).
    2.  Accept user agreements for `pyannote/speaker-diarization-3.1` and `pyannote/segmentation-3.0`.
    3.  Create a `.env` file in the root directory:
        ```env
        HF_TOKEN=hf_yourtokenhere...
        ```

    **B. YouTube Cookies (For Downloads)**
    _Fixes "Sign in to confirm you’re not a bot" errors._

    1.  Install "Get cookies.txt LOCALLY" extension on Chrome/Firefox.
    2.  Go to YouTube (logged in).
    3.  Export cookies and save the file as `cookies.txt` in this project folder (`d:\VS Code\Python\AI-summerizztion\cookies.txt`).

## 🚀 How to Run

1.  **Activate Environment** (if not active)

    ```powershell
    .\venv\Scripts\activate
    ```

2.  **Start the App**

    ```powershell
    python app.py
    ```

3.  **Open in Browser**
    - Go to: http://127.0.0.1:5000

_Note: The first run will download models (approx 2GB). Please be patient._

## ⚠️ Common Issues

- **`DownloadError: Sign in to confirm...`**:
  - Missing `cookies.txt`. See Step 5B above.
- **`ModuleNotFoundError`**:
  - Ensure `venv` is activated.
- **`torchcodec` Warning**:
  - You can safely ignore "torchcodec is not installed correctly" warnings if the app starts.
