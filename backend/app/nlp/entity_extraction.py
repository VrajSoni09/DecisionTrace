from collections import Counter


def extract_entities(doc: object) -> dict[str, list[str] | dict[str, int]]:
    entities: Counter[str] = Counter()
    spans: list[str] = []
    for ent in getattr(doc, "ents", []):
        label = ent.label_
        span = ent.text.strip()
        if span:
            entities[label] += 1
            spans.append(span)
    return {"labels": dict(entities), "spans": spans}
