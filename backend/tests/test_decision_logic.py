from app.nlp.decision_extraction import extract_decision_candidates
from app.nlp.reversal_detector import same_decision
from app.services.decision_service import DecisionService


def analyze(*texts: str) -> dict[str, object]:
    return DecisionService().analyze_records(
        [
            {"id": f"m{index}", "timestamp": f"2024-01-0{index + 1}T09:00:00Z", "text": text}
            for index, text in enumerate(texts)
        ]
    )


def test_extraction_normalizes_option_status_and_context():
    candidates = extract_decision_candidates(["PostgreSQL was approved as the database."])
    assert candidates[0]["option"] == "PostgreSQL"
    assert candidates[0]["status"] == "approved"
    assert candidates[0]["context"] == "database"


def test_matching_requires_context_and_does_not_merge_projects():
    first = {"text": "PostgreSQL was approved for billing.", "option": "PostgreSQL", "context": "project:billing"}
    same = {"text": "PostgreSQL was confirmed for billing.", "option": "PostgreSQL", "context": "project:billing"}
    unrelated = {"text": "PostgreSQL was approved for analytics.", "option": "PostgreSQL", "context": "project:analytics"}
    assert same_decision(first, same)
    assert not same_decision(first, unrelated)


def test_confirmed_reversal_requires_two_explicit_approvals():
    result = analyze(
        "PostgreSQL was approved as the database.",
        "MongoDB was explicitly approved instead.",
    )
    assert len(result["reversed_decisions"]) == 1
    reversal = result["reversed_decisions"][0]
    assert reversal["original_decision"]["option"] == "PostgreSQL"
    assert reversal["latest_decision"]["option"] == "MongoDB"
    assert reversal["evidence"][0]["text"] == "PostgreSQL was approved as the database."


def test_proposal_rejection_refinement_confirmation_and_ambiguity_are_not_reversals():
    assert not analyze(
        "PostgreSQL was approved as the database.",
        "MongoDB was suggested as an alternative.",
    )["reversed_decisions"]
    assert not analyze(
        "MongoDB was proposed as the database.",
        "The team rejected MongoDB.",
    )["reversed_decisions"]
    assert not analyze(
        "PostgreSQL was approved as the database.",
        "The PostgreSQL configuration was changed to use SSL.",
    )["reversed_decisions"]
    assert not analyze(
        "PostgreSQL was approved as the database.",
        "The team confirmed PostgreSQL as the database again.",
    )["reversed_decisions"]
    assert not analyze(
        "The team discussed PostgreSQL and MongoDB for the database, but no final choice was made.",
    )["reversed_decisions"]


def test_chronology_is_timestamp_ordered_and_evidence_preserves_metadata():
    result = DecisionService().analyze_records(
        [
            {"timestamp": "2024-01-03T09:00:00Z", "speaker": "Lee", "text": "MongoDB was approved instead."},
            {"timestamp": "2024-01-01T09:00:00Z", "speaker": "Sam", "text": "PostgreSQL was approved as the database."},
        ]
    )
    reversal = result["reversed_decisions"][0]
    assert reversal["original_decision"]["speaker"] == "Sam"
    assert reversal["latest_decision"]["speaker"] == "Lee"
    assert reversal["evidence"][0]["source_text"] == reversal["original_decision"]["source_text"]
    assert reversal["evidence"][0]["char_start"] == 0
    assert reversal["original_decision"]["chronology_source"] == "timestamp"


def test_empty_input_has_no_candidates():
    result = DecisionService().analyze_records([])
    assert result["total_candidates"] == 0
    assert result["reversed_decisions"] == []


def test_nlp_signals_are_populated_from_the_real_spacy_document():
    result = analyze("The product team approved PostgreSQL as the database.")
    candidate = result["candidates"][0]
    reversal = analyze(
        "PostgreSQL was approved as the database.",
        "MongoDB was explicitly approved instead.",
    )["reversed_decisions"][0]
    assert candidate["confidence"] > 0
    assert reversal["nlp_signals"]["original"]["pos"]["tags"]
    assert reversal["nlp_signals"]["original"]["syntax"]["dependencies"]


def test_sequential_explicit_approvals_produce_two_reversals():
    result = analyze(
        "PostgreSQL was approved as the database.",
        "MongoDB was explicitly approved instead.",
        "MySQL was explicitly approved instead.",
    )
    assert len(result["reversed_decisions"]) == 2
    assert [
        item["latest_decision"]["option"] for item in result["reversed_decisions"]
    ] == ["MongoDB", "MySQL"]


def test_negated_and_conditional_approval_is_not_an_approved_decision():
    result = analyze(
        "PostgreSQL was approved as the database.",
        "MongoDB was not approved.",
        "If MySQL is approved, we will revisit the database choice.",
    )
    assert not result["reversed_decisions"]
    assert [item["status"] for item in result["candidates"][1:]] == ["ambiguous", "ambiguous"]


def test_invalid_timestamp_falls_back_to_input_order_and_discloses_it():
    result = DecisionService().analyze_records(
        [
            {"timestamp": "not-a-date", "text": "PostgreSQL was approved as the database."},
            {"text": "MongoDB was explicitly approved instead."},
        ]
    )
    reversal = result["reversed_decisions"][0]
    assert reversal["original_decision"]["chronology_source"] == "input_order_fallback"
    assert reversal["latest_decision"]["chronology_source"] == "input_order_fallback"
