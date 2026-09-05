FROM python:3.12-slim

# System deps for psycopg2 (PostgreSQL driver).
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Hosting platforms inject $PORT; default to 8000 for local runs.
ENV PORT=8000
EXPOSE 8000

# Uvicorn worker under Gunicorn for production.
CMD ["sh", "-c", "gunicorn app.main:app -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:${PORT} --workers 2"]
