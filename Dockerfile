# Verdict Watch V16 — Dockerfile for Google Cloud Run
# Deploys the Streamlit UI. FastAPI runs as a separate service if needed.

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY services.py .
COPY streamlit_app.py .
COPY api.py .

# Create data directory for SQLite
RUN mkdir -p /data
ENV DATABASE_URL=sqlite:////data/verdict_watch.db

# Streamlit config — disable telemetry, set port
ENV STREAMLIT_SERVER_PORT=8080
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
ENV STREAMLIT_SERVER_ENABLE_CORS=false

# Cloud Run expects PORT env var
ENV PORT=8080

EXPOSE 8080

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s \
    CMD curl -f http://localhost:8080/_stcore/health || exit 1

# Run Streamlit
CMD streamlit run streamlit_app.py \
    --server.port=$PORT \
    --server.address=0.0.0.0 \
    --server.headless=true \
    --browser.gatherUsageStats=false