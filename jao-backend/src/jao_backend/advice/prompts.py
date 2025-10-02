ADVICE_PROMPTS = {
    "general": {
        "system": "You are an expert recruitment advisor. Analyze job postings and provide actionable advice.",
        "user_template": """SIMILAR JOB POSTINGS:
{rag_content}

ANALYSIS REQUEST:
{user_input}

Please provide:
1. Key insights based on patterns in these postings
2. Specific recommendations with examples from the postings
3. Prioritized action items for improvement

Keep your advice specific and reference examples from the job postings."""
    },
    "gender": {
        "system": "You are an expert recruitment advisor specializing in creating inclusive job advertisements that attract diverse gender representation.",
        "user_template": """SIMILAR JOB POSTINGS WITH BALANCED GENDER REPRESENTATION:
{rag_content}

CURRENT JOB DESCRIPTION TO ANALYZE:
{user_input}

Please analyze and provide advice on achieving better gender balance by:
1. Identifying gendered language or biases
2. Highlighting effective practices from similar postings
3. Providing specific recommendations with examples
4. Prioritizing the most impactful changes"""
    },
    "disability": {
        "system": "You are an expert recruitment advisor specializing in creating accessible job advertisements that attract candidates with disabilities.",
        "user_template": """SIMILAR JOB POSTINGS WITH STRONG DISABILITY REPRESENTATION:
{rag_content}

CURRENT JOB DESCRIPTION TO ANALYZE:
{user_input}

Please analyze and provide advice on achieving better disability representation by:
1. Identifying barriers or unnecessarily restrictive requirements
2. Highlighting inclusive practices from similar postings
3. Providing recommendations for accessible language
4. Suggesting ways to emphasize accommodations and support"""
    }
}
