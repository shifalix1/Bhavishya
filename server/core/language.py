from langdetect import detect


def detect_language(text: str) -> str:
    """
    Returns 'hindi', 'english', or 'hinglish'.
    Checks for Devanagari script first. Then uses langdetect library.
    """
    try:
        # Check for Devanagari script characters directly
        # Unicode range U+0900 to U+097F is Hindi Devanagari
        for char in text:
            if "\u0900" <= char <= "\u097f":
                return "hindi"

        # No Devanagari found, use langdetect
        lang = detect(text)

        if lang == "hi":
            return "hindi"
        if lang == "en":
            return "english"

        # Mixed or unrecognised — treat as Hinglish
        return "hinglish"

    except Exception:
        # langdetect fails on very short or single-character inputs
        return "english"
