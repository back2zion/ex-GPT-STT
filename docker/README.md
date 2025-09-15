# Docker 배포 가이드

Docker를 사용하여 Ex-GPT STT를 컨테이너 환경에서 실행할 수 있습니다.

## 🐳 구성 요소

### 서비스
- **ex-gpt-stt**: 메인 STT 애플리케이션
- **ollama**: AI 회의록 생성용 Qwen3-32B 모델 서버

### 볼륨 매핑
- `./input`: 처리할 오디오 파일 디렉토리
- `./output`: 생성된 STT 결과 및 회의록 저장 디렉토리
- `ollama_data`: Ollama 모델 데이터 영구 저장

## 🚀 빠른 시작

### 1. 디렉토리 준비
```bash
cd docker/
mkdir -p input output
```

### 2. Docker Compose로 실행
```bash
# GPU 지원 환경에서 실행
docker compose up -d

# CPU만 사용하는 경우
DEVICE=cpu COMPUTE_TYPE=int8 docker compose up -d
```

### 3. Ollama 모델 다운로드
```bash
# 컨테이너 내부에서 모델 다운로드
docker exec -it ex-gpt-stt-ollama ollama pull qwen3:32b
```

### 4. 오디오 파일 처리
```bash
# input 디렉토리에 오디오 파일 복사
cp /path/to/your/audio.mp3 input/

# 처리 시작 (일회성)
docker exec -it ex-gpt-stt-app python3 docker_infer.py

# 또는 감시 모드로 실행 (새 파일 자동 처리)
docker exec -e WATCH_MODE=true -it ex-gpt-stt-app python3 docker_infer.py
```

## ⚙️ 환경 변수

### Whisper 설정
- `WHISPER_MODEL`: 모델 크기 (default: `large-v3`)
  - 옵션: `tiny`, `base`, `small`, `medium`, `large-v3`
- `DEVICE`: 처리 장치 (default: `cuda`)
  - 옵션: `cuda`, `cpu`
- `COMPUTE_TYPE`: 연산 타입 (default: `float16`)
  - GPU: `float16`, `int8`
  - CPU: `int8`, `float32`

### 실행 모드
- `WATCH_MODE`: 파일 감시 모드 (default: `false`)
  - `true`: 새 파일 자동 감지 및 처리
  - `false`: 일회성 처리

### Ollama 설정
- `OLLAMA_BASE_URL`: Ollama 서버 URL (default: `http://ollama:11434`)

## 📝 사용 예시

### 기본 실행
```bash
# 컨테이너 시작
docker compose up -d

# 오디오 파일 추가
cp meeting.mp3 input/

# 처리 실행
docker exec -it ex-gpt-stt-app python3 docker_infer.py

# 결과 확인
ls output/
# meeting_STT_20240315_143022.txt
# meeting_회의록_20240315_143022.md
```

### 감시 모드 (자동 처리)
```bash
# 감시 모드로 시작
docker exec -e WATCH_MODE=true -d ex-gpt-stt-app python3 docker_infer.py

# 파일 추가하면 자동으로 처리됨
cp new_audio.wav input/

# 로그 확인
docker logs -f ex-gpt-stt-app
```

### CPU 전용 실행
```bash
# CPU 설정으로 실행
DEVICE=cpu COMPUTE_TYPE=int8 docker compose up -d
```

## 🔧 커스텀 설정

### docker-compose.override.yml 생성
```yaml
version: '3.8'

services:
  ex-gpt-stt:
    environment:
      - WHISPER_MODEL=medium  # 더 빠른 모델 사용
      - WATCH_MODE=true       # 자동 감시 모드
    volumes:
      - /your/custom/input:/app/input:ro
      - /your/custom/output:/app/output
```

## 📊 모니터링

### 컨테이너 상태 확인
```bash
# 전체 서비스 상태
docker compose ps

# 로그 확인
docker compose logs -f

# 개별 서비스 로그
docker logs -f ex-gpt-stt-app
docker logs -f ex-gpt-stt-ollama
```

### 리소스 사용량
```bash
# CPU/메모리 사용량
docker stats

# GPU 사용량 (nvidia-smi 필요)
nvidia-smi
```

## 🚨 트러블슈팅

### GPU 인식 안됨
```bash
# NVIDIA Container Toolkit 설치 확인
docker run --rm --gpus all nvidia/cuda:12.3.2-base-ubuntu22.04 nvidia-smi
```

### Ollama 연결 실패
```bash
# Ollama 서비스 상태 확인
docker exec ex-gpt-stt-ollama ollama list

# 수동 모델 다운로드
docker exec -it ex-gpt-stt-ollama ollama pull qwen3:32b
```

### 메모리 부족
```bash
# 더 작은 모델 사용
WHISPER_MODEL=base docker compose up -d

# CPU 모드로 변경
DEVICE=cpu COMPUTE_TYPE=int8 docker compose up -d
```

## 🧹 정리

```bash
# 컨테이너 중지 및 제거
docker compose down

# 볼륨까지 완전 삭제
docker compose down -v

# 이미지 정리
docker image prune -f
```