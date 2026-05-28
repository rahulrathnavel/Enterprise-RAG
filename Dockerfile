FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    APP_ENV=production \
    ALLOW_LOCAL_SECRET_FILE=false \
    ENABLE_LOCAL_MODEL_FALLBACK=false \
    FORCE_LOCAL_MODEL_FALLBACK=false \
    BUILD_INDEX_ON_STARTUP=true

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy only approved runtime files. This avoids accidental inclusion of local
# secret files even if a developer misconfigures their Docker build context.
COPY app.py README.md .env.example Dockerfile docker-compose.yml ./
COPY .streamlit ./.streamlit
COPY scripts ./scripts
COPY src ./src

RUN python scripts/generate_data.py

EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health || exit 1

CMD ["sh", "-c", "python scripts/prepare_runtime.py && streamlit run app.py --server.port=${PORT:-8501} --server.address=0.0.0.0"]
