import os
from celery import Celery
from ojd_daps_skills.extract_skills.extract_skills import SkillsExtractor

print("SKILLS-WORKER: Loading ESCO skills model... (this may take a moment)")
sm = SkillsExtractor(taxonomy_name="esco")
print("SKILLS-WORKER: ESCO Model loaded successfully.")

REDIS_URL = os.environ.get("CELERY_BROKER_URL", "redis://redis:6379/0")

skills_celery_app = Celery(
    "skills_worker",
    broker=REDIS_URL,
    backend=REDIS_URL
)

skills_celery_app.conf.task_routes = {
    'skills_worker.tasks.*': {'queue': 'skills_queue'}
}

def _clean_extracted_spans(skill_spans: list) -> list[str]:
    """
    Cleans the output from doc._.skill_spans.
    This list can contain a mix of spaCy Spans (objects) and strings.
    """
    if not skill_spans:
        return []
    
    cleaned_skills = set()
    for span in skill_spans:
        

        if hasattr(span, 'text'):
            skill_text = str(span.text).lower().strip()
        else:
            skill_text = str(span).lower().strip()
            
        if skill_text:
            cleaned_skills.add(skill_text)
            
    return list(cleaned_skills)

@skills_celery_app.task(name="skills_worker.tasks.extract_from_applicant_text")
def extract_from_applicant_text(applicant_text_batch: list[str]):
    """
    Receives a list of applicant text, extracts raw skills (no mapping),
    and returns a clean list of results.
    """
    print(f"SKILLS-WORKER: Received {len(applicant_text_batch)} texts to process.")
    try:
        job_ad_docs = sm.extract_skills(applicant_text_batch)
        
        final_results = []
        for doc in job_ad_docs:
            
            cleaned_skill_list = _clean_extracted_spans(doc._.skill_spans)
            
            final_results.append({
                "original_text": str(doc),
                "extracted_skills": cleaned_skill_list 
            })
        
        print("SKILLS-WORKER: Processing complete.")
        return {"status": "success", "data": final_results}
        
    except Exception as e:
        print(f"SKILLS-WORKER: Error during extraction: {e}")
        return {"status": "error", "message": str(e)}