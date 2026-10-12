from __future__ import annotations

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity as sklearn_cosine_similarity


def cosine_similarity(a: list[str], b: list[str]) -> float:
    if not a or not b:
        return 0.0
    matrix = TfidfVectorizer(token_pattern=r"(?u)\b\w[\w-]*\b").fit_transform(
        [" ".join(a), " ".join(b)]
    )
    return float(sklearn_cosine_similarity(matrix[0:1], matrix[1:2])[0, 0])


def semantic_match(text_a: str, text_b: str) -> float:
    tokens_a = [part.lower() for part in text_a.replace("-", " ").split() if part.strip()]
    tokens_b = [part.lower() for part in text_b.replace("-", " ").split() if part.strip()]
    return round(cosine_similarity(tokens_a, tokens_b), 4)
