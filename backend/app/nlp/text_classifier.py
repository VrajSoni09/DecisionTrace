import re
from collections import Counter


TOPIC_TOKENS = {
    "budget": ["budget", "cost", "spend", "finance", "allocation"],
    "timeline": ["timeline", "deadline", "schedule", "launch", "date"],
    "scope": ["scope", "deliverable", "feature", "requirements", "priority"],
    "personnel": ["team", "resource", "hire", "headcount", "staff"],
    "risk": ["risk", "risk mitigation", "issue", "dependency", "blocker"],
}


def classify_text(text: str) -> str:
    lowered = text.lower()
    scores = Counter()
    for topic, tokens in TOPIC_TOKENS.items():
        score = sum(1 for token in tokens if token in lowered)
        if score:
            scores[topic] = score
    if not scores:
        return "general"
    return scores.most_common(1)[0][0]


def fallback_status(sentence: str) -> str:
    text = sentence.lower()
    if re.search(r"\b(approved|approved\s+for|greenlight|move\s+forward|go\s+ahead|confirmed|agreed)\b", text):
        return "finalized"
    if re.search(r"\b(rejected|declined|not\s+approved|won't|will\s+not)\b", text):
        return "rejected"
    if re.search(r"\b(postpone|delay|hold|defer|later)\b", text):
        return "temporary"
    if re.search(r"\b(consider|revisit|reconsider|change\s+mind|revise)\b", text):
        return "reconsidered"
    if re.search(r"\b(proposal|proposed|suggest|recommend)\b", text):
        return "proposed"
    return "unknown"
