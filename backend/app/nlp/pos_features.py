from __future__ import annotations

from collections import Counter


def extract_pos_summary(doc: object) -> dict[str, float | int | list[str]]:
    counts: Counter[str] = Counter()
    tags: list[str] = []
    tokens = getattr(doc, "tokens", doc)
    for token in tokens:
        tag = getattr(token, "pos_", "")
        if tag:
            counts[tag] += 1
            tags.append(tag)

    total = max(sum(counts.values()), 1)
    summary = {tag: round(count / total, 3) for tag, count in counts.items()}
    summary["tag_density"] = round(len(tags) / total, 3)
    summary["tags"] = tags
    return summary
