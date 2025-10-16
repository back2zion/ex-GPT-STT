#!/bin/bash

echo "🚀 한국도로공사 모바일 오피스 STT API 서버 시작"
echo "📱 모바일 녹음 → API 업로드 → STT 처리 → 회의록 이메일 발송"
echo "=================================================="

# 환경 확인
echo "🔍 시스템 환경 확인"
echo "  - Python: $(python3 --version 2>/dev/null || echo 'Not found')"
echo "  - UV: $(uv --version 2>/dev/null || echo 'Not found')"

# GPU 상태 확인
echo ""
echo "🎮 GPU 상태:"
if command -v nvidia-smi >/dev/null 2>&1; then
    nvidia-smi --query-gpu=index,name,memory.used,memory.total,utilization.gpu --format=csv,noheader | head -2
else
    echo "  ❌ NVIDIA GPU 또는 nvidia-smi를 찾을 수 없습니다"
fi

# Ollama 상태 확인
echo ""
echo "🤖 Ollama 상태 확인:"
if curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
    echo "  ✅ Ollama 서버 실행 중 (localhost:11434)"
    # 사용 가능한 모델 확인
    MODELS=$(curl -s http://localhost:11434/api/tags | grep -o '"name":"[^"]*"' | sed 's/"name":"//g' | sed 's/"//g' | head -3)
    if [ ! -z "$MODELS" ]; then
        echo "  📦 사용 가능한 모델:"
        echo "$MODELS" | sed 's/^/    - /'
    fi
else
    echo "  ❌ Ollama 서버가 실행되지 않았습니다"
    echo "  💡 ollama serve 명령으로 Ollama를 먼저 시작하세요"
fi

# 필수 모델 확인
echo ""
echo "🎤 STT 모델 확인:"
WHISPER_MODEL_PATH="$HOME/.cache/huggingface/hub/models--Systran--faster-whisper-large-v3"
if [ -d "$WHISPER_MODEL_PATH" ]; then
    echo "  ✅ Whisper Large-v3 모델 캐시됨"
else
    echo "  ⚠️ Whisper Large-v3 모델이 캐시되지 않음 (첫 실행 시 자동 다운로드)"
fi

# 필수 디렉토리 생성
echo ""
echo "📁 필수 디렉토리 생성:"
mkdir -p /tmp/mobile_office_uploads
mkdir -p /tmp/stt_api_results
echo "  ✅ 업로드 디렉토리: /tmp/mobile_office_uploads"
echo "  ✅ 결과 디렉토리: /tmp/stt_api_results"

# 환경변수 확인
echo ""
echo "📧 이메일 설정 확인:"
if [ ! -z "$SENDER_EMAIL" ]; then
    echo "  ✅ SENDER_EMAIL: ${SENDER_EMAIL}"
else
    echo "  ⚠️ SENDER_EMAIL 환경변수가 설정되지 않음"
    echo "    export SENDER_EMAIL=\"your_email@gmail.com\""
fi

if [ ! -z "$SENDER_PASSWORD" ]; then
    echo "  ✅ SENDER_PASSWORD: 설정됨"
else
    echo "  ⚠️ SENDER_PASSWORD 환경변수가 설정되지 않음"
    echo "    export SENDER_PASSWORD=\"your_app_password\""
fi

if [ ! -z "$EMAIL_NAME_MAPPING" ]; then
    echo "  ✅ EMAIL_NAME_MAPPING: 설정됨"
else
    echo "  ⚠️ EMAIL_NAME_MAPPING 환경변수가 설정되지 않음"
    echo "    python setup_email_env.py로 설정하세요"
fi

# 포트 사용 확인
echo ""
echo "🌐 네트워크 포트 확인:"
API_PORT=${API_PORT:-8080}
if lsof -i:$API_PORT >/dev/null 2>&1; then
    echo "  ⚠️ 포트 $API_PORT 이미 사용 중"
    echo "    다른 포트를 사용하려면: export API_PORT=다른포트번호"
else
    echo "  ✅ 포트 $API_PORT 사용 가능"
fi

echo ""
echo "🔧 API 서버 설정:"
echo "  - 호스트: ${API_HOST:-0.0.0.0}"
echo "  - 포트: ${API_PORT:-8080}"
echo "  - 업로드 경로: /api/v1/stt/upload"
echo "  - 상태 조회: /api/v1/stt/status/{task_id}"
echo "  - API 문서: http://localhost:${API_PORT:-8080}/docs"

echo ""
echo "🚀 API 서버 시작 중..."
echo "   Ctrl+C로 종료할 수 있습니다"
echo ""

# 가상환경 활성화 (uv 사용)
if [ -f "uv.lock" ]; then
    echo "📦 UV 가상환경 활성화 중..."
    export PYTHONPATH=$(pwd):$PYTHONPATH
else
    echo "⚠️ uv.lock 파일이 없습니다. uv sync를 먼저 실행하세요."
fi

# API 서버 실행
exec uv run python api_server.py