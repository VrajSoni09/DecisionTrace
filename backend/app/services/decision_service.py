from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import spacy

from app.config import get_settings
from app.nlp.decision_extraction import extract_decision_candidates
from app.nlp.entity_extraction import extract_entities
from app.nlp.pos_features import extract_pos_summary
from app.nlp.preprocessing import normalize_text, split_sentences
from app.nlp.reversal_detector import detect_reversal_candidates, same_decision
from app.nlp.semantic_matching import semantic_match
from app.nlp.syntactic_analysis import extract_dependency_summary
from app.nlp.text_classifier import classify_text


def _timestamp_value(value: object, fallback: int) -> tuple[float, str | None, str]:
    if not value:
        return float(fallback), None, "input_order_fallback"
    text = str(value)
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp(), text, "timestamp"
    except ValueError:
        return float(fallback), text, "input_order_fallback"


class DecisionService:
    def __init__(self, match_threshold: float | None = None):
        settings = get_settings()
        self.match_threshold = match_threshold or settings.decision_match_threshold
        try:
            self.nlp = spacy.load(settings.nlp_model_name)
        except OSError:
            self.nlp = spacy.blank("en")

    def _candidate(
        self,
        sentence: str,
        record: dict[str, object],
        record_index: int,
        sentence_index: int,
        chronology: float,
        timestamp: str | None,
        chronology_source: str,
        offset: int,
    ) -> dict[str, Any] | None:
        extracted = extract_decision_candidates([sentence])
        if not extracted:
            return None
        decision = extracted[0]
        doc = self.nlp(sentence)
        signals = {
            "entities": extract_entities(doc),
            "pos": extract_pos_summary(doc),
            "syntax": extract_dependency_summary(doc),
            "classification": {
                "topic": classify_text(sentence),
                "status": decision["status"],
                "confidence": decision["score"],
            },
        }
        return {
            "index": record_index * 10000 + sentence_index,
            "chronology": chronology,
            "text": sentence,
            "option": decision["option"],
            "subject": decision["subject"],
            "context": decision["context"],
            "topic": decision["context"],
            "status": decision["status"],
            "score": decision["score"],
            "timestamp": timestamp,
            "chronology_source": chronology_source,
            "speaker": record.get("speaker"),
            "record_id": record.get("id"),
            "source_text": str(record.get("text", "")),
            "char_start": offset,
            "char_end": offset + len(sentence),
            "signals": signals,
        }

    def _trace(
        self,
        record: dict[str, object],
        record_index: int,
        sentence: str,
        sentence_index: int,
        offset: int,
        normalized_text: str,
        candidate: dict[str, Any] | None,
        comparisons: list[dict[str, Any]],
        final_result: str,
    ) -> dict[str, Any]:
        record_id = str(record.get("id")) if record.get("id") is not None else f"record-{record_index + 1}"
        doc = self.nlp(sentence)
        tokens = [
            {"text": token.text, "pos": token.pos_, "tag": token.tag_}
            for token in doc
        ]
        entities = [
            {
                "text": ent.text,
                "label": ent.label_,
                "start": ent.start_char,
                "end": ent.end_char,
            }
            for ent in doc.ents
        ]
        dependencies = [
            {
                "token": token.text,
                "head": token.head.text,
                "dependency": token.dep_,
                "pos": token.pos_,
            }
            for token in doc
        ]
        warnings: list[str] = []
        if not record.get("timestamp"):
            warnings.append("Timestamp unavailable; input order was used for chronology.")
        if not record.get("speaker"):
            warnings.append("Speaker unavailable.")
        if not entities:
            warnings.append("The NLP model recognized no named entities in this entry.")
        if candidate is None:
            warnings.append("No decision candidate met the extraction threshold.")
        stages = [
            {
                "stage": "input_ingestion",
                "status": "success",
                "inputs": {"record_count": 1, "record_id": record_id},
                "outputs": {
                    "source_text": str(record.get("text", "")),
                    "speaker": record.get("speaker"),
                    "timestamp": record.get("timestamp"),
                    "sentence_count": 1,
                },
                "explanation": "The frontend submitted this record to POST /analysis/run.",
            },
            {
                "stage": "text_preprocessing",
                "status": "success",
                "inputs": {"source_text": str(record.get("text", ""))},
                "outputs": {
                    "normalized_text": normalized_text,
                    "sentences": [sentence],
                    "char_start": offset,
                    "char_end": offset + len(sentence),
                },
                "explanation": "Whitespace is normalized and the record is split at sentence punctuation.",
            },
            {
                "stage": "pos_tagging",
                "status": "success",
                "inputs": {"text": sentence},
                "outputs": {"tokens": tokens, "summary": extract_pos_summary(doc)},
                "explanation": "spaCy supplies the part-of-speech and tag values for each token.",
            },
            {
                "stage": "named_entity_recognition",
                "status": "success",
                "inputs": {"text": sentence},
                "outputs": {"entities": entities, "summary": extract_entities(doc)},
                "explanation": "Named entities are taken directly from the spaCy Doc. An empty list is a valid model result.",
            },
            {
                "stage": "syntactic_parsing",
                "status": "success",
                "inputs": {"text": sentence},
                "outputs": {
                    "dependencies": dependencies,
                    "summary": extract_dependency_summary(doc),
                },
                "explanation": "The dependency table uses each token's head and relation from the same spaCy Doc.",
            },
            {
                "stage": "decision_extraction",
                "status": "success" if candidate else "no_result",
                "inputs": {"text": sentence},
                "outputs": candidate or {},
                "explanation": "Deterministic status, option, context, and score rules produce a candidate only when the score reaches 0.7.",
            },
            {
                "stage": "semantic_matching",
                "status": "success",
                "inputs": {"candidate": candidate or {}, "previous_candidates": comparisons},
                "outputs": {"comparisons": comparisons, "algorithm": "TF-IDF cosine similarity"},
                "explanation": "Similarity is a matching signal; it does not by itself prove a reversal.",
            },
            {
                "stage": "decision_state_transition",
                "status": "success",
                "inputs": {"candidate": candidate or {}, "comparisons": comparisons},
                "outputs": {"final_result": final_result},
                "explanation": "The reversal detector applies context, status, option, and relationship rules.",
            },
            {
                "stage": "final_outcome",
                "status": "success" if final_result != "unresolved" else "no_result",
                "inputs": {"candidate": candidate or {}},
                "outputs": {"classification": final_result, "warnings": warnings},
                "explanation": "This is the outcome assigned to the selected entry by the actual analysis.",
            },
        ]
        return {
            "record_id": record_id,
            "source_text": str(record.get("text", "")),
            "sentence_index": sentence_index,
            "source_spans": [{"start": offset, "end": offset + len(sentence)}],
            "warnings": warnings,
            "stages": stages,
        }

    def analyze_records(self, records: list[dict[str, object]]) -> dict[str, object]:
        history: list[dict[str, Any]] = []
        traces: list[dict[str, Any]] = []
        trace_inputs: list[tuple[dict[str, object], int, str, int, int, str]] = []
        normalized_records = []
        for record_index, record in enumerate(records):
            if not isinstance(record, dict):
                continue
            text = str(record.get("text", "")).strip()
            if not text:
                continue
            chronology, timestamp, chronology_source = _timestamp_value(
                record.get("timestamp"), record_index
            )
            normalized_records.append(
                (chronology, record_index, record, timestamp, chronology_source)
            )

        normalized_records.sort(key=lambda item: (item[0], item[1]))
        for chronology, record_index, record, timestamp, chronology_source in normalized_records:
            source_text = str(record["text"])
            normalized_text = normalize_text(source_text)
            cursor = 0
            for sentence_index, sentence in enumerate(split_sentences(source_text)):
                offset = source_text.find(sentence, cursor)
                offset = max(offset, cursor)
                cursor = offset + len(sentence)
                candidate = self._candidate(
                    sentence,
                    record,
                    record_index,
                    sentence_index,
                    chronology,
                    timestamp,
                    chronology_source,
                    offset,
                )
                trace_inputs.append(
                    (record, record_index, sentence, sentence_index, offset, normalized_text)
                )
                if candidate:
                    history.append(candidate)

        findings = detect_reversal_candidates(history)
        reversals = [self._evidence_for_finding(finding) for finding in findings]
        reversal_texts = {item["latest_decision"]["text"] for item in reversals}
        reversal_by_text = {
            item["latest_decision"]["text"]: item for item in reversals
        }
        for record, record_index, sentence, sentence_index, offset, normalized_text in trace_inputs:
            candidate = next(
                (
                    item for item in history
                    if item["text"] == sentence
                    and item["record_id"] == record.get("id")
                    and item["char_start"] == offset
                ),
                None,
            )
            comparisons: list[dict[str, Any]] = []
            if candidate:
                for previous in history:
                    if previous is candidate or previous["chronology"] > candidate["chronology"]:
                        continue
                    if previous["context"] != candidate["context"]:
                        continue
                    comparisons.append(
                        {
                            "previous_text": previous["text"],
                            "previous_option": previous.get("option"),
                            "previous_status": previous.get("status"),
                            "similarity": semantic_match(previous["text"], candidate["text"]),
                            "related": same_decision(previous, candidate),
                        }
                    )
            if candidate and candidate["text"] in reversal_texts:
                final_result = "confirmed reversal"
            elif candidate:
                final_result = str(candidate["status"])
            else:
                final_result = "unresolved"
            reversal = reversal_by_text.get(candidate["text"]) if candidate else None
            transition = {
                "classification": final_result,
                "reason": (
                    "Both decisions are approved, share context, and have different explicit options."
                    if reversal
                    else "No confirmed approved-to-approved option change was found for this entry."
                ),
            }
            final_outputs = {"classification": final_result}
            if reversal:
                final_outputs["original_decision"] = reversal["original_decision"]
                final_outputs["latest_decision"] = reversal["latest_decision"]
                final_outputs["evidence"] = reversal["evidence"]
            traces.append(
                self._trace(
                    record,
                    record_index,
                    sentence,
                    sentence_index,
                    offset,
                    normalized_text,
                    candidate,
                    comparisons,
                    final_result,
                )
            )
            traces[-1]["stages"][-2]["outputs"]["transition"] = transition
            final_outputs["warnings"] = traces[-1]["warnings"]
            traces[-1]["stages"][-1]["outputs"] = final_outputs
        return {
            "summary": f"Analyzed {len(records)} records and found {len(reversals)} confirmed reversal candidates.",
            "candidates": [
                {
                    "text": item["text"],
                    "topic": item["topic"],
                    "status": item["status"],
                    "confidence": item["score"],
                    "reversal": item["text"] in reversal_texts,
                    "related_to": item.get("option"),
                    "evidence": [
                        "Exact source sentence retained",
                        f"option={item.get('option') or 'not identified'}",
                        f"context={item['context']}",
                    ],
                }
                for item in history
            ],
            "reversed_decisions": reversals,
            "total_records": len(records),
            "total_candidates": len(history),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "traces": traces,
            "processing_summary": {
                "records_received": len(records),
                "records_parsed": len(normalized_records),
                "records_processed": len(trace_inputs),
                "decision_candidates": len(history),
                "candidates_matched": sum(
                    1 for trace in traces
                    for comparison in next(
                        (stage["outputs"]["comparisons"] for stage in trace["stages"] if stage["stage"] == "semantic_matching"),
                        [],
                    )
                    if comparison["related"]
                ),
                "confirmed_reversals": len(reversals),
                "unresolved_candidates": sum(1 for trace in traces if trace["stages"][-1]["outputs"]["classification"] == "unresolved"),
            },
        }

    def _evidence_for_finding(self, finding: dict[str, Any]) -> dict[str, Any]:
        timeline = finding["timeline"]
        previous = finding["previous"]
        current = finding["current"]
        evidence = [
            {
                "text": item["text"],
                "speaker": item.get("speaker"),
                "timestamp": item.get("timestamp"),
                "chronology_source": item.get("chronology_source"),
                "record_id": item.get("record_id"),
                "source_text": item.get("source_text"),
                "char_start": item.get("char_start"),
                "char_end": item.get("char_end"),
            }
            for item in timeline
        ]
        return {
            "topic": finding["context"],
            "relationship": finding["relationship"],
            "similarity": round(semantic_match(previous["text"], current["text"]), 4),
            "confidence": round(min(previous["score"], current["score"]), 3),
            "confidence_basis": "Rule-supported approved-to-approved option change with matching context; not a probability.",
            "limitations": [
                "The system does not resolve pronouns or unstated references.",
                "A reversal is confirmed only when both options are explicitly approved.",
            ],
            "original_decision": previous,
            "intermediate_updates": [
                item for item in timeline
                if item is not previous and item is not current
            ],
            "latest_decision": current,
            "timeline": timeline,
            "evidence": evidence,
            "nlp_signals": {
                "original": previous["signals"],
                "latest": current["signals"],
            },
        }
