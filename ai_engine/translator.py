import torch
from transformers import M2M100ForConditionalGeneration, M2M100Tokenizer
import warnings

# Suppress warnings
warnings.filterwarnings("ignore")

# Language code mapping: Whisper codes -> M2M-100 codes
# M2M-100 uses standard ISO codes, but some normalization is needed
LANGUAGE_CODE_MAP = {
    # Hindi/Urdu are phonetically similar, Whisper may confuse them
    # Both map to Hindi for M2M-100 as it's more widely supported
    'ur': 'hi',  # Urdu -> Hindi (they're mutually intelligible)
    'hi': 'hi',  # Hindi -> Hindi
    # Add other common mappings as needed
    'en': 'en',
    'es': 'es',
    'fr': 'fr',
    'de': 'de',
    'zh': 'zh',
    'ja': 'ja',
    'ko': 'ko',
    'ar': 'ar',
    'ru': 'ru',
    'pt': 'pt',
    'it': 'it',
    'nl': 'nl',
    'pl': 'pl',
    'tr': 'tr',
    'vi': 'vi',
    'th': 'th',
    'id': 'id',
    'ms': 'ms',
    'fa': 'fa',
    'bn': 'bn',
    'ta': 'ta',
    'te': 'te',
    'mr': 'mr',
    'gu': 'gu',
    'kn': 'kn',  # Kannada
}

# Supported languages for summary translation
SUPPORTED_LANGUAGES = {
    # International
    'en': 'English',
    'es': 'Spanish',
    'ja': 'Japanese',
    
    # Indian Languages
    'hi': 'Hindi',
    'ta': 'Tamil',
    'te': 'Telugu',
    'kn': 'Kannada',
    'ml': 'Malayalam'
}

class Translator:
    def __init__(self, model_name="facebook/m2m100_418M"):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Loading M2M-100 Translation Model ({model_name}) on {self.device}...")
        
        try:
            self.tokenizer = M2M100Tokenizer.from_pretrained(model_name)
            self.model = M2M100ForConditionalGeneration.from_pretrained(model_name).to(self.device)
            self.model.eval()
            print(f"Supported summary languages: {', '.join(SUPPORTED_LANGUAGES.values())}")
        except Exception as e:
            print(f"Failed to load M2M-100 model: {e}")
            raise e

    def normalize_language_code(self, lang_code):
        """Normalize Whisper language codes to M2M-100 compatible codes."""
        normalized = LANGUAGE_CODE_MAP.get(lang_code, lang_code)
        if normalized != lang_code:
            print(f"DEBUG: Normalized language code '{lang_code}' -> '{normalized}'")
        return normalized

    def validate_language(self, lang_code):
        """
        Validate if language is supported for summary translation.
        Returns normalized language code or raises ValueError.
        """
        normalized = self.normalize_language_code(lang_code)
        if normalized not in SUPPORTED_LANGUAGES:
            supported_list = ', '.join(SUPPORTED_LANGUAGES.values())
            raise ValueError(
                f"Language '{lang_code}' is not supported for summary translation. "
                f"Supported languages: {supported_list}"
            )
        return normalized

    def translate(self, text, src_lang, target_lang):
        """
        Translates text from source language to target language.
        Args:
            text (str): Input text.
            src_lang (str): Source language code (e.g., 'en', 'hi', 'es', 'ur').
            target_lang (str): Target language code.
        Returns:
            str: Translated text.
        """
        if not text or not text.strip():
            return ""
        
        # Normalize language codes
        src_lang_normalized = self.normalize_language_code(src_lang)
        target_lang_normalized = self.normalize_language_code(target_lang)
        
        print(f"DEBUG: Translation request: {src_lang} ({src_lang_normalized}) -> {target_lang} ({target_lang_normalized})")
        
        # Don't translate if same language after normalization
        if src_lang_normalized == target_lang_normalized:
            print(f"DEBUG: Source and target languages are the same after normalization, skipping translation")
            return text

        try:
            # Validate language codes are supported by M2M-100
            try:
                src_lang_id = self.tokenizer.get_lang_id(src_lang_normalized)
                target_lang_id = self.tokenizer.get_lang_id(target_lang_normalized)
            except Exception as lang_error:
                print(f"WARNING: Unsupported language code: {lang_error}")
                print(f"Falling back to original text (no translation)")
                return text
            
            # Set source language
            self.tokenizer.src_lang = src_lang_normalized
            encoded = self.tokenizer(text, return_tensors="pt", truncation=True, max_length=512).to(self.device)
            
            # Generate translation
            # forced_bos_token_id is crucial for M2M100 to know target language
            generated_tokens = self.model.generate(
                **encoded, 
                forced_bos_token_id=target_lang_id,
                max_length=512
            )
            
            translation = self.tokenizer.batch_decode(generated_tokens, skip_special_tokens=True)[0]
            print(f"DEBUG: Translation successful, output length: {len(translation)}")
            return translation
            
        except Exception as e:
            print(f"Translation Error ({src_lang_normalized}->{target_lang_normalized}): {type(e).__name__}: {e}")
            # Fallback: return original text to avoid pipeline crash
            return text
