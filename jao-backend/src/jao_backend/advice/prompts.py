
GENERAL_ADVICE_PROMPT = """You are an expert career advisor and recruiter. Based on these similar job postings, provide specific, actionable advice.

        SIMILAR JOB POSTINGS: {context}

        ANALYSIS REQUEST: {user_input}


        Please provide:
            1. Key insights based on patterns in these postings
            2. Specific recommendations with examples from the postings
            3. Prioritized action items for improvement

        Keep your advice specific. Reference examples from the job postings to support your recommendations.

        Answer:"""

GENDER_BALANCE_PROMPT = """Provide advice to attract more applicants with
disabilities {options}"""

DISABILITY_BALANCE_PROMPT = """Provide advice to attract more applicants with
disabilities {options}"""
