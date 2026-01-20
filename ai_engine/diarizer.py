import os
import math
import logging
from typing import List, Dict, Any, Optional

import torch
from pyannote.audio import Pipeline

from ai_engine.pipeline import update_job_status

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class Diarizer:
    def __init__(
        self,
        hf_token: Optional[str] = None,
        model_name: str = "pyannote/speaker-diarization-3.1",
        device: Optional[torch.device] = None,
        min_segment_duration: float = 0.6,
        merge_gap: float = 0.35,
    ):
        """
        Args:
            hf_token: Hugging Face token. If None, will attempt to read HF_TOKEN env var.
            model_name: pretrained pyannote pipeline id to load.
            device: torch.device or None (auto-detect GPU if available).
            min_segment_duration: drop/merge segments shorter than this (seconds).
            merge_gap: join adjacent segments with same speaker if gap <= merge_gap (seconds).
        """
        self.hf_token = hf_token or os.getenv("HF_TOKEN")
        if not self.hf_token:
            logger.warning("HF_TOKEN not found. Attempting unauthenticated load (may fail for gated models).")
        self.model_name = model_name

        if device is None:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        else:
            self.device = device

        self.min_segment_duration = float(min_segment_duration)
        self.merge_gap = float(merge_gap)

        # Lazy load pipeline into memory; keep None if load fails so methods can degrade gracefully.
        self.pipeline: Optional[Pipeline] = None
        self._load_pipeline()

    def _load_pipeline(self):
        """Load the pyannote Pipeline once. Keep it cached on success."""
        try:
            logger.info("Loading pyannote pipeline `%s` ...", self.model_name)
            # `use_auth_token` works; newer HF API may expect `token=` — pyannote docs show `use_auth_token` historically.
            # Wrap this in try/except to fail gracefully when token is missing or model gated.
            self.pipeline = Pipeline.from_pretrained(self.model_name, use_auth_token=self.hf_token)
            # Try to move models to chosen device if supported:
            try:
                self.pipeline.to(self.device)
            except Exception:
                # some pipeline implementations handle device internally; ignore if .to() is not supported.
                logger.debug("pipeline.to(device) not supported or failed; relying on default device.")
            logger.info("pyannote pipeline loaded successfully.")
        except Exception as e:
            logger.exception("Failed to load pyannote pipeline: %s", e)
            self.pipeline = None

    @staticmethod
    def _segment_duration(seg: Dict[str, Any]) -> float:
        return seg["end"] - seg["start"]

    @staticmethod
    def _round_time(t: float, ndigits: int = 3) -> float:
        return round(float(t), ndigits)

    def _postprocess_segments(self, raw_segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        - Sort segments by start time.
        - Merge adjacent segments from same speaker when gap <= merge_gap.
        - Drop segments shorter than min_segment_duration (or merge them to neighbor).
        - Normalize speaker labels to stable "Speaker 1", "Speaker 2", ... in order of first appearance.
        """
        if not raw_segments:
            return []

        # Ensure sorted
        segs = sorted(raw_segments, key=lambda s: s["start"])

        # Round times to avoid floating noise
        for s in segs:
            s["start"] = self._round_time(s["start"])
            s["end"] = self._round_time(s["end"])

        merged = []
        for seg in segs:
            if not merged:
                merged.append(seg.copy())
                continue
            last = merged[-1]
            # If same speaker and gap <= merge_gap, merge
            gap = seg["start"] - last["end"]
            if seg["speaker"] == last["speaker"] and gap <= self.merge_gap:
                # extend last segment
                last["end"] = max(last["end"], seg["end"])
            # If gap small and segment is tiny, merge into last (regardless of speaker) to avoid spurious short segments
            elif self._segment_duration(seg) < self.min_segment_duration and gap <= self.merge_gap:
                last["end"] = max(last["end"], seg["end"])
            else:
                merged.append(seg.copy())

        # Remove segments that are still too short by merging into neighbor if possible
        final = []
        for seg in merged:
            dur = self._segment_duration(seg)
            if dur < self.min_segment_duration and final:
                # merge into previous
                prev = final[-1]
                prev["end"] = max(prev["end"], seg["end"])
            else:
                final.append(seg.copy())

        # Stable speaker re-labeling: map original labels to Speaker 1..N by first appearance
        speaker_map = {}
        next_idx = 1
        for seg in final:
            lbl = seg["speaker"]
            if lbl not in speaker_map:
                speaker_map[lbl] = f"Speaker {next_idx}"
                next_idx += 1
            seg["speaker"] = speaker_map[lbl]

        # Ensure times are floats and sorted
        final = sorted(final, key=lambda s: s["start"])
        for s in final:
            s["start"] = float(s["start"])
            s["end"] = float(s["end"])

        return final

    def diarize(self, job_id: str, file_path: str) -> List[Dict[str, Any]]:
        """
        Perform diarization on `file_path`.

        Returns a list of segments: {"start": float, "end": float, "speaker": "Speaker 1", ...}
        On failure returns empty list (graceful degradation). Always updates job status.
        """
        update_job_status(job_id, "processing", 40, "Diarizing speakers...")
        if self.pipeline is None:
            # Attempt to lazy load once more (in case HF_TOKEN set later at runtime)
            self._load_pipeline()
            if self.pipeline is None:
                update_job_status(job_id, "failed", 100, "Diarization pipeline not available.")
                return []

        try:
            # Handle local file path vs URL automatically — pyannote pipeline accepts both in many cases
            logger.info("Running diarization on file: %s", file_path)
            diarization = self.pipeline(file_path)

            # Convert diarization timeline to list of segments
            raw_segments = []
            # diarization.itertracks returns (segment, track, label) or yields segments; we use yield_label=True pattern as before
            for turn, _, speaker in diarization.itertracks(yield_label=True):
                raw_segments.append({
                    "start": float(turn.start),
                    "end": float(turn.end),
                    "speaker": speaker
                })

            if not raw_segments:
                logger.warning("Diarization returned no segments.")
                update_job_status(job_id, "processing", 60, "No speakers detected.")
                return []

            # Post-process: merge, drop tiny segments, stable labels
            processed = self._postprocess_segments(raw_segments)
            update_job_status(job_id, "completed", 100, "Diarization completed.")
            logger.info("Diarization produced %d segments across %d speakers.", len(processed), len({s["speaker"] for s in processed}))
            return processed

        except Exception as e:
            logger.exception("Diarization Error: %s", e)
            update_job_status(job_id, "failed", 100, f"Diarization failed: {str(e)}")
            return []

    # Helper: align diarization segments with ASR transcript segments
    @staticmethod
    def align_transcript_with_diarization(
        diarization_segments: List[Dict[str, Any]],
        asr_segments: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Given:
            diarization_segments: [{"start": s, "end": e, "speaker": "Speaker 1"}, ...]
            asr_segments: [{"start": s, "end": e, "text": "..."}, ...]

        Returns:
            per-speaker list of {"speaker": "Speaker 1", "start": s, "end": e, "text": "..."}
            This simple aligner associates ASR segments with overlapping diarization segments by max overlap.
        """
        aligned = []
        
        # Helper to find speaker at a specific time
        def get_speaker_at(time_point):
            for seg in diarization_segments:
                if seg["start"] <= time_point <= seg["end"]:
                    return seg["speaker"]
            return "Speaker"

        # Flatten all words from ASR segments
        all_words = []
        for asr_seg in asr_segments:
            if "words" in asr_seg and asr_seg["words"]:
                all_words.extend(asr_seg["words"])
            else:
                # Fallback if no words (shouldn't happen with new transcriber)
                # Treat the whole segment as a "word"
                all_words.append({
                    "start": asr_seg["start"],
                    "end": asr_seg["end"],
                    "word": asr_seg["text"],
                    "probability": 1.0
                })

        if not all_words:
            return []

        # Assign speaker to each word
        current_speaker_words = []
        current_speaker = None
        
        for word in all_words:
            midpoint = (word["start"] + word["end"]) / 2
            word_speaker = get_speaker_at(midpoint)
            
            # If it's the very first word
            if current_speaker is None:
                current_speaker = word_speaker
                current_speaker_words.append(word)
                continue
            
            # If speaker changed, push previous segment and start new
            if word_speaker != current_speaker:
                # Close previous
                aligned.append({
                    "speaker": current_speaker,
                    "start": current_speaker_words[0]["start"],
                    "end": current_speaker_words[-1]["end"],
                    "text": "".join([w["word"] for w in current_speaker_words]).strip() 
                    # Note: Whisper words usually include leading space, so simple join works often.
                    # But let's be careful. faster-whisper words might not have spaces?
                    # Faster-whisper words usually capture spacing. If not, we might need " ".join()
                    # Let's inspect faster-whisper output typically. 
                    # Actually, let's use a safe join: if word starts with space, join directly, else add space?
                    # For simplicity/safety with pure text, let's just space join if they look stripped.
                })
                # But faster-whisper words DO preserve spaces usually.
                # Let's re-join carefully.
                
                current_speaker = word_speaker
                current_speaker_words = [word]
            else:
                current_speaker_words.append(word)
        
        # Append last segment
        if current_speaker_words:
             aligned.append({
                "speaker": current_speaker,
                "start": current_speaker_words[0]["start"],
                "end": current_speaker_words[-1]["end"],
                "text": "".join([w["word"] for w in current_speaker_words]).strip()
            })

        return aligned

    # Utility: build per-speaker concatenated transcripts ordered by time
    @staticmethod
    def build_per_speaker_transcripts(aligned_segments: List[Dict[str, Any]]) -> Dict[str, str]:
        per_speaker = {}
        for seg in sorted(aligned_segments, key=lambda x: x["start"]):
            s = seg["speaker"]
            per_speaker.setdefault(s, []).append(seg["text"].strip())
        # join with space and return
        return {k: " ".join([t for t in texts if t]) for k, texts in per_speaker.items()}




# import os
# from pyannote.audio import Pipeline
# import torch
# from config import Config
# from ai_engine.pipeline import update_job_status

# class Diarizer:
#     def __init__(self):
#         self.auth_token = os.getenv("HF_TOKEN")
#         if not self.auth_token:
#             print("Warning: HF_TOKEN not found. Diarization will fail.")
#         self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

#     def diarize(self, job_id, file_path):
#         update_job_status(job_id, "processing", 40, "Diarizing speakers...")
#         try:
#             pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization-3.1", use_auth_token=self.auth_token)
#             pipeline.to(self.device)
            
#             # Run diarization
#             diarization = pipeline(file_path)
            
#             # Convert to list of segments
#             segments = []
#             for turn, _, speaker in diarization.itertracks(yield_label=True):
#                 segments.append({
#                     "start": turn.start,
#                     "end": turn.end,
#                     "speaker": speaker
#                 })
#             return segments
#         except Exception as e:
#             print(f"Diarization Error: {e}")
#             # Return empty or dummy if it fails (graceful degradation)
#             return [] 
