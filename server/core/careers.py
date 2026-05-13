import json
import os

# Semantic bucket map: bridges Darpan natural language -> careers.json identity_tag vocabulary.
# Keys are words Darpan commonly outputs. Values are the EXACT strings that appear in
# careers.json identity_tags - verified against actual tag vocabulary (129 careers).
_SEMANTIC_BUCKETS: dict[str, list[str]] = {
    # Analytical cluster
    "analytical": [
        "analytical",
        "analytical thinking",
        "analytically rigorous",
        "critical thinking",
    ],
    "analyzing": [
        "analytical",
        "analytical thinking",
        "data analysis",
        "research methodology",
    ],
    "logical": ["logical thinking", "analytical", "systematic", "methodical"],
    "systems": ["systems thinking", "analytical", "systematic", "analytical rigor"],
    "systematic": ["systematic", "systems thinking", "methodical", "organized"],
    "abstract": ["abstract reasoning", "analytical thinking", "critical thinking"],
    "math": ["mathematical reasoning", "analytical", "quantitative analysis"],
    "numbers": ["quantitative analysis", "mathematical reasoning", "analytical"],
    "data": ["data analysis", "analytical", "research methodology"],
    "research": ["research", "research methodology", "evidence-based", "analytical"],
    "science": ["scientific inquiry", "research methodology", "analytical rigor"],
    "thinking": ["critical thinking", "analytical thinking", "systems thinking"],
    # Creative cluster
    "creative": [
        "creative",
        "creative thinking",
        "creative problem-solving",
        "artistic expression",
    ],
    "artistic": [
        "artistic",
        "artistic expression",
        "aesthetic-driven",
        "aesthetically sensitive",
    ],
    "drawing": [
        "visual thinking",
        "artistic expression",
        "aesthetic-driven",
        "creative",
    ],
    "design": [
        "design thinking",
        "aesthetic-driven",
        "visual thinking",
        "creative problem-solving",
    ],
    "aesthetic": [
        "aesthetic-driven",
        "aesthetically sensitive",
        "visual thinking",
        "artistic expression",
    ],
    "storytelling": [
        "storytelling",
        "narrative building",
        "communication",
        "creative writing",
    ],
    "writing": ["writing", "analytical writing", "communication", "storytelling"],
    "music": ["musical", "acoustic understanding", "artistic expression", "creative"],
    "performing": [
        "performance",
        "artistic expression",
        "public speaking",
        "communication",
    ],
    "art": ["artistic expression", "aesthetic-driven", "creative", "visual thinking"],
    # Visual / spatial / building cluster
    "visual": [
        "visual thinking",
        "3d visualization",
        "spatial awareness",
        "design thinking",
    ],
    "spatial": [
        "spatial reasoning",
        "3d spatial thinking",
        "spatial awareness",
        "visual thinking",
    ],
    "building": [
        "building real things",
        "building physical things",
        "technical craftsmanship",
        "building something new",
    ],
    "making": [
        "building real things",
        "technical craftsmanship",
        "hands-on problem solving",
        "making things work",
    ],
    "doing": [
        "hands-on problem solving",
        "building real things",
        "technical craftsmanship",
        "practical application",
    ],
    "hands": [
        "hands-on problem solving",
        "technical craftsmanship",
        "building physical things",
    ],
    "maker": [
        "building real things",
        "technical craftsmanship",
        "hands-on problem solving",
    ],
    "builder": [
        "building real things",
        "technical craftsmanship",
        "engineering mindset",
    ],
    "coding": [
        "programming",
        "software development",
        "technical craftsmanship",
        "logical thinking",
    ],
    "programming": [
        "programming",
        "software development",
        "logical thinking",
        "systems thinking",
    ],
    "technical": [
        "technical craftsmanship",
        "engineering mindset",
        "systems thinking",
        "analytical",
    ],
    "engineering": [
        "engineering mindset",
        "systems thinking",
        "technical craftsmanship",
        "building real things",
    ],
    "output": ["building real things", "making things work", "results-oriented"],
    "experiment": [
        "scientific inquiry",
        "hands-on problem solving",
        "curiosity",
        "research",
    ],
    "practical": [
        "hands-on problem solving",
        "practical application",
        "technical craftsmanship",
    ],
    # Pattern / observation / detail cluster
    "pattern": ["pattern recognition", "analytical", "data analysis", "observational"],
    "noticing": [
        "pattern recognition",
        "observational",
        "attention to detail",
        "analytical",
    ],
    "observing": ["observational", "pattern recognition", "attention to detail"],
    "detail": ["attention to detail", "detail-oriented", "precision", "accuracy"],
    "precision": ["precision", "accuracy", "attention to detail", "detail-oriented"],
    "accuracy": ["accuracy", "precision", "attention to detail", "evidence-based"],
    "observation": ["observational", "pattern recognition", "attention to detail"],
    # Communication / social cluster
    "communication": [
        "communication",
        "communicative",
        "verbal communication",
        "public speaking",
    ],
    "teaching": ["teaching", "mentoring", "communication", "knowledge sharing"],
    "explaining": [
        "communication",
        "teaching",
        "simplifying complexity",
        "knowledge sharing",
    ],
    "helping": ["empathy", "empathetic", "human-centered", "service orientation"],
    "empathy": ["empathy", "empathetic", "user-first thinking", "social awareness"],
    "social": ["social awareness", "communicative", "empathetic", "community focus"],
    "leadership": [
        "leadership",
        "team leadership",
        "strategic leadership",
        "influence",
    ],
    "managing": ["management", "leadership", "team leadership", "organized"],
    "teamwork": ["collaboration", "team player", "communicative", "empathetic"],
    "collaboration": ["collaboration", "team player", "communicative"],
    "speaking": ["public speaking", "communication", "verbal communication"],
    # Problem solving cluster
    "solving": [
        "problem-solving",
        "troubleshooting",
        "solutions-oriented",
        "analytical",
    ],
    "problems": [
        "problem-solving",
        "troubleshooting",
        "analytical",
        "critical thinking",
    ],
    "challenge": ["problem-solving", "resilience", "persistence", "achievement-driven"],
    "fixing": ["troubleshooting", "problem-solving", "technical craftsmanship"],
    "process": ["systematic", "methodical", "process-oriented", "organized"],
    # Independence / entrepreneurial cluster
    "independent": [
        "self-directed",
        "entrepreneurial mindset",
        "autonomous",
        "deep focus",
        "initiative",
    ],
    "entrepreneurial": [
        "entrepreneurial mindset",
        "risk-taking",
        "innovation",
        "self-directed",
    ],
    "innovation": ["innovation", "creative problem-solving", "entrepreneurial mindset"],
    "alone": ["self-directed", "autonomous", "deep focus", "research"],
    # Values cluster
    "impact": [
        "social impact",
        "service orientation",
        "community focus",
        "purpose-driven",
    ],
    "nature": ["environmental awareness", "fieldwork", "biodiversity", "conservation"],
    "environment": ["environmental awareness", "conservation", "sustainability"],
    "justice": ["access to justice", "equity", "advocacy", "social impact"],
    "truth": ["truth-seeking", "evidence-based", "integrity", "analytical rigor"],
    "curiosity": [
        "curiosity",
        "continuous learning",
        "research",
        "analytical thinking",
    ],
    "curious": ["curiosity", "continuous learning", "research", "analytical thinking"],
    "learning": ["continuous learning", "curiosity", "research methodology"],
    "competitive": ["competitive", "achievement-driven", "resilience"],
    "sports": ["athletic excellence", "competitive", "teamwork", "physical discipline"],
    "physical": [
        "physical discipline",
        "athletic excellence",
        "hands-on problem solving",
    ],
    # Finance / business cluster
    "finance": ["financial analysis", "quantitative analysis", "business acumen"],
    "business": [
        "business acumen",
        "entrepreneurial mindset",
        "management",
        "strategic thinking",
    ],
    "money": ["financial analysis", "quantitative analysis", "business acumen"],
    "strategy": ["strategic thinking", "business acumen", "analytical thinking"],
    # Energy signature patterns
    "audience": ["public speaking", "performance", "communication", "teaching"],
    "constraint": ["creative problem-solving", "design thinking", "problem-solving"],
    "recognition": ["achievement-driven", "competitive", "leadership"],
    "team": ["collaboration", "team player", "communicative"],
    "result": ["results-oriented", "achievement-driven", "problem-solving"],
    "visible": ["building real things", "making things work", "portfolio-driven"],
    "persistence": ["persistence", "resilience", "achievement-driven", "deep focus"],
    "persistent": ["persistence", "resilience", "achievement-driven"],
    "patient": ["patience", "long-term thinking", "deep focus", "methodical"],
    "autonomy": ["autonomous", "self-directed", "independent thinking"],
}


_CAREER_CACHE: list | None = None


def load_all_careers() -> list:
    global _CAREER_CACHE
    if _CAREER_CACHE is not None:
        return _CAREER_CACHE
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(BASE_DIR, "data", "careers.json")
    if not os.path.exists(path):
        print(f"Error: {path} not found!")
        return []
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    _CAREER_CACHE = data if isinstance(data, list) else data.get("careers", [])
    return _CAREER_CACHE


def _expand_to_tags(text: str) -> list[str]:
    """
    Convert a Darpan natural language phrase into careers.json identity_tag vocabulary.
    Checks single words AND bigrams. Falls back to stem partial match.
    Returns deduplicated list of exact target tag strings from careers.json.
    """
    words = text.lower().split()
    tags = []
    seen_keys = set()

    for i, word in enumerate(words):
        clean = word.strip(".,!?-\u2014\"'")

        # Single word lookup
        if clean in _SEMANTIC_BUCKETS and clean not in seen_keys:
            tags.extend(_SEMANTIC_BUCKETS[clean])
            seen_keys.add(clean)

        # Bigram lookup (e.g. "systems thinking", "pattern recognition")
        if i + 1 < len(words):
            bigram = clean + " " + words[i + 1].strip(".,!?-\u2014\"'")
            if bigram in _SEMANTIC_BUCKETS and bigram not in seen_keys:
                tags.extend(_SEMANTIC_BUCKETS[bigram])
                seen_keys.add(bigram)

        # Stem partial match fallback
        if clean not in seen_keys:
            for key in _SEMANTIC_BUCKETS:
                if (
                    len(key) > 4
                    and (key in clean or clean in key)
                    and key not in seen_keys
                ):
                    tags.extend(_SEMANTIC_BUCKETS[key])
                    seen_keys.add(key)
                    break

    # Deduplicate preserving order
    seen = set()
    result = []
    for t in tags:
        if t not in seen:
            seen.add(t)
            result.append(t)
    return result


def _score_career(career: dict, expanded_set: set) -> int:
    """
    Score a career against the student's expanded tag set.
    Exact match: 3pts. Partial (substring): 1pt.
    Multi-word tags like 'visual thinking' and 'pattern recognition' get full
    credit because _expand_to_tags now outputs the exact careers.json strings.
    """
    career_tags = career.get("identity_tags", {})
    career_kw = set(
        k.lower()
        for k in (
            career_tags.get("personality", [])
            + career_tags.get("values", [])
            + career_tags.get("strengths", [])
        )
    )

    score = 0
    for tag in expanded_set:
        if tag in career_kw:
            score += 3
        else:
            for ck in career_kw:
                if len(tag) > 4 and (tag in ck or ck in tag):
                    score += 1
                    break
    return score


def get_careers_for_identity(identity: dict, n: int = 5) -> list:
    """
    Returns n most relevant careers for a student's identity.
    Uses corrected bucket vocabulary aligned to careers.json actual tag strings.
    """
    careers = load_all_careers()
    if not careers:
        return []

    expanded_tags: list[str] = []
    if identity.get("thinking_style"):
        expanded_tags.extend(_expand_to_tags(identity["thinking_style"]))
    if identity.get("energy_signature"):
        expanded_tags.extend(_expand_to_tags(identity["energy_signature"]))
    for strength in identity.get("hidden_strengths", []):
        expanded_tags.extend(_expand_to_tags(strength))
    for value in identity.get("core_values", []):
        expanded_tags.extend(_expand_to_tags(value))

    if not expanded_tags:
        return _slim_careers(careers[:n])

    expanded_set = set(expanded_tags)
    scored = [(_score_career(c, expanded_set), c) for c in careers]
    scored.sort(key=lambda x: x[0], reverse=True)
    return _slim_careers([c for _, c in scored[:n]])


def _slim_careers(careers: list) -> list:
    """
    Returns only what the simulator and Margdarshak actually need.
    Keeps salary inside indian_reality, honest_reality, parent_frame, ai_disruption.
    Drops pathways/certifications to save tokens.
    """
    keep = {
        "id",
        "name",
        "category",
        "description_short",
        "indian_reality",
        "ai_disruption",
        "honest_reality",
        "parent_frame",
    }
    return [{k: v for k, v in c.items() if k in keep} for c in careers]
