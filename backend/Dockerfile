# ---------- Backend Dockerfile (multi-stage) ----------
# Stage 1: dependencies
FROM python:3.13-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install system build deps needed by some wheels (e.g. asyncpg build)
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# ---------- Development stage ----------
FROM base AS dev

# Copy package metadata and source first so the editable install can find
# the `app` package (setuptools errors with "package directory does not exist"
# if the source is not present yet).
COPY pyproject.toml ./
COPY app ./app
RUN pip install --upgrade pip \
    && pip install -e ".[dev]"

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# ---------- Production stage ----------
FROM base AS prod

COPY pyproject.toml ./
COPY app ./app
RUN pip install --upgrade pip \
    && pip install "."

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]