from typing import Dict, List

from pydantic import BaseModel


class JobDescriptionRequest(BaseModel):
    description: str


class JobDescriptionOptimisationRequest(JobDescriptionRequest):
    pass


class VacancyListing(BaseModel):
    job_title: str
    full_job_desc: str
    vacancy_id: int


class SimilarVacanciesResponse(BaseModel):
    similar_vacancies: List[VacancyListing]
