# Note: build context is the root of the repository: ..
#       this is set in docker-compose.base.yml
FROM python:3.12-slim AS base
ENV POETRY_VERSION=1.8.3
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV POETRY_REQUESTS_TIMEOUT=60
ENV POETRY_INSTALLER_MAX_WORKERS=4
ENV ENV=dev
ENV HOST=0.0.0.0

RUN --mount=target=/var/lib/apt/lists,type=cache,sharing=locked \
    --mount=target=/var/cache/apt,type=cache,sharing=locked \
    rm -f /etc/apt/apt.conf.d/docker-clean \
    && apt-get update -y \
    && apt-get install -y gcc g++ libgdal-dev curl npm \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --shell /bin/bash web
RUN mkdir -p /app/jao-backend && \
    chown -R web:web /app

RUN --mount=type=cache,mode=0755,target=/root/.cache/pip \
    pip install --upgrade pip \
    && pip install "poetry==$POETRY_VERSION" \
    && chown -R web:web /app

WORKDIR /app
USER web

COPY --chown=web:web jao-backend-schemas/ /app/jao-backend-schemas

WORKDIR /app/jao-backend
COPY --chown=web:web jao-backend/package*.json /app/jao-backend

RUN --mount=type=cache,uid=1000,gid=1000,mode=0755,target=/home/web/.npm \
    npm ci

COPY --chown=web:web jao-backend/ /app/jao-backend

RUN --mount=type=cache,uid=1000,gid=1000,mode=0755,target=/home/web/.npm \
    npm run build

RUN --mount=type=cache,mode=0755,target=/home/web/.cache/pip \
    if [ "$ENV" = "dev" ]; then \
        poetry install --no-root; \
    else \
        poetry install --no-root --no-dev; \
    fi

RUN --mount=type=cache,mode=0755,target=/home/web/.cache/pip \
    poetry install

RUN poetry run python src/manage.py collectstatic --noinput

ENV PATH="$PATH:/home/web/.local/bin"
EXPOSE 8000

ENTRYPOINT ["poetry", "run"]
CMD ["hypercorn", "src/asgi:application", "--bind", "0.0.0.0:8000", "--reload"]

FROM base AS jupyter

EXPOSE 8888
ENV DJANGO_ALLOW_ASYNC_UNSAFE=True

USER web
WORKDIR /app/jao-backend

# Install jupyter extra dependencies
RUN --mount=type=cache,mode=0755,target=/home/web/.cache/pip \
    poetry install -E jupyter

# Expose Jupyter port
EXPOSE 8899

# Set the entrypoint to run Jupyter notebook
ENTRYPOINT ["poetry", "run"]
CMD ["src/manage.py", "shell_plus", "--lab"]
