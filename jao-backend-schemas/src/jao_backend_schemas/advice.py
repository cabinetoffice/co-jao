from pydantic import BaseModel


class AdviceRequest(BaseModel):
    description: str
    advice_type: str


class AdviceResponse(BaseModel):
    advice: str
