# Use the official Python runtime as a parent image
FROM python:3.12-slim AS base

# Install system dependencies including ODBC driver
RUN apt-get update && \
    apt-get install -y curl gnupg2 apt-transport-https ca-certificates && \
    curl -sL https://deb.nodesource.com/setup_18.x | bash - && \
    apt-get install -y nodejs && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Add Microsoft GPG key and repository
RUN curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg && \
    echo "deb [arch=amd64,arm64,armhf signed-by=/usr/share/keyrings/microsoft-prod.gpg] https://packages.microsoft.com/debian/12/prod bookworm main" | tee /etc/apt/sources.list.d/mssql-release.list

# Install ODBC driver and build tools
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

# Verify ODBC installation in separate layer for better debugging
RUN echo "=== Checking ODBC installation ===" && \
    ls -la /opt/microsoft/msodbcsql17/lib64/ || echo "msodbcsql17 lib64 directory not found" && \
    ls -la /usr/lib/x86_64-linux-gnu/odbc/ || echo "ODBC directory not found" && \
    odbcinst -q -d || echo "ODBC driver check failed"

# Create the app directory
RUN mkdir /app
WORKDIR /app

# Set environment variables to optimize Python
ENV ENV=dev
ENV PYTHONPATH="/app/src"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python -
ENV PATH="/root/.local/bin:$PATH"

# Copy the poetry.lock and pyproject.toml files
COPY ./jao-backend/pyproject.toml ./pyproject.toml
# COPY ./jao-backend/poetry.lock ./poetry.lock

# Install Python dependencies
RUN poetry install --no-root --no-cache

# Copy the package.json and package-lock.json files for npm
COPY ./jao-backend/package.json ./package.json
# COPY ./jao-backend/package-lock.json ./package-lock.json

# Install npm dependencies
RUN npm i

# Copy the rest of the application code
COPY ./jao-backend/src/ ./src/
COPY ./jao-backend/*.py ./
COPY ./jao-backend/webpack.config.js ./webpack.config.js

# Build frontend assets with backendpack
RUN npm run build

# Create frontend module directory
RUN mkdir -p /app/src/frontend && \
    touch /app/src/frontend/__init__.py

# Debug: List directory contents and check ODBC
RUN ls -la /app && \
    ls -la /app/src && \
    echo "=== ODBC Drivers Available ===" && \
    odbcinst -q -d && \
    echo "=== Python ODBC Test ===" && \
    poetry run python -c "import pyodbc; print('Available drivers:', pyodbc.drivers())" || echo "pyodbc test failed"

# Expose the Django port
EXPOSE 8000

# Start the application using hypercorn
CMD sh -c "set -e && \
    echo 'Checking ODBC drivers...' && \
    odbcinst -q -d && \
    echo 'Running migrations...' && \
    poetry run python src/manage.py migrate && \
    echo 'Creating superuser...' && \
    echo 'Username: $JAO_BACKEND_SUPERUSER_USERNAME' && \
    echo 'Email: $JAO_BACKEND_SUPERUSER_EMAIL' && \
    DJANGO_SUPERUSER_USERNAME=$JAO_BACKEND_SUPERUSER_USERNAME DJANGO_SUPERUSER_EMAIL=$JAO_BACKEND_SUPERUSER_EMAIL DJANGO_SUPERUSER_PASSWORD=$JAO_BACKEND_SUPERUSER_PASSWORD \
    poetry run python src/manage.py createsuperuser --noinput || echo 'Superuser creation failed or user already exists' && \
    echo 'Starting server...' && \
    poetry run hypercorn src.asgi:application --bind 0.0.0.0:8000"
