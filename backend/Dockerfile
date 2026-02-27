FROM python:3.12-slim

WORKDIR /app

# Install system dependencies for ML libs (scikit-learn, xgboost, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

# Default to safe paper mode with mock data
ENV TRADING_MODE=paper
ENV USE_MOCK_DATA=true

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
