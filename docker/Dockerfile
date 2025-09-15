FROM nvidia/cuda:12.3.2-cudnn9-runtime-ubuntu22.04

# 환경 변수 설정
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV UV_SYSTEM_PYTHON=1

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 패키지 업데이트 및 필수 패키지 설치
RUN apt-get update -y && \
    apt-get install -y \
    python3 \
    python3-pip \
    python3-dev \
    curl \
    git \
    build-essential \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# UV 패키지 매니저 설치
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# 프로젝트 파일 복사
COPY pyproject.toml uv.lock ./
COPY faster_whisper/ ./faster_whisper/
COPY stt_simple.py app.py main.py ./
COPY docker/docker_infer.py ./

# 의존성 설치
RUN uv sync --frozen

# 포트 노출 (GUI 앱용)
EXPOSE 8080

# 헬스체크 스크립트
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python3 -c "from faster_whisper import WhisperModel; print('OK')" || exit 1

# 기본 명령어
CMD ["python3", "docker_infer.py"]