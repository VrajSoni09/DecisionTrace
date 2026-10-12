import re
from collections.abc import Iterable


STATUS_PATTERNS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("approved", ("approved", "selected", "chosen", "greenlighted", "agreed on", "confirmed")),
    ("rejected", ("rejected", "declined", "not approved", "ruled out")),
    ("proposed", ("proposed", "suggested", "recommended", "considering", "considered")),
    ("refined", ("configuration", "configured", "settings", "modified", "updated", "changed")),
    ("ambiguous", ("discussed", "debated", "no final choice", "unclear")),
)

OPTION_PATTERN = re.compile(
    r"\b(postgresql|postgres|mongodb|mysql|sqlite|redis|kafka|rabbitmq|"
    r"azure\s+sql|sql\s+server|[a-z][a-z0-9_-]{2,})\b",
    re.IGNORECASE,
)
KNOWN_OPTIONS = {"postgresql", "postgres", "mongodb", "mysql", "sqlite", "redis", "kafka", "rabbitmq"}
CONTEXT_TERMS = (
    "database",
    "technology",
    "platform",
    "storage",
    "cache",
    "queue",
    "budget",
    "timeline",
    "scope",
    "vendor",
)
STOPWORDS = {
    "the", "team", "was", "were", "is", "are", "as", "an", "a", "for", "to",
    "and", "or", "of", "on", "in", "with", "this", "that", "it", "we",
}
NON_OPTIONS = {
    "approved", "selected", "chosen", "suggested", "proposed", "configuration",
    "confirmed", "rejected", "instead", "alternative", "again", "changed",
}


def score_decision_clause(sentence: str) -> float:
    lowered = sentence.lower()
    score = 0.0
    if any(pattern in lowered for _, patterns in STATUS_PATTERNS for pattern in patterns):
        score += 0.65
    if any(term in lowered for term in CONTEXT_TERMS):
        score += 0.15
    if OPTION_PATTERN.search(sentence):
        score += 0.15
    if re.search(r"\b(we|team|committee|board|leadership)\b", lowered):
        score += 0.05
    return round(min(score, 1.0), 3)


def _status(sentence: str) -> str:
    lowered = sentence.lower()
    if re.search(r"\b(if|unless|whether)\b[^.?!]*\b(approved|selected|chosen)\b", lowered):
        return "ambiguous"
    if re.search(r"\b(not|never|wasn't|isn't|wouldn't)\s+(?:explicitly\s+)?approved\b", lowered):
        return "ambiguous"
    for status, patterns in STATUS_PATTERNS:
        if any(pattern in lowered for pattern in patterns):
            return status
    return "unknown"


def _option(sentence: str) -> str | None:
    lowered = sentence.lower()
    matches = [match.group(0).strip() for match in OPTION_PATTERN.finditer(sentence)]
    for candidate in matches:
        if candidate.lower() in KNOWN_OPTIONS:
            return candidate
    for candidate in matches:
        normalized = candidate.lower()
        if normalized not in STOPWORDS and normalized not in CONTEXT_TERMS and normalized not in NON_OPTIONS:
            if normalized in lowered:
                return candidate
    return None


def _context(sentence: str, option: str | None) -> str:
    lowered = sentence.lower()
    terms = [term for term in CONTEXT_TERMS if term in lowered]
    if option and re.search(r"\b(config|configuration|settings?)\b", lowered):
        terms.append("database")
    if option and re.search(r"\b(instead|alternative|rather)\b", lowered):
        terms.append("database")
    project_match = re.search(r"\b(?:for|on)\s+([a-z][a-z0-9_-]*)", lowered)
    if project_match and project_match.group(1) not in {"the", "an", "a"}:
        terms.append(f"project:{project_match.group(1)}")
    if option:
        lowered = lowered.replace(option.lower(), " ")
    return " ".join(sorted(set(terms))) or "general"


def _subject(sentence: str) -> str | None:
    match = re.match(r"\s*(?:the\s+)?([A-Z][\w-]*)\s+(?:was|were|is|are)\b", sentence)
    if match:
        return match.group(1)
    return None


def extract_decision_candidates(sentences: Iterable[str]) -> list[dict[str, object]]:
    candidates: list[dict[str, object]] = []
    for idx, sentence in enumerate(sentences):
        score = score_decision_clause(sentence)
        if score < 0.7:
            continue
        option = _option(sentence)
        candidates.append(
            {
                "index": idx,
                "text": sentence,
                "score": score,
                "status": _status(sentence),
                "option": option,
                "subject": _subject(sentence),
                "context": _context(sentence, option),
            }
        )
    return candidates
