# UNCOMMON RAG API Dockerfile - CUDA 지원
FROM nvidia/cuda:12.1.1-cudnn8-runtime-ubuntu22.04 AS base

# 환경변수
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8

# 시스템 패키지 설치
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.10 \
    python3.10-dev \
    python3-pip \
    python3.10-venv \
    build-essential \
    cmake \
    curl \
    wget \
    git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# PyTorch 설치 스테이지
FROM base AS pytorch

# 빌드 인자
ARG USE_CUDA=true
ARG CUDA_VERSION=cu121

WORKDIR /app
COPY requirements.txt .

# 빌드 인자 확인
RUN echo "=== Build Arguments ===" && \
    echo "USE_CUDA: $USE_CUDA" && \
    echo "CUDA_VERSION: $CUDA_VERSION" && \
    echo "======================="

# PyTorch 설치 (CUDA 버전만)
RUN pip install --upgrade pip && \
    if [ "$USE_CUDA" = "true" ]; then \
        echo "Installing CUDA version of PyTorch with cu121..." && \
        pip install torch==2.5.1+cu121 torchvision==0.20.1+cu121 torchaudio==2.5.1+cu121 --index-url https://download.pytorch.org/whl/cu121; \
    else \
        echo "Installing CPU version of PyTorch..." && \
        pip install torch==2.5.1 torchvision==0.20.1 torchaudio==2.5.1 --index-url https://download.pytorch.org/whl/cpu; \
    fi

# 나머지 패키지 설치
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 스테이지
FROM pytorch AS app

# 사용자 생성 및 홈 디렉토리 권한 설정
RUN groupadd -r appuser && useradd -r -g appuser -m -d /home/appuser appuser

# HuggingFace 캐시 디렉토리 미리 생성 및 권한 설정
RUN mkdir -p /home/appuser/.cache/huggingface \
    && mkdir -p /app/models \
    && mkdir -p /app/logs \
    && chown -R appuser:appuser /home/appuser \
    && chmod -R 755 /home/appuser

# 환경변수 - 캐시 디렉토리
ENV TRANSFORMERS_CACHE=/home/appuser/.cache/huggingface
ENV HF_HOME=/home/appuser/.cache/huggingface

# 애플리케이션 복사
COPY --chown=appuser:appuser . .

# 권한 설정
RUN chown -R appuser:appuser /app

USER appuser
EXPOSE ${RAG_API_INTERNAL_PORT}

# 헬스체크
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:${RAG_API_INTERNAL_PORT}/health || exit 1

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${RAG_API_INTERNAL_PORT} --reload"]