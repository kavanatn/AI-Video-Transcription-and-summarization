import numpy as np
import requests
from sklearn.cluster import AgglomerativeClustering
from sklearn.neighbors import kneighbors_graph
from sentence_transformers import SentenceTransformer
from ai_engine.pipeline import update_job_status
from config import Config
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Chapterizer:
    def __init__(self, embedding_model="all-MiniLM-L6-v2", ollama_model="llama3.2"):
        """
        Initialize the Chapterizer with embedding and LLM models.
        """
        self.device = "cpu" # Efficient enough for MiniLM
        logger.info(f"Loading SentenceTransformer: {embedding_model}...")
        self.embed_model = SentenceTransformer(embedding_model, device=self.device)
        self.ollama_model = ollama_model
        self.ollama_url = "http://localhost:11434/api/generate"

    def process(self, job_id, segments):
        """
        Main entry point to segment the transcript.
        Args:
            job_id: Current job ID for status updates.
            segments: List of transcript segments with 'text', 'start', 'end'.
        Returns:
            List of chapters: [{"start": float, "title": str, "summary": str}]
        """
        if not segments:
            return []

        update_job_status(job_id, "processing", 82, "Generating embeddings for segmentation...")
        
        # 1. Preprocess: Group sentences into chunks for better context
        # Single sentences are often too short for robust topic detection.
        chunked_data = self._chunk_segments(segments, window_size=3)
        if len(chunked_data) < 2:
            # Too short to segment
            return [{"start": 0.0, "title": "Overview", "summary": "Full Content"}]

        sentences = [c['text'] for c in chunked_data]
        
        # 2. Embed
        embeddings = self.embed_model.encode(sentences, show_progress_bar=False)
        
        # 3. Constrained Clustering
        update_job_status(job_id, "processing", 85, "identifying topic boundaries...")
        num_clusters = self._determine_optimal_clusters(len(sentences))
        logger.info(f"Segmenting into approximately {num_clusters} chapters.")
        
        # Connectivity matrix enforces temporal constraint (only adjacent chunks can merge)
        # This ensures we don't group Intro and Outro together.
        connectivity = kneighbors_graph(
            self._create_temporal_feature_matrix(len(sentences)), 
            n_neighbors=2, 
            mode='connectivity', 
            include_self=True
        )

        clustering = AgglomerativeClustering(
            n_clusters=num_clusters, 
            connectivity=connectivity,
            linkage='ward'
        )
        labels = clustering.fit_predict(embeddings)

        # 4. Post-process labels into chapter ranges
        chapters = self._labels_to_chapters(labels, chunked_data)

        # 5. Generate Titles
        update_job_status(job_id, "processing", 88, "Generating chapter titles...")
        final_chapters = []
        for i, chapter in enumerate(chapters):
            title = self._generate_title(chapter['text'])
            final_chapters.append({
                "start": chapter['start'],
                "end": chapter['end'],
                "title": title,
                "summary": chapter['text'][:200] + "..." # Store preview or full text if needed
            })
            # Progress update per chapter
            prog = 88 + int((i / len(chapters)) * 5)
            update_job_status(job_id, "processing", prog, f"Titled chapter {i+1}/{len(chapters)}")

        return final_chapters

    def _chunk_segments(self, segments, window_size=3):
        """Groups small segments into larger semantic windows."""
        chunks = []
        current_text = []
        current_start = segments[0]['start']
        
        for i, seg in enumerate(segments):
            current_text.append(seg['text'])
            
            if (i + 1) % window_size == 0 or i == len(segments) - 1:
                chunks.append({
                    "text": " ".join(current_text),
                    "start": current_start,
                    "end": seg['end']
                })
                current_text = []
                # Next chunk starts at next segment's start
                if i + 1 < len(segments):
                    current_start = segments[i+1]['start']
        
        return chunks

    def _determine_optimal_clusters(self, num_sentences):
        """Heuristic to guess a good number of chapters."""
        # Rule of thumb: a new chapter every ~2-5 minutes? 
        # Or simply sqrt(n)/2? Let's use a conservative log-based heuristic.
        # For 100 chunks, maybe 5-8 chapters.
        if num_sentences < 5:
            return 1
        return max(2, int(np.sqrt(num_sentences) * 0.6))

    def _create_temporal_feature_matrix(self, n_samples):
        # We need a feature matrix X for kneighbors_graph even if we use precomputed connectivity
        # Just simple reshaping of indices works as a dummy X if needed, 
        # but kneighbors_graph needs actual data to compute neighbors if we don't build graph manually.
        # Actually, for temporal constraint, we can just build a diagonal graph manually.
        # But sklearn's kneighbors_graph is convenient.
        # To strictly enforce 1D temporal chain: neighbor of i is i-1 and i+1.
        X = np.array([[i] for i in range(n_samples)])
        return X

    def _labels_to_chapters(self, labels, chunks):
        """Converts cluster labels back to time ranges."""
        chapters = []
        current_label = labels[0]
        chapter_start = chunks[0]['start']
        chapter_text = [chunks[0]['text']]
        
        for i in range(1, len(labels)):
            if labels[i] != current_label:
                # Chapter boundary
                chapters.append({
                    "start": chapter_start,
                    "end": chunks[i-1]['end'],
                    "text": " ".join(chapter_text)
                })
                # Reset
                current_label = labels[i]
                chapter_start = chunks[i]['start']
                chapter_text = [chunks[i]['text']]
            else:
                chapter_text.append(chunks[i]['text'])
        
        # Add last chapter
        chapters.append({
            "start": chapter_start,
            "end": chunks[-1]['end'],
            "text": " ".join(chapter_text)
        })
        
        return chapters

    def _generate_title(self, text):
        """Uses Ollama to generate a short title."""
        if len(text) < 50:
            return "Untitled Segment"
            
        prompt = f"""
        Generate a very short, engaging title (3-6 words) for the following video segment.
        Do not use quotes. Do not say "Here is a title". Just the title.
        
        Segment: {text[:1500]}...
        
        Title:
        """
        
        try:
            payload = {
                "model": self.ollama_model,
                "prompt": prompt,
                "stream": False,
                "options": {"num_ctx": 2048}
            }
            response = requests.post(self.ollama_url, json=payload, timeout=30)
            if response.status_code == 200:
                title = response.json().get("response", "").strip().replace('"', '')
                return title if title else "Chapter"
        except Exception as e:
            logger.error(f"Title generation failed: {e}")
            
        return "New Chapter"
