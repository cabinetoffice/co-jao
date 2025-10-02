from pydantic import BaseModel


class AdviceRequest(BaseModel):
    description: str
    advice_type: str
    similar_vacancies: []


class AdviceResponse(BaseModel):
    advice: str
