# syntax=docker/dockerfile:1
FROM python:3.14-slim

# --- Environment ---
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# --- System dependencies ---
# build-essential + libpq-dev: needed to build psycopg2 (Postgres) if used
# libjpeg/zlib/libpng: needed by Pillow for image handling
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        libjpeg62-turbo-dev \
        zlib1g-dev \
        libpng-dev \
    && rm -rf /var/lib/apt/lists/*

# --- Install pipenv and project dependencies ---
RUN pip install pipenv

COPY Pipfile Pipfile.lock ./
RUN pipenv install --system --deploy --ignore-pipfile

# --- Copy project source ---
COPY . .

# --- Static & media directories ---
RUN mkdir -p /app/staticfiles /app/media

# --- Collect static files at build time (WhiteNoise will serve these) ---
# Uses the fallback SECRET_KEY/DEBUG defaults already in settings.py, so no
# env vars are required at build time. DATABASE_URL is not needed here since
# collectstatic doesn't touch the DB.
RUN python manage.py collectstatic --noinput

# --- Run as a non-root user ---
RUN useradd --create-home --uid 1000 appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# --workers 3 is a reasonable default for Render's smaller instance types;
# bump it if you're on a larger plan.
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]