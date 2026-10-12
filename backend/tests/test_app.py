from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_analysis_endpoint_allows_frontend_origin():
    response = client.options(
        "/analysis/run",
        headers={
            "Origin": "http://127.0.0.1:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"
    assert "POST" in response.headers["access-control-allow-methods"]


def test_analysis_sample():
    response = client.get("/analysis/sample")
    assert response.status_code == 200
    payload = response.json()
    assert "summary" in payload
    assert "reversed_decisions" in payload
    assert payload["total_records"] >= 1


def test_analysis_includes_traceable_pipeline_outputs():
    response = client.post(
        "/analysis/run",
        json={"meeting_records": [{"id": "m-1", "timestamp": "2024-01-01T09:00:00Z", "text": "The team approved PostgreSQL as the database."}]},
    )
    assert response.status_code == 200
    payload = response.json()
    trace = payload["traces"][0]
    assert trace["record_id"] == "m-1"
    assert trace["source_spans"][0] == {"start": 0, "end": len(trace["source_text"])}
    assert [stage["stage"] for stage in trace["stages"]] == [
        "input_ingestion",
        "text_preprocessing",
        "pos_tagging",
        "named_entity_recognition",
        "syntactic_parsing",
        "decision_extraction",
        "semantic_matching",
        "decision_state_transition",
        "final_outcome",
    ]
    assert payload["processing_summary"]["decision_candidates"] == payload["total_candidates"]


def test_analysis_handles_multiple_decision_sentences_without_server_error():
    response = client.post(
        "/analysis/run",
        json={
            "meeting_records": [
                "The team approved PostgreSQL as the primary database for Project Atlas.",
                "MongoDB is proposed, not approved.",
                "We now approve MongoDB as the primary database for Project Atlas instead.",
                "PostgreSQL is approved for analytics reporting only.",
            ]
        },
    )
    assert response.status_code == 200
    assert response.json()["total_records"] == 4


def test_evaluation_endpoint():
    response = client.get("/evaluation")
    assert response.status_code == 200
    payload = response.json()
    assert "dataset_size" in payload


def test_api_accepts_csv_and_txt_and_rejects_malformed_json():
    csv_response = client.post(
        "/api/analysis/import",
        files={"file": ("notes.csv", b"timestamp,speaker,text\n2024-01-01T09:00:00Z,Sam,PostgreSQL was approved as the database.\n", "text/csv")},
    )
    assert csv_response.status_code == 200
    assert csv_response.json()["total_candidates"] == 1

    txt_response = client.post(
        "/api/analysis/import",
        files={"file": ("notes.txt", b"PostgreSQL was approved as the database.\n", "text/plain")},
    )
    assert txt_response.status_code == 200

    malformed = client.post(
        "/api/analysis/import",
        files={"file": ("notes.json", b"{not-json}", "application/json")},
    )
    assert malformed.status_code == 400


def test_api_export_returns_csv():
    response = client.post(
        "/api/analysis/export",
        json={"format": "csv", "payload": {"reversed_decisions": []}},
    )
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert "topic,relationship,similarity,original,latest" in response.text


def test_empty_import_returns_a_useful_validation_error():
    response = client.post(
        "/api/analysis/import",
        files={"file": ("empty.txt", b"   ", "text/plain")},
    )
    assert response.status_code == 400
    assert "at least one" in response.json()["detail"]
