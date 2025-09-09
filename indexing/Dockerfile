# UNCOMMON Indexing Server Dockerfile - 기존 동작 코드 참조
FROM nvidia/cuda:12.1.1-cudnn8-runtime-ubuntu22.04 AS base

# 환경변수
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8

# 시스템 패키지 설치
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.11 \
    python3.11-dev \
    python3-pip \
    python3.11-venv \
    build-essential \
    cmake \
    curl \
    wget \
    git \
    && ln -s /usr/bin/python3.11 /usr/bin/python \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# PyTorch 설치 스테이지
FROM base AS pytorch

# 빌드 인자를 이 스테이지에서 다시 선언
ARG USE_CUDA=false
ARG CUDA_VERSION=cu121

WORKDIR /app
COPY requirements.txt .

# 빌드 인자 확인을 위한 디버그 출력
RUN echo "=== Build Arguments ===" && \
    echo "USE_CUDA: $USE_CUDA" && \
    echo "CUDA_VERSION: $CUDA_VERSION" && \
    echo "======================="

# PyTorch 설치 (기본 CPU 버전 또는 CUDA 버전)
RUN pip install --upgrade pip && \
    if [ "$USE_CUDA" = "true" ]; then \
        echo "Installing CUDA version of PyTorch (cu121)..." && \
        pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121; \
    else \
        echo "Installing CPU version of PyTorch..." && \
        pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu; \
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
EXPOSE 8002

# 헬스체크
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8002/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002"]