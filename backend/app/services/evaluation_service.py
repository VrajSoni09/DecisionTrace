import json
from pathlib import Path

from app.services.decision_service import DecisionService


class EvaluationService:
    def __init__(self):
        self.dataset_path = Path(__file__).resolve().parents[3] / "data" / "labeled" / "decision_examples.json"
        self.service = DecisionService(match_threshold=0.42)

    def load_dataset(self) -> list[dict[str, object]]:
        with self.dataset_path.open("r", encoding="utf-8") as file:
            payload = json.load(file)
        return payload.get("examples", [])

    def run(self) -> dict[str, object]:
        dataset = self.load_dataset()
        results = []
        correct = 0
        true_positive = false_positive = false_negative = true_negative = 0
        for entry in dataset:
            records = entry.get("records")
            if not isinstance(records, list):
                records = [{"text": entry.get("text", ""), "timestamp": entry.get("timestamp")}]
            response = self.service.analyze_records(records)
            detected = bool(response["reversed_decisions"])
            expected = bool(entry.get("reversal", False))
            correct += int(detected == expected)
            if detected and expected:
                true_positive += 1
            elif detected:
                false_positive += 1
            elif expected:
                false_negative += 1
            else:
                true_negative += 1
            results.append({
                "text": " ".join(str(record.get("text", "")) for record in records),
                "expected": expected,
                "detected": detected,
                "matches": detected == expected,
            })
        accuracy = (correct / len(dataset)) if dataset else 0.0
        precision = (
            true_positive / (true_positive + false_positive)
            if true_positive + false_positive
            else 0.0
        )
        recall = (
            true_positive / (true_positive + false_negative)
            if true_positive + false_negative
            else 0.0
        )
        f1 = (
            2 * precision * recall / (precision + recall)
            if precision + recall
            else 0.0
        )
        return {
            "dataset_size": len(dataset),
            "accuracy": round(accuracy, 3),
            "precision": round(precision, 3),
            "recall": round(recall, 3),
            "f1": round(f1, 3),
            "confusion_matrix": {
                "true_positive": true_positive,
                "false_positive": false_positive,
                "false_negative": false_negative,
                "true_negative": true_negative,
            },
            "dataset_type": "synthetic holdout transcripts",
            "deterministic": True,
            "results": results,
        }
