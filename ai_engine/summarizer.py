import requests
import json
from ai_engine.pipeline import update_job_status
import warnings

# Filter warnings
warnings.filterwarnings("ignore")

from config import Config

class Summarizer:
    def __init__(self, provider=None):
        self.provider = provider or Config.SUMMARIZER_PROVIDER
        print(f"Initialized Summarizer with provider: {self.provider}")

    def summarize(self, job_id, text):
        update_job_status(job_id, "processing", 60, f"Summarizing content ({self.provider})...")
        
        if not text or len(text.strip()) < 50:
            return "Text too short to summarize."

        if self.provider == "gemini":
            return self._summarize_gemini(text)
        else:
            return self._summarize_ollama(text)

    def _summarize_ollama(self, text):
        try:
            model_name = Config.OLLAMA_MODEL
            api_url = Config.OLLAMA_URL
            
            prompt = self._get_prompt(text)
            
            payload = {
                "model": model_name,
                "prompt": prompt,
                "stream": False,
                "options": {"num_ctx": 4096}
            }
            
            response = requests.post(api_url, json=payload, timeout=120)
            response.raise_for_status()
            
            result = response.json()
            return result.get("response", "").strip() or "Ollama returned an empty summary."

        except requests.exceptions.ConnectionError:
            return "Summarization failed: Could not connect to Ollama. Make sure 'ollama serve' is running."
        except Exception as e:
            return f"Summarization failed: {str(e)}"

    def _summarize_gemini(self, text):
        if not Config.GEMINI_API_KEY:
            return "Summarization failed: GEMINI_API_KEY not configured."
            
        try:
            import google.generativeai as genai
            genai.configure(api_key=Config.GEMINI_API_KEY)
            model = genai.GenerativeModel("gemini-1.5-flash")
            
            prompt = self._get_prompt(text)
            response = model.generate_content(prompt)
            return response.text.strip()
            
        except ImportError:
            return "Summarization failed: 'google-generativeai' package not installed."
        except Exception as e:
            return f"Summarization failed: {str(e)}"

    def _get_prompt(self, text):
        return f"""
        You are an expert summarizer. Summarize the following content directly and concisely.
        
        Guidelines:
        - Write in a direct, objective tone.
        - Do NOT use phrases like "The transcript says", "The speaker discusses", or "The text mentions".
        - Focus purely on the Information and Actionable Insights.
        - Organize with clear headings or bullet points if appropriate.
        
        Content:
        {text}
        
        Summary:
        """
