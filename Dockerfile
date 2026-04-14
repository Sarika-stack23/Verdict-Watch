# Dockerfile — Verdict Watch V20
# Google Cloud Run deployment
# weasyprint requires extra system deps vs V16

FROM python:3.11-slim

WORKDIR /app

# System deps — weasyprint (PDF) needs pango, cairo, fontconfig
RUN apt-get update && apt-get install -y \
    build-essential curl \
    libpango-1.0-0 libpangoft2-1.0-0 \
    libcairo2 libgdk-pixbuf2.0-0 \
    libffi-dev libssl-dev \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services.py .
COPY streamlit_app.py .
COPY api.py .

RUN mkdir -p /data
ENV DATABASE_URL=sqlite:////data/verdict_watch.db
ENV STREAMLIT_SERVER_PORT=8080
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
ENV STREAMLIT_SERVER_ENABLE_CORS=false
ENV PORT=8080

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s \
    CMD curl -f http://localhost:8080/_stcore/health || exit 1

CMD streamlit run streamlit_app.py \
    --server.port=$PORT \
    --server.address=0.0.0.0 \
    --server.headless=true \
    --browser.gatherUsageStats=false