# JAO Data Engine

Django-based data processing engine for job advert analysis. Runs as scheduled batch jobs.

## Overview

This is a minimal data engine that:
- Ingests job vacancy data from Oleeo
- Generates embeddings using AWS Bedrock
- Extracts skills (via separate Python 3.10 worker)
- Aggregates statistics and regional data

## File Layout

This project uses src layout with Django apps in `src/jao_backend/`.

## Configuration

Settings are in `src/jao_backend/settings/` with per-environment settings extending `common.py`:
- `dev.py`
- `production.py`
- `test.py`

Environment variables are used for configuration. See settings files for the full list.

Key environment variables:

| Variable | Description |
|----------|-------------|
| `JAO_BACKEND_DATABASE_URL` | PostgreSQL database URL |
| `JAO_BACKEND_OLEEO_DATABASE_URL` | Oleeo MSSQL database URL |
| `JAO_BACKEND_SECRET_KEY` | Django secret key |

## Prerequisites

### Poetry

Manages Python dependencies. Install it, then:

```sh
poetry install
```

### ODBC Libraries (for Oleeo MSSQL)

On macOS with Homebrew:

```sh
brew tap microsoft/mssql-release https://github.com/Microsoft/homebrew-mssql-release
brew update
HOMEBREW_ACCEPT_EULA=Y brew install msodbcsql17 mssql-tools
```

## Commands

### Database migrations

```sh
python src/manage.py migrate
```

### Run the weekly pipeline

```sh
python src/manage.py run_weekly_pipeline
```

This orchestrates:
1. Data ingestion from Oleeo
2. Embedding generation
3. Statistics aggregation
4. Regional aggregation

### Individual commands

```sh
# Ingest data
python src/manage.py ingest

# Generate embeddings
python src/manage.py embed_vacancies

# Aggregate statistics
python src/manage.py aggregate_statistics

# Aggregate regions
python src/manage.py aggregate_regions
```

## Deployment

The data engine runs as scheduled ECS tasks on AWS, triggered by EventBridge.

See `iac/` for Terraform infrastructure configuration.
