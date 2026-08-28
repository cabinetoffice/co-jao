FROM python:3.12-slim AS base

RUN apt-get update && \
    apt-get install -y curl gnupg2 apt-transport-https ca-certificates && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg && \
    echo "deb [arch=amd64,arm64,armhf signed-by=/usr/share/keyrings/microsoft-prod.gpg] https://packages.microsoft.com/debian/12/prod bookworm main" | tee /etc/apt/sources.list.d/mssql-release.list

RUN apt-get update && \
    ACCEPT_EULA=Y apt-get install -y \
    msodbcsql17 \
    mssql-tools \
    unixodbc \
    unixodbc-dev \
    gcc \
    g++ && \
    ldconfig && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN mkdir /app
WORKDIR /app

ENV ENV=production
ENV PYTHONPATH="/app/src"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# setuptools provides pkg_resources, required by some packages (e.g. django-polymorphic)
RUN pip install --no-cache-dir setuptools

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python -
ENV PATH="/root/.local/bin:$PATH"

COPY ./jao-backend/pyproject.toml ./pyproject.toml
COPY ./jao-backend/poetry.lock ./poetry.lock

RUN poetry install --no-root --no-cache --only main

COPY ./jao-backend/src/ ./src/

CMD ["poetry", "run", "python", "src/manage.py", "run_weekly_pipeline"]
