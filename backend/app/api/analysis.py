from __future__ import annotations

import csv
import io
import json

from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse

from app.config import get_settings
from app.schemas.analysis import AnalysisRequest, AnalysisResponse, ExportRequest
from app.services.decision_service import DecisionService

router = APIRouter(prefix="/analysis")
settings = get_settings()
service = DecisionService(match_threshold=settings.decision_match_threshold)


@router.get("/sample")
def sample_analysis() -> dict[str, object]:
    records = [
        {"text": "On Monday, the team approved the marketing launch budget for Q3.", "timestamp": "2024-01-10T09:00:00Z"},
        {"text": "By Wednesday, leadership rejected the launch budget after cost overruns surfaced.", "timestamp": "2024-01-12T11:00:00Z"},
        {"text": "Later, the committee reconsidered the budget and restored the launch plan.", "timestamp": "2024-01-15T15:15:00Z"},
    ]
    return service.analyze_records(records)


@router.post("/run")
def run_analysis(payload: AnalysisRequest) -> AnalysisResponse:
    records = payload.meeting_records
    if isinstance(records, list) and records and all(isinstance(item, str) for item in records):
        records = [{"text": item} for item in records]
    elif not isinstance(records, list):
        raise HTTPException(status_code=400, detail="meeting_records must be a list of strings or meeting records")
    else:
        records = [
            item.model_dump() if hasattr(item, "model_dump") else item
            for item in records
        ]
    result = service.analyze_records(records)
    return AnalysisResponse(**result)


@router.post("/import")
async def import_data(file: UploadFile) -> dict[str, object]:
    if not file.filename:
        raise HTTPException(status_code=400, detail="A file is required")
    content = await file.read()
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail="Import file exceeds configured maximum size")
    try:
        filename = file.filename.lower()
        decoded = content.decode("utf-8-sig")
        if filename.endswith(".json"):
            payload = json.loads(decoded)
            records = payload.get("meeting_records", []) if isinstance(payload, dict) else payload
        elif filename.endswith(".csv"):
            records = list(csv.DictReader(io.StringIO(decoded)))
        elif filename.endswith(".txt"):
            records = [{"text": line} for line in decoded.splitlines() if line.strip()]
        else:
            raise HTTPException(status_code=400, detail="Only JSON, CSV, and TXT files are supported")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="Import file must be UTF-8 text") from exc
    except (json.JSONDecodeError, csv.Error, TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="Malformed import file") from exc
    if not isinstance(records, list) or not records:
        raise HTTPException(status_code=400, detail="Import must contain at least one meeting record")
    if len(records) > settings.max_import_rows:
        raise HTTPException(status_code=400, detail="Import must contain a bounded list of meeting records")
    if any(not isinstance(record, dict) or not str(record.get("text", "")).strip() for record in records):
        raise HTTPException(status_code=400, detail="Every imported record must contain non-empty text")
    result = service.analyze_records(records)
    return result


@router.post("/export", response_model=None)
def export_analysis(payload: ExportRequest) -> JSONResponse | StreamingResponse:
    data = payload.payload or {}
    if payload.format == "json":
        return JSONResponse(content=data)
    rows = data.get("reversed_decisions", []) if isinstance(data, dict) else []
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["topic", "relationship", "similarity", "original", "latest"])
    writer.writeheader()
    for row in rows:
        writer.writerow(
            {
                "topic": row.get("topic"),
                "relationship": row.get("relationship"),
                "similarity": row.get("similarity"),
                "original": row.get("original_decision", {}).get("text"),
                "latest": row.get("latest_decision", {}).get("text"),
            }
        )
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=decisiontrace-results.csv"},
    )
