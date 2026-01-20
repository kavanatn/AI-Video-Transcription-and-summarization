import sys
import os

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)

from ai_engine.translator import Translator

def test_translation():
    print("Test 1: Initializing Translator...")
    try:
        translator = Translator()
    except Exception as e:
        print(f"Failed to load model: {e}")
        return

    text = "Hello world, this is a test for AI summarization."
    print(f"\nOriginal (en): {text}")
    
    # Test En -> Es
    es_text = translator.translate(text, "en", "es")
    print(f"Translated (es): {es_text}")
    
    if not es_text or es_text == text:
        print("Warning: Translation failed or returned original.")
    else:
        print("Translation En->Es successful.")

    # Test Es -> En (Round trip)
    original_back = translator.translate(es_text, "es", "en")
    print(f"Back (en): {original_back}")
    
    # Test Hindi
    hi_text = translator.translate("Hello friend", "en", "hi")
    print(f"Translated (hi): {hi_text}")

if __name__ == "__main__":
    test_translation()
