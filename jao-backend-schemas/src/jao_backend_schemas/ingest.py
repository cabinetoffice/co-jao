from typing import Optional

from pydantic import BaseModel

from jao_backend_schemas.celery import CeleryTaskState


class IngestRequest(BaseModel):
    pass

class IngestResponse(BaseModel):
    task_id: str
    status: CeleryTaskState
    error: Optional[str] = None
    details: Optional[dict] = None

    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "123e4567-e89b-12d3-a456-426614174000",
                "status": "PENDING",
                "error": None,
                "details": {
                    "info": "Task queued successfully.",
                    "timestamp": "2024-12-04T12:00:00Z"
                },
            }
        }