FROM python:3.12-slim

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies (cached layer unless requirements change)
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . .

ENV PYTHONPATH=/app
ENV ENVIRONMENT=production
ENV DEBUG=false

# Apply DB migrations then start the ASGI server
CMD ["sh", "-c", \
    "python scripts/migrate_calendar_tables.py && \
     uvicorn fastapi_app.main:app --host 0.0.0.0 --port 8000"]
