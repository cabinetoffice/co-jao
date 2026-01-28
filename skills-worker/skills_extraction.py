import os
from flask import Flask, request, jsonify
from ojd_daps_skills.extract_skills.extract_skills import SkillsExtractor

print("SKILLS-WORKER: Loading ESCO skills model... (this may take a moment)")
sm = SkillsExtractor(taxonomy_name="esco")
print("SKILLS-WORKER: ESCO Model loaded successfully.")

app = Flask(__name__)


def _clean_extracted_spans(skill_spans: list) -> list[str]:
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


@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy", "service": "skills-worker"})


@app.route('/extract', methods=['POST'])
def extract():
    data = request.get_json()

    if not data or 'texts' not in data:
        return jsonify({"status": "error", "message": "Missing 'texts' field in request"}), 400

    applicant_text_batch = data['texts']

    if not isinstance(applicant_text_batch, list):
        return jsonify({"status": "error", "message": "'texts' must be a list"}), 400

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
        return jsonify({"status": "success", "data": final_results})

    except Exception as e:
        print(f"SKILLS-WORKER: Error during extraction: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
