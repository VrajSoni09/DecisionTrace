from fastapi import APIRouter

from app.services.evaluation_service import EvaluationService

router = APIRouter(prefix="/evaluation")
service = EvaluationService()


@router.get("")
def list_evaluation() -> dict[str, object]:
    dataset = service.load_dataset()
    return {"dataset_size": len(dataset), "examples": dataset}


@router.post("/run")
def run_evaluation() -> dict[str, object]:
    return service.run()
