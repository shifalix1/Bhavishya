import json
import logging
import os
import re

logger = logging.getLogger("bhavishya.careers")

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
    # Additional natural-language phrases that _SEMANTIC_BUCKETS previously missed
    "understand": ["systems thinking", "analytical thinking", "curiosity"],
    "understanding": ["systems thinking", "analytical thinking", "curiosity"],
    "work": ["hands-on problem solving", "practical application", "results-oriented"],
    "works": ["making things work", "results-oriented", "practical application"],
    "figure": ["problem-solving", "analytical thinking", "curiosity"],
    "connect": ["systems thinking", "pattern recognition", "communicative"],
    "connects": ["systems thinking", "pattern recognition", "communicative"],
    "question": ["curiosity", "truth-seeking", "research", "analytical thinking"],
    "questions": ["curiosity", "truth-seeking", "research", "analytical thinking"],
    "imagine": ["creative thinking", "creative problem-solving", "innovation"],
    "imagine ": ["creative thinking", "creative problem-solving", "innovation"],
    "feel": ["empathy", "empathetic", "social awareness"],
    "feelings": ["empathy", "empathetic", "social awareness"],
    "move": ["physical discipline", "hands-on problem solving", "spatial reasoning"],
    "fix": ["troubleshooting", "problem-solving", "technical craftsmanship"],
    "broken": ["troubleshooting", "problem-solving", "technical craftsmanship"],
    "organize": ["systematic", "organized", "methodical", "process-oriented"],
    "organize ": ["systematic", "organized", "methodical"],
    "plan": ["strategic thinking", "systematic", "organized", "long-term thinking"],
    "explore": ["curiosity", "fieldwork", "research", "continuous learning"],
    "connect people": ["communicative", "leadership", "social awareness", "empathy"],
    "make sense": ["simplifying complexity", "teaching", "analytical thinking"],
    "big picture": ["systems thinking", "strategic thinking", "analytical"],
    "details": ["attention to detail", "detail-oriented", "precision"],
    "ideas": ["creative thinking", "innovation", "entrepreneurial mindset"],
    "change": ["social impact", "purpose-driven", "innovation", "advocacy"],
    "fair": ["equity", "access to justice", "social impact", "advocacy"],
    "story": ["storytelling", "narrative building", "communication"],
    "stories": ["storytelling", "narrative building", "communication"],
    "protect": [
        "conservation",
        "environmental awareness",
        "advocacy",
        "service orientation",
    ],
    "build": ["building real things", "technical craftsmanship", "engineering mindset"],
    "create": ["creative", "building something new", "artistic expression"],
    "solve": ["problem-solving", "troubleshooting", "analytical", "solutions-oriented"],
    "measure": ["precision", "quantitative analysis", "evidence-based", "accuracy"],
    "test": ["scientific inquiry", "research methodology", "evidence-based"],
    "lead": ["leadership", "influence", "team leadership", "strategic leadership"],
    "help": ["empathy", "human-centered", "service orientation", "empathetic"],
    "teach": ["teaching", "knowledge sharing", "communication", "mentoring"],
    "discover": ["curiosity", "research", "scientific inquiry", "continuous learning"],
}


_CAREER_CACHE: list | None = None


def load_all_careers() -> list:
    global _CAREER_CACHE
    if _CAREER_CACHE is not None:
        return _CAREER_CACHE
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(BASE_DIR, "data", "careers.json")
    if not os.path.exists(path):
        logger.error(f"careers.json not found at {path}")
        return []
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    _CAREER_CACHE = data if isinstance(data, list) else data.get("careers", [])
    return _CAREER_CACHE


def _expand_to_tags(text: str) -> list[str]:
    words = text.lower().split()
    tags = []
    seen_keys = set()

    for i, word in enumerate(words):
        clean = word.strip(".,!?-\u2014\"'")

        if clean in _SEMANTIC_BUCKETS and clean not in seen_keys:
            tags.extend(_SEMANTIC_BUCKETS[clean])
            seen_keys.add(clean)

        if i + 1 < len(words):
            bigram = clean + " " + words[i + 1].strip(".,!?-\u2014\"'")
            if bigram in _SEMANTIC_BUCKETS and bigram not in seen_keys:
                tags.extend(_SEMANTIC_BUCKETS[bigram])
                seen_keys.add(bigram)

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

    seen = set()
    result = []
    for t in tags:
        if t not in seen:
            seen.add(t)
            result.append(t)
    return result


def _tokenize(text: str) -> set[str]:
    """Return a set of lowercase word tokens from free text."""
    return set(re.findall(r"[a-z]{3,}", text.lower()))


def _score_career_text_pass(career: dict, identity_tokens: set[str]) -> int:
    """
    Second scoring pass: substring match against description_short,
    indian_reality, and honest_reality free-text fields.
    Returns a bonus score (max ~10) so it complements but doesn't
    override strong identity_tag matches.
    """
    corpus_parts = []
    if career.get("description_short"):
        corpus_parts.append(career["description_short"])
    if career.get("indian_reality"):
        ir = career["indian_reality"]
        if isinstance(ir, str):
            corpus_parts.append(ir)
        elif isinstance(ir, dict):
            corpus_parts.extend(str(v) for v in ir.values())
    if career.get("honest_reality"):
        hr = career["honest_reality"]
        if isinstance(hr, str):
            corpus_parts.append(hr)
        elif isinstance(hr, dict):
            corpus_parts.extend(str(v) for v in hr.values())

    if not corpus_parts:
        return 0

    corpus_tokens = _tokenize(" ".join(corpus_parts))
    overlap = identity_tokens & corpus_tokens
    # Cap at 10 to keep it a bonus, not a takeover
    return min(len(overlap), 10)


def _score_career(career: dict, expanded_set: set) -> int:
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
    careers = load_all_careers()
    if not careers:
        return []

    expanded_tags: list[str] = []
    raw_identity_text_parts: list[str] = []

    if identity.get("thinking_style"):
        expanded_tags.extend(_expand_to_tags(identity["thinking_style"]))
        raw_identity_text_parts.append(identity["thinking_style"])
    if identity.get("energy_signature"):
        expanded_tags.extend(_expand_to_tags(identity["energy_signature"]))
        raw_identity_text_parts.append(identity["energy_signature"])
    for strength in identity.get("hidden_strengths", []):
        expanded_tags.extend(_expand_to_tags(strength))
        raw_identity_text_parts.append(strength)
    for value in identity.get("core_values", []):
        expanded_tags.extend(_expand_to_tags(value))
        raw_identity_text_parts.append(value)
    # Also pull from fears and identity summary if present
    if identity.get("core_fear"):
        raw_identity_text_parts.append(identity["core_fear"])
    if identity.get("summary"):
        raw_identity_text_parts.append(identity["summary"])

    if not expanded_tags:
        logger.debug(
            "get_careers_for_identity: no tags expanded - returning top-n by default"
        )
        return _slim_careers(careers[:n])

    expanded_set = set(expanded_tags)

    # Build token set from raw identity text for second pass
    identity_tokens = _tokenize(" ".join(raw_identity_text_parts))

    scored = []
    for c in careers:
        primary_score = _score_career(c, expanded_set)
        # Second pass: only run if primary score is low (avoids inflating
        # already strong matches while rescuing zero-score careers)
        if primary_score < 6:
            text_bonus = _score_career_text_pass(c, identity_tokens)
        else:
            text_bonus = 0
        scored.append((primary_score + text_bonus, c))

    scored.sort(key=lambda x: x[0], reverse=True)

    if scored and scored[0][0] == 0:
        logger.debug(
            f"Expanded tags: {expanded_set} | top career: {scored[0][1].get('name')} | score: 0 - "
            "no tag matches found; check _SEMANTIC_BUCKETS coverage"
        )
    elif scored:
        logger.debug(
            f"Expanded tags (sample): {list(expanded_set)[:5]} | "
            f"top career: {scored[0][1].get('name')} | score: {scored[0][0]}"
        )

    return _slim_careers([c for _, c in scored[:n]])


def _slim_careers(careers: list) -> list:
    keep = {
        "id",
        "name",
        "category",
        "description_short",
        "indian_reality",
        "ai_disruption",
        "honest_reality",
        "parent_frame",
        "identity_tags",  # kept so simulator can do its own reasoning
    }
    return [{k: v for k, v in c.items() if k in keep} for c in careers]
