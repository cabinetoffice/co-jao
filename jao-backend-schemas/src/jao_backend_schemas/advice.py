from pydantic import BaseModel


class AdviceRequest(BaseModel):
    description: str
    advice_type: str
    similar_vacancies: list[str]


class AdviceResponse(BaseModel):
    advice: str
