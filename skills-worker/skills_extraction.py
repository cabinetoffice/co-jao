# import os
# from celery import Celery
# from ojd_daps_skills.extract_skills.extract_skills import SkillsExtractor

# print("Loading ESCO skills model...")
# sm = SkillsExtractor(taxonomy_name="esco")
# print("ESCO Model loaded successfully.")


# REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")

# skills_celery_app = Celery(
#     "skills_worker",
#     broker=REDIS_URL,
#     backend=REDIS_URL
# )

# skills_celery_app.conf.task_routes = {
#     'skills_worker.tasks.*': {'queue': 'skills_queue'}
# }

# def _clean_skill_output(mapped_skills_list: list) -> list[str]:
#     """Cleans the complex output from doc._.mapped_skills."""
#     if not mapped_skills_list:
#         return []
    
#     cleaned_skills = set()
#     for mapping_result in mapped_skills_list:
#         if isinstance(mapping_result, dict):
#             skill_name = mapping_result.get('preferred_label')
#             if skill_name:
#                 cleaned_skills.add(skill_name.lower())
                
#     return list(cleaned_skills)

# @skills_celery_app.task(name="skills_worker.tasks.extract_from_applicant_text")
# def extract_from_applicant_text(job_ad_batch: list[str]):
#     """
#     Receives a list of applicant text, extracts skills,
#     and returns a clean list of results.
#     """
#     print(f"SKILLS-WORKER: Received {len(job_ad_batch)} ads to process.")
#     try:
#         job_ad_docs = sm(job_ad_batch)
        
#         final_results = []
#         for doc in job_ad_docs:
#             cleaned_skill_list = _clean_skill_output(doc._.mapped_skills)
#             final_results.append({
#                 "original_text": str(doc),
#                 "mapped_skills": cleaned_skill_list
#             })
        
#         print("SKILLS-WORKER: Processing complete.")
#         return {"status": "success", "data": final_results}
        
#     except Exception as e:
#         print(f"Error during extraction: {e}")
#         return {"status": "error", "message": str(e)}


import os
from celery import Celery
# We must import the main class to load the model
from ojd_daps_skills.extract_skills.extract_skills import SkillsExtractor

# --- 1. Load the Model (PAID ONCE) ---
print("SKILLS-WORKER: Loading ESCO skills model... (this may take a moment)")
sm = SkillsExtractor(taxonomy_name="esco")
print("SKILLS-WORKER: ✅ ESCO Model loaded successfully.")

# --- 2. Define the Celery App ---
REDIS_URL = os.environ.get("CELERY_BROKER_URL", "redis://redis:6379/0")

skills_celery_app = Celery(
    "skills_worker",
    broker=REDIS_URL,
    backend=REDIS_URL
)

skills_celery_app.conf.task_routes = {
    'skills_worker.tasks.*': {'queue': 'skills_queue'}
}

# --- This is the NEW, CORRECTED cleaning function ---
def _clean_extracted_spans(skill_spans: list) -> list[str]:
    """
    Cleans the output from doc._.skill_spans.
    This list can contain a mix of spaCy Spans (objects) and strings.
    """
    if not skill_spans:
        return []
    
    cleaned_skills = set() # Use a set for unique skills
    for span in skill_spans:
        
        # --- THIS IS THE FIX ---
        if hasattr(span, 'text'):
            # It's a spaCy Span object, so get its .text
            skill_text = str(span.text).lower().strip()
        else:
            # It's already a plain string
            skill_text = str(span).lower().strip()
        # ---------------------
            
        if skill_text:
            cleaned_skills.add(skill_text)
            
    return list(cleaned_skills)

# --- 4. This is the CORRECT task ---
@skills_celery_app.task(name="skills_worker.tasks.extract_from_applicant_text")
def extract_from_applicant_text(applicant_text_batch: list[str]):
    """
    Receives a list of applicant text, extracts raw skills (no mapping),
    and returns a clean list of results.
    """
    print(f"SKILLS-WORKER: Received {len(applicant_text_batch)} texts to process.")
    try:
        # --- FIX 1: Call extract_skills() to skip mapping ---
        job_ad_docs = sm.extract_skills(applicant_text_batch)
        
        final_results = []
        for doc in job_ad_docs:
            
            # --- FIX 2: Read from ._.skill_spans and use the correct cleaner ---
            cleaned_skill_list = _clean_extracted_spans(doc._.skill_spans)
            
            final_results.append({
                "original_text": str(doc),
                # --- FIX 3: Use the key 'extracted_skills' ---
                "extracted_skills": cleaned_skill_list 
            })
        
        print("SKILLS-WORKER: Processing complete.")
        return {"status": "success", "data": final_results}
        
    except Exception as e:
        print(f"SKILLS-WORKER: Error during extraction: {e}")
        return {"status": "error", "message": str(e)}