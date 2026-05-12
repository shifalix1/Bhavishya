from langdetect import detect

# Common Roman-script Hindi/Hinglish words that langdetect cannot identify correctly.
# If 2+ of these appear in the text, it is Hinglish regardless of what langdetect says.
_HINGLISH_MARKERS = {
    "hoon",
    "hun",
    "hai",
    "hain",
    "nahi",
    "nahin",
    "karna",
    "karo",
    "karta",
    "karti",
    "mujhe",
    "muje",
    "chahiye",
    "chahie",
    "lagta",
    "lagti",
    "lagti",
    "yaar",
    "yar",
    "bhai",
    "bhi",
    "aur",
    "toh",
    "tou",
    "par",
    "lekin",
    "matlab",
    "iska",
    "uska",
    "mera",
    "tera",
    "unka",
    "acha",
    "accha",
    "thoda",
    "thora",
    "bilkul",
    "sach",
    "jhoot",
    "pata",
    "samjha",
    "samjhi",
    "bolte",
    "bolti",
    "bolna",
    "dekho",
    "dekh",
    "suno",
    "sun",
    "bata",
    "batao",
    "kya",
    "kyun",
    "kyunki",
    "isliye",
    "waise",
    "aise",
    "kaisa",
    "kaisi",
    "kitna",
    "kitni",
    "bahut",
    "bohot",
    "zyada",
    "kuch",
    "koyi",
    "koi",
    "woh",
    "wo",
    "yeh",
    "ye",
    "inhe",
    "unhe",
    "apna",
    "apni",
    "ghar",
    "school",
    "padhai",
    "padhna",
    "likhna",
    "khelna",
    "banana",
    "bana",
    "banaya",
    "banai",
    "chahta",
    "chahti",
    "sochta",
    "sochti",
    "rehna",
    "reh",
    "hua",
    "hui",
    "hoga",
    "hogi",
    "tha",
    "thi",
}


def detect_language(text: str) -> str:
    """
    Returns 'hindi', 'english', or 'hinglish'.
    Priority: Devanagari check -> Hinglish word list -> langdetect.
    """
    if not text or not text.strip():
        return "hinglish"

    try:
        # Devanagari Unicode range U+0900 to U+097F
        for char in text:
            if "\u0900" <= char <= "\u097f":
                return "hindi"

        # Hinglish word list check - split on whitespace and punctuation
        words = set(w.strip(".,!?\"'()[]{}:;").lower() for w in text.split())
        hinglish_hits = len(words & _HINGLISH_MARKERS)
        if hinglish_hits >= 2:
            return "hinglish"

        # Fall back to langdetect for pure scripts
        lang = detect(text)
        if lang == "hi":
            return "hindi"
        if lang == "en":
            return "english"

        # Anything unrecognised from a student in this app context is Hinglish
        return "hinglish"

    except Exception:
        return "hinglish"
