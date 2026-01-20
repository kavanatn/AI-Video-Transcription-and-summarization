
import sys
import os

# Add project root to path
sys.path.insert(0, os.getcwd())

from ai_engine.diarizer import Diarizer
from ai_engine.summarizer import Summarizer

def test_alignment():
    print("Testing Alignment Logic...")
    
    # Mock Whisper Segments with Words
    asr_segments = [
        {
            "start": 0.0, "end": 2.0, "text": "Hello world",
            "words": [
                {"start": 0.0, "end": 0.5, "word": "Hello", "probability": 0.9},
                {"start": 0.6, "end": 1.0, "word": " world", "probability": 0.9}, # gap 0.5-0.6
                {"start": 1.5, "end": 2.0, "word": " here", "probability": 0.9}   # gap 1.0-1.5
            ]
        },
        {
            "start": 2.2, "end": 3.0, "text": " I am speaking.",
            "words": [
                {"start": 2.2, "end": 2.5, "word": " I", "probability": 0.9},
                {"start": 2.5, "end": 2.7, "word": " am", "probability": 0.9},
                {"start": 2.8, "end": 3.0, "word": " speaking.", "probability": 0.9}
            ]
        }
    ]
    
    # Mock Diarization Segments
    # Speaker A: 0.0 - 1.2 (Covers "Hello world")
    # Speaker B: 1.4 - 3.0 (Covers "here" and "I am speaking")
    diarization_segments = [
        {"start": 0.0, "end": 1.2, "speaker": "SPEAKER_01"},
        {"start": 1.4, "end": 3.0, "speaker": "SPEAKER_02"}
    ]
    
    aligned = Diarizer.align_transcript_with_diarization(diarization_segments, asr_segments)
    
    print("Aligned Segments:")
    for seg in aligned:
        print(f"[{seg['start']:.2f} - {seg['end']:.2f}] {seg['speaker']}: {seg['text']}")
        
    # Validation
    # "Hello" (0.0-0.5) -> SPEAKER_01
    # " world" (0.6-1.0) -> SPEAKER_01
    # " here" (1.5-2.0) -> SPEAKER_02 (because midpoint 1.75 is inside 1.4-3.0)
    # " I am speaking." -> SPEAKER_02
    
    assert len(aligned) == 2, f"Expected 2 segments, got {len(aligned)}"
    assert aligned[0]["speaker"] == "SPEAKER_01"
    assert "Hello world" in aligned[0]["text"]
    assert aligned[1]["speaker"] == "SPEAKER_02"
    assert "here I am speaking" in aligned[1]["text"]
    print("Alignment Test Passed!")

def test_summarizer_loading():
    print("\nTesting Summarizer Loading...")
    try:
        s = Summarizer()
        if s.summarizer:
            print("Summarizer loaded successfully.")
            # Test with dummy text
            text = "Artificial intelligence is a branch of computer science that aims to create intelligent machines. " * 10
            summary = s.summarize("test_job", text)
            print("Summary:", summary)
        else:
            print("Summarizer failed to load (maybe no internet or missing libs).")
    except Exception as e:
        print(f"Summarizer crashed: {e}")

if __name__ == "__main__":
    test_alignment()
    # test_summarizer_loading() # Uncomment to test model loading (heavy)
