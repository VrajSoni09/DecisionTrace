import re
from collections.abc import Iterable


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def split_sentences(text: str) -> list[str]:
    chunks = re.split(r"(?<=[.!?])\s+", normalize_text(text))
    return [chunk.strip() for chunk in chunks if chunk.strip()]


def flatten(items: Iterable[str]) -> list[str]:
    return [item for sub in items for item in (sub if isinstance(sub, list) else [sub])]
