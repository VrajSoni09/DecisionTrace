from __future__ import annotations

from collections import defaultdict

from app.nlp.semantic_matching import semantic_match


def same_decision(previous: dict[str, object], current: dict[str, object], threshold: float = 0.25) -> bool:
    if previous.get("context") != current.get("context"):
        return False
    previous_option = str(previous.get("option") or "").lower()
    current_option = str(current.get("option") or "").lower()
    if previous_option and current_option and previous_option == current_option:
        return True
    if previous_option and current_option:
        return True
    similarity = semantic_match(str(previous.get("text", "")), str(current.get("text", "")))
    return similarity >= threshold and bool(previous_option or current_option)


def determine_relationship(current: dict[str, object], previous: dict[str, object]) -> str:
    previous_status = str(previous.get("status", "unknown"))
    current_status = str(current.get("status", "unknown"))
    previous_option = str(previous.get("option") or "").lower()
    current_option = str(current.get("option") or "").lower()

    if current_status == "rejected" and previous_status == "proposed":
        return "rejection"
    if current_status == "proposed":
        return "proposal"
    if current_status == "refined" and previous_option == current_option:
        return "refinement"
    if current_status == "ambiguous":
        return "unresolved"
    if previous_status == "approved" and current_status == "approved" and previous_option != current_option:
        return "reversal"
    if previous_option == current_option and current_status == previous_status == "approved":
        return "confirmation"
    return "update"


def detect_reversal_candidates(history: list[dict[str, object]]) -> list[dict[str, object]]:
    groups: defaultdict[str, list[dict[str, object]]] = defaultdict(list)
    for item in history:
        groups[str(item.get("context", "general"))].append(item)

    findings: list[dict[str, object]] = []
    for context, items in groups.items():
        items = sorted(items, key=lambda item: item.get("chronology", 0))
        approved = [item for item in items if item.get("status") == "approved"]
        for current_index, current in enumerate(approved[1:], start=1):
            previous = approved[current_index - 1]
            if not same_decision(previous, current):
                continue
            relationship = determine_relationship(current, previous)
            if relationship == "reversal":
                findings.append(
                    {
                        "context": context,
                        "previous": previous,
                        "current": current,
                        "relationship": relationship,
                        "timeline": items,
                    }
                )
    return findings
