from faster_whisper import WhisperModel
import torch
from ai_engine.pipeline import update_job_status
import os

class Transcriber:
    def __init__(self, model_size="base"): # Upgraded to base for accuracy, still fast with faster-whisper
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.compute_type = "float16" if self.device == "cuda" else "int8"
        print(f"Loading Faster-Whisper model ({model_size}) on {self.device} with {self.compute_type}...")
        self.model = WhisperModel(model_size, device=self.device, compute_type=self.compute_type)

    def remove_repeated_lines(self, segments):
        """
        Remove consecutive repeated lines in transcription.
        This is especially useful for languages like Japanese and Chinese where Whisper
        sometimes repeats the same line multiple times.
        """
        if not segments or len(segments) <= 1:
            return segments
        
        filtered_segments = [segments[0]]  # Always keep the first segment
        
        for i in range(1, len(segments)):
            current_text = segments[i].get('text', '').strip().lower()
            previous_text = filtered_segments[-1].get('text', '').strip().lower()
            
            # Skip if this segment is identical to the previous one
            if current_text == previous_text and current_text:
                print(f"DEBUG: Skipping repeated line: '{segments[i].get('text', '')[:50]}...'")
                continue
            
            # Also check for very similar lines (>90% similarity)
            if current_text and previous_text:
                # Simple character-based similarity
                similarity = len(set(current_text) & set(previous_text)) / max(len(set(current_text)), len(set(previous_text)))
                if similarity > 0.9 and abs(len(current_text) - len(previous_text)) < 5:
                    print(f"DEBUG: Skipping similar line (similarity: {similarity:.2f})")
                    continue
            
            filtered_segments.append(segments[i])
        
        removed_count = len(segments) - len(filtered_segments)
        if removed_count > 0:
            print(f"DEBUG: Removed {removed_count} repeated/similar segments")
        
        return filtered_segments

    def transcribe(self, job_id, file_path):
        update_job_status(job_id, "processing", 20, "Transcribing audio (Faster-Whisper)...")
        try:
            # Enforce English Language
            segments, info = self.model.transcribe(file_path, beam_size=5, language="en", word_timestamps=True)
            
            # Format segments to match previous structure
            formatted_segments = []
            full_text = []
            
            for segment in segments:
                # Capture words if available
                words = []
                if segment.words:
                    for w in segment.words:
                        words.append({
                            "start": w.start,
                            "end": w.end,
                            "word": w.word,
                            "probability": w.probability
                        })

                formatted_segments.append({
                    "start": segment.start,
                    "end": segment.end,
                    "text": segment.text,
                    "words": words
                })
                full_text.append(segment.text)
            
            # Remove repeated lines (especially for Japanese, Chinese, etc.)
            formatted_segments = self.remove_repeated_lines(formatted_segments)
            
            # Rebuild full_text from deduplicated segments
            full_text = [seg['text'] for seg in formatted_segments]
            
            return {
                "text": " ".join(full_text),
                "segments": formatted_segments
            }
        except Exception as e:
            raise Exception(f"Transcription failed: {e}")

# Singleton (load once) or load on demand? 
# For now, load on demand or global if memory permits. 
# We'll instantiate inside the task for memory safety if concurrency is low.
