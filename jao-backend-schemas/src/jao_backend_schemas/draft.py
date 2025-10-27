from pydantic import BaseModel
from .vacancies import VacancyListing


class DraftRequest(BaseModel):
    description: str
    similar_vacancies: list[VacancyListing]


class DraftResponse(BaseModel):
    draft: str
