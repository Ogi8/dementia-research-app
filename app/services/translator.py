"""Google Translate integration for translation (free)."""
from deep_translator import GoogleTranslator
from typing import Optional, Tuple


async def translate_text(text: str, target_language: str, source_language: str = "en") -> Optional[Tuple[str, str]]:
    """
    Translate text using Google Translate (free).
    
    Args:
        text: Text to translate
        target_language: Target language code (en, de, fr, es, it, hr)
        source_language: Source language code (default: en)
        
    Returns:
        Tuple of (translated_text, source_language) or None if error
    """
    # Map language codes to Google Translate format
    lang_map = {
        "en": "en",
        "de": "de",
        "fr": "fr",
        "es": "es",
        "it": "it",
        "hr": "hr"
    }
    
    source = lang_map.get(source_language.lower(), "en")
    target = lang_map.get(target_language.lower(), target_language.lower())
    
    # Don't translate if source and target are the same
    if source == target:
        return (text, source)
    
    try:
        translator = GoogleTranslator(source=source, target=target)
        translated = translator.translate(text)
        return (translated, source)
    except Exception as e:
        print(f"Error translating text: {e}")
        return (text, source)
