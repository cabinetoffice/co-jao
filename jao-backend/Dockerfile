# Use the official Python runtime as a parent image
FROM python:3.12-slim AS base

# Install Node.js and npm
RUN apt-get update && \
    apt-get install -y curl && \
    curl -sL https://deb.nodesource.com/setup_18.x | bash - && \
    apt-get install -y nodejs && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Create the app directory
RUN mkdir /app

# Set the working directory inside the container
WORKDIR /app

# Set environment variables to optimize Python
ENV ENV=dev
ENV PYTHONPATH="/app/src"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python -

# Add Poetry to the PATH
ENV PATH="/root/.local/bin:$PATH"

# Copy the jao-backend-schemas directory
COPY ./jao-backend/jao_backend_schemas/ ./jao_backend_schemas/

# Copy the poetry.lock and pyproject.toml files
COPY ./jao-backend/pyproject.toml ./pyproject.toml
# COPY poetry.lock ./poetry.lock

# Install Python dependencies
RUN poetry install --no-root --no-cache

# Copy the package.json and package-lock.json files for npm
COPY ./jao-backend/package.json ./package.json
# COPY package-lock.json ./package-lock.json

# Install npm dependencies
RUN npm i

# Copy the rest of the application code
COPY ./jao-backend/src/ ./src/
COPY ./jao-backend/*.py ./

RUN ls -la /app
RUN ls -la /app/src

# Expose the Django port
EXPOSE 8000

# Start the application using hypercorn
CMD ["poetry", "run", "hypercorn", "src.asgi:application", "--bind", "0.0.0.0:8000"]
