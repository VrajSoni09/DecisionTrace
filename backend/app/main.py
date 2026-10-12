from __future__ import annotations

from fastapi import FastAPI, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.api.analysis import (
    export_analysis,
    import_data,
    router as analysis_router,
    run_analysis,
    sample_analysis,
)
from app.api.evaluation import list_evaluation, router as evaluation_router, run_evaluation
from app.api.health import healthcheck, router as health_router
from app.config import get_settings
from app.schemas.analysis import AnalysisRequest, AnalysisResponse, ExportRequest

settings = get_settings()
configured_origins = [origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()]
origins = list(dict.fromkeys([
    *configured_origins,
    "http://127.0.0.1:5173",
    "http://localhost:5173",
]))
app = FastAPI(title="DecisionTrace", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(analysis_router)
app.include_router(evaluation_router)


@app.get("/api/health")
def api_healthcheck() -> dict[str, str]:
    return healthcheck()


@app.get("/api/analysis/sample")
def api_sample_analysis() -> dict[str, object]:
    return sample_analysis()


@app.post("/api/analysis/run")
def api_run_analysis(payload: AnalysisRequest) -> AnalysisResponse:
    return run_analysis(payload)


@app.post("/api/analysis/import")
async def api_import_data(file: UploadFile) -> dict[str, object]:
    return await import_data(file)


@app.post("/api/analysis/export")
def api_export_analysis(payload: ExportRequest):
    return export_analysis(payload)


@app.get("/api/evaluation")
def api_list_evaluation() -> dict[str, object]:
    return list_evaluation()


@app.post("/api/evaluation/run")
def api_run_evaluation() -> dict[str, object]:
    return run_evaluation()


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "DecisionTrace API"}
