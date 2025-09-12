"""
The schemas here require celery to be installed.

jao_backend_schemas should be installed with -E celery
"""

from enum import Enum
from typing import Any
from typing import Optional

from celery import states
from pydantic import BaseModel

# Enums of celery states, so we can use them in pydantic models
CeleryTaskState = Enum("CeleryTaskState", {state: state for state in states.ALL_STATES})

CeleryReadyState = Enum(
    "CeleryReadyState", {state: state for state in states.READY_STATES}
)

CeleryUnreadyState = Enum(
    "CeleryUnreadyState", {state: state for state in states.UNREADY_STATES}
)

CeleryExceptionState = Enum(
    "CeleryExceptionState", {state: state for state in states.EXCEPTION_STATES}
)


class TaskStatusResponse(BaseModel):
    status: CeleryTaskState
    result: Optional[Any]
    error_message: Optional[str] = None

    @property
    def is_ready(self):
        return self.status in CeleryReadyState

    @property
    def is_unready(self):
        return self.status in CeleryUnreadyState

    @property
    def is_error(self):
        return self.status in CeleryExceptionState


class TaskResponse(BaseModel):
    task_id: str


class TaskStopResponse(BaseModel):
    message: str
