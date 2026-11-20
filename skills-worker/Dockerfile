FROM python:3.10-slim

WORKDIR /app
ENV PYTHONPATH="/app"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN groupadd -r workergroup && useradd -r -g workergroup workeruser

COPY ./skills-worker/requirements.txt ./requirements.txt

RUN pip install --no-cache-dir -r ./requirements.txt

COPY ./skills-worker/skills_extraction.py ./skills_extraction.py

RUN chown -R workeruser:workergroup /app

USER workeruser