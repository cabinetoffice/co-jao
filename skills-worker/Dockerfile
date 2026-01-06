# 1. Use the correct, older Python version
FROM python:3.10-slim

# 2. Set up our environment
WORKDIR /app
ENV PYTHONPATH="/app"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 3. Copy the requirements file
COPY ./skills-worker/requirements.txt ./requirements.txt

# 4. Install the dependencies using pip
#    This follows the same successful logic as your notebook test
RUN pip install -r ./requirements.txt

# 5. Copy the application code
COPY ./skills-worker/skills_extraction.py ./skills_extraction.py