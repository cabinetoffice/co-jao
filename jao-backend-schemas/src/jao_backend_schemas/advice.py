from pydantic import BaseModel
from .vacancies import VacancyListing


class AdviceRequest(BaseModel):
    description: str
    advice_type: str
    similar_vacancies: list[VacancyListing]


class AdviceResponse(BaseModel):
    advice: str
