from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from bertopic import BERTopic
from ai_engine.pipeline import update_job_status

class Analyzer:
    def __init__(self):
        self.sentiment_analyzer = SentimentIntensityAnalyzer()
        # Loading BERTopic can be heavy, maybe lazy load or lighter model?
        # self.topic_model = BERTopic(language="english") 
        pass

    def analyze_sentiment(self, text):
        """Returns compound sentiment score for text."""
        scores = self.sentiment_analyzer.polarity_scores(text)
        return scores

    def extract_topics(self, job_id, transcript_segments):
        """
        Placeholder for BERTopic.
        Real implementation needs list of docs.
        """
        update_job_status(job_id, "processing", 70, "Analyzing topics...")
        # Mock logic for MVP speed (BERTopic is slow on CPU)
        # In a real run, we'd feed sentences to BERTopic
        return ["General Discussion", "Key Insights"] 
