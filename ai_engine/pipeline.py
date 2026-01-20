import concurrent.futures
import uuid
from datetime import datetime
from db import db_instance

# Global Thread Pool
executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)
jobs = {}  # In-memory job status (for quick polling)

def generate_job_id():
    return str(uuid.uuid4())

from db import db_instance
import os

# Global lazy-loaded models
transcriber = None
diarizer = None
summarizer = None
analyzer = None
chapterizer = None

def start_job(job_id, task_func, *args):
    """Submits a task to the thread pool."""
    jobs[job_id] = {
        "status": "queued",
        "progress": 0,
        "message": "Waiting in queue...",
        "created_at": datetime.now()
    }
    # Update DB
    if db_instance.db is not None:
         db_instance.db.jobs.insert_one({"job_id": job_id, "status": "queued", "created_at": datetime.now()})

    executor.submit(run_job_wrapper, job_id, task_func, *args)

def run_job_wrapper(job_id, task_func, *args):
    """Wrapper to handle status updates and errors."""
    try:
        update_job_status(job_id, "processing", 10, "Starting processing...")
        result = task_func(job_id, *args)
        # Task function should handle final completion status to ensure correct result format
        # update_job_status(job_id, "completed", 100, "Processing complete.", result=result)
    except Exception as e:
        print(f"Job {job_id} failed: {e}")
        update_job_status(job_id, "failed", 0, f"Error: {str(e)}")

def run_full_pipeline(job_id, input_source, is_url=False):
    global transcriber, diarizer, summarizer, analyzer, chapterizer
    
    # Lazy Import inside function to avoid circular dependency
    from ai_engine.downloader import Downloader
    from ai_engine.transcriber import Transcriber
    from ai_engine.diarizer import Diarizer
    from ai_engine.summarizer import Summarizer
    from ai_engine.analyzer import Analyzer
    from ai_engine.chapterizer import Chapterizer

    if transcriber is None: transcriber = Transcriber()
    if diarizer is None: diarizer = Diarizer()
    if summarizer is None: summarizer = Summarizer()
    if analyzer is None: analyzer = Analyzer()
    if chapterizer is None: chapterizer = Chapterizer()

    update_job_status(job_id, "processing", 10, "Initializing pipeline...")
    
    try:
        # 1. Acquire Media
        if is_url:
            update_job_status(job_id, "processing", 15, "Downloading media...")
            file_path, title, error_msg = Downloader.download_url(input_source)
            if not file_path:
                raise Exception(f"Download failed: {error_msg}")
        else:
            file_path = input_source
            title = os.path.basename(file_path)

        # 2. Transcription (Sequential for stability & speed without Diarization)
        update_job_status(job_id, "processing", 30, "Transcribing (Optimized)...")
        whisper_result = transcriber.transcribe(job_id, file_path)
            
        transcript_text = whisper_result['text']
        segments = whisper_result['segments']

        # 3. Diarization (Re-enabled)
        # Note: This increases processing time but is required for Speaker IDs.
        update_job_status(job_id, "processing", 50, "Diarizing (Detecting Speakers)...")
        diarization_segments = diarizer.diarize(job_id, file_path)
        
        # 4. Alignment
        # Use precise word-level alignment
        update_job_status(job_id, "processing", 55, "Aligning transcript with speakers...")
        if diarization_segments:
             # Segments now contain 'words'
             aligned = diarizer.align_transcript_with_diarization(diarization_segments, segments)
             # Replace segments with aligned version which has speaker data
             segments = aligned
        else:
             # Fallback if diarization failed to produce segments
             pass

        # 5. Summarization
        update_job_status(job_id, "processing", 70, "Summarizing...")
        summary = summarizer.summarize(job_id, transcript_text)

        # 6. Analysis
        update_job_status(job_id, "processing", 80, "Analyzing sentiment...")
        sentiment = analyzer.analyze_sentiment(transcript_text)

        # 7. Chaptering
        update_job_status(job_id, "processing", 82, "Segmenting chapters...")
        chapters = chapterizer.process(job_id, segments)

        # 8. Finalize
        result = {
            "title": title,
            "transcript": segments, # List of dicts with start, end, text, speaker
            "full_text": transcript_text,
            "summary": summary,
            "sentiment": sentiment,
            "chapters": chapters,
            "file_path": file_path
        }
        
        # Save to DB
        if db_instance.db is not None:
             db_instance.db.transcripts.insert_one(result)
             # Link job to result
             db_instance.db.jobs.update_one({"job_id": job_id}, {"$set": {"result_id": result["_id"]}})

        update_job_status(job_id, "completed", 100, "Done!", result={"transcript_id": str(result.get("_id", "local"))})
        return result

    except Exception as e:
        print(f"Pipeline Error: {e}")
        update_job_status(job_id, "failed", 0, str(e))
        raise e

def update_job_status(job_id, status, progress, message, result=None):
    """Updates in-memory and MongoDB status."""
    jobs[job_id] = {
        "status": status,
        "progress": progress,
        "message": message,
        "updated_at": datetime.now()
    }
    if result:
        jobs[job_id]["result"] = result
    
    # Update DB
    if db_instance.db is not None:
        update_data = {
            "status": status,
            "progress": progress,
            "message": message,
            "updated_at": datetime.now()
        }
        if result:
            update_data["result"] = result
        db_instance.db.jobs.update_one({"job_id": job_id}, {"$set": update_data})

def get_job_status(job_id):
    # Check memory first
    if job_id in jobs:
        return jobs[job_id]
    
    # Fallback to DB
    if db_instance.db is not None:
        job = db_instance.db.jobs.find_one({"job_id": job_id})
        if job:
            # Convert datetime to string or handle it? JSON serialization might fail on datetime objects in app.py
            # But app.py uses jsonify which fails on datetime?
            # Let's ensure we return compatiable dict.
            # jobs dict uses datetime objects? No, `app.py` jsonify handles standard types. 
            # We should probably format datetime here or remove it if not needed for status poll.
            return {
                "status": job.get("status"),
                "progress": job.get("progress"),
                "message": job.get("message"),
                "result": job.get("result") # link to result
            }
            
    return {"status": "unknown", "message": "Job not found."}
