# Ex-GPT STT: AI-Powered Meeting Minutes Generator

**Ex-GPT STT**는 Faster Whisper와 AI 분석을 결합하여 음성을 텍스트로 변환하고 구조화된 회의록을 자동으로 생성하며, 이메일로 송부까지 자동화하는 종합 솔루션입니다.

## 🌟 주요 기능

### 🎯 핵심 기능
- **고성능 STT (Speech-to-Text)**: Faster Whisper 기반 음성 인식
- **한국어 후처리**: 전문 용어 및 고유명사 보정
- **AI 회의록 생성**: Ollama Qwen3-8B 모델을 활용한 구조화된 회의록 자동 생성
- **이메일 자동 발송**: 생성된 회의록을 참석자에게 자동 이메일 발송
- **API 서버**: RESTful API를 통한 모바일/웹 연동 지원

### 🚀 사용자 인터페이스
- **GUI 애플리케이션**: 드래그 앤 드롭 지원 데스크톱 앱
- **웹 대시보드**: 관리자용 모니터링 대시보드
- **API 엔드포인트**: 외부 시스템과의 연동

## 📋 프로젝트 구성

### 핵심 파일
- **`app.py`**: GUI 기반 통합 STT 및 회의록 생성 애플리케이션
- **`api_server.py`**: FastAPI 기반 REST API 서버
- **`stt_simple.py`**: 명령행 기반 간단한 STT 변환 도구
- **`email_utils.py`**: 이메일 발송 및 주소 관리 유틸리티
- **`speaker_diarization.py`**: 화자 분리 처리 모듈

### 처리 흐름
1. **음성 인식**: Faster Whisper를 사용한 고정밀도 STT
2. **텍스트 후처리**: 한국어 전문용어 및 고유명사 보정
3. **AI 분석**: Qwen3-8B 모델을 통한 내용 구조화
4. **회의록 생성**: PDF 템플릿 형식의 회의록 자동 생성


## 🚀 빠른 시작

### 설치 요구사항

* **Python 3.10 이상**
* **uv**: 고속 Python 패키지 매니저
* **Ollama**: Qwen3-8B 모델 실행을 위한 로컬 AI 서버
* **드래그 앤 드롭 라이브러리**: GUI 지원

### 설치 방법

1. **uv 설치**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"
```

2. **저장소 클론**
```bash
git clone https://github.com/back2zion/ex-GPT-STT.git
cd ex-GPT-STT
```

3. **가상환경 설정 및 의존성 설치**
```bash
uv sync
```

4. **Ollama 설치 및 모델 다운로드**
```bash
# Ollama 설치 (https://ollama.ai/)
curl -fsSL https://ollama.ai/install.sh | sh

# Qwen3-8B 모델 다운로드 (빠른 성능)
ollama pull qwen3:8b
```

### 사용법

#### 1. GUI 애플리케이션 (권장)
```bash
uv run python app.py
```
- 드래그 앤 드롭으로 오디오 파일 추가
- 자동 STT 처리, 회의록 생성, 이메일 발송

#### 2. API 서버 실행
```bash
# API 서버 시작
uv run python api_server.py

# 또는 스크립트 사용
./start_api_server.sh
```

#### 3. 명령행 STT 변환
```bash
uv run python stt_simple.py audio_file.wav
```

#### 4. 웹 대시보드 접속
- API 서버 실행 후 `http://localhost:8081/dashboard` 접속
- 업로드 및 처리 현황 모니터링

## 🔧 고급 기능

### 화자 분리 (Speaker Diarization)
Ex-GPT STT는 두 가지 화자 분리 방식을 지원합니다:

#### 🎯 실제 음성 특성 기반 화자 분리 (권장)
```bash
# pyannote.audio 설치
uv sync --extra diarization

# Hugging Face 토큰 설정 (https://huggingface.co/settings/tokens 에서 생성)
export HF_TOKEN="your_token_here"

# 또는 huggingface-cli 사용
huggingface-cli login --token your_token_here
```

**특징:**
- 실제 음성 특징 분석으로 정확한 화자 구분
- 자동 화자 수 감지 또는 수동 지정 가능
- GPU 가속 지원으로 빠른 처리
- NumPy 1.x 호환성 (NumPy 2.0+ 대응)

#### ⏰ 시간 기반 간단 화자 구분 (기본)
- 5초 이상 공백시 화자 변경으로 간주
- 추가 설치 없이 즉시 사용 가능
- 최대 4명까지 순환 배치

### STT 후처리
- **용어 사전 기반 보정**: 설정된 참조 디렉터리의 용어집 파일들을 활용한 자동 보정
- **전문 용어 및 고유명사 자동 수정**
- **맞춤법 및 표기법 표준화**

### 회의록 템플릿
회의록은 다음 구조로 생성됩니다:
- **기본 정보**: 일시, 장소, 회의주제, 참석자, 작성자
- **회의 내용**: 구조화된 주요 내용 (번호 매김 + 불릿 포인트)
- **이슈사항**: 미결사항 정리
- **첨부파일**: 관련 자료 목록

### API 사용법

#### 기본 STT 처리
```python
from faster_whisper import WhisperModel

model = WhisperModel("large-v3", device="cuda", compute_type="float16")
segments, info = model.transcribe("audio.mp3", beam_size=5, language="ko")

for segment in segments:
    print(f"[{segment.start:.2f}s -> {segment.end:.2f}s] {segment.text}")
```

#### AI 회의록 생성

**방법 1: Ollama 사용 (기본)**
```python
import requests

def generate_meeting_minutes(transcription_text):
    response = requests.post("http://localhost:11434/api/generate", json={
        "model": "qwen3:8b",
        "prompt": f"다음 회의 내용을 구조화된 회의록으로 작성해주세요:\n\n{transcription_text}",
        "stream": False
    })
    return response.json()["response"]
```

### 이메일 자동 발송 설정

이메일 기능을 위한 환경 설정:

#### 1. Gmail SMTP 설정 (권장)
```bash
# 이메일 환경 설정
uv run python setup_email_env.py

# Gmail 앱 비밀번호 설정
uv run python setup_gmail_smtp.py
```

#### 2. 환경 변수 설정 (.env 파일)
```bash
# Gmail 설정
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
EMAIL_ADDRESS=your_email@gmail.com
EMAIL_PASSWORD=your_app_password

# 회의록 참석자 이메일 매핑
SENDER_EMAIL_MAPPING={"김철수": "kim@company.com", "이영희": "lee@company.com"}
```

### API 서버 기능

#### 주요 엔드포인트
```bash
POST /upload-audio          # 오디오 파일 업로드 및 처리
GET  /processing-status/{id} # 처리 상태 확인  
GET  /download/{filename}    # 결과 파일 다운로드
POST /send-email            # 이메일 발송
GET  /dashboard             # 웹 대시보드 접속
```

#### API 사용 예시
```python
import requests
import json

# 오디오 파일 업로드
with open("meeting.mp3", "rb") as f:
    response = requests.post(
        "http://localhost:8081/upload-audio",
        files={"file": f},
        data={
            "meeting_title": "프로젝트 회의",
            "sender_email": "admin@company.com",
            "auto_send_email": "true"
        }
    )

result = response.json()
print(f"처리 ID: {result['processing_id']}")
```

## 🛠 개발 및 테스트

### 선택적 기능별 패키지 설치
```bash
# 개발 도구 (pytest, black, isort, flake8)
uv sync --extra dev

# GPU 가속 (CUDA 지원)
uv sync --extra gpu

# 실제 화자 분리 기능 (pyannote.audio)
uv sync --extra diarization

```

### 테스트 실행
```bash
# 전체 테스트 실행
uv run pytest tests/

# 특정 테스트 파일 실행
uv run pytest tests/test_transcribe.py -v
```

### 코드 품질 검사
```bash
# 코드 포맷팅
uv run black .
uv run isort .

# 린터 실행
uv run flake8 .
```

## 📝 라이선스

이 프로젝트는 [MIT 라이선스](LICENSE)를 따릅니다.

## 🙏 감사의 말

- **[SYSTRAN/faster-whisper](https://github.com/SYSTRAN/faster-whisper)**: 고성능 Whisper 구현
- **[Ollama](https://ollama.ai/)**: 로컬 AI 모델 실행 환경
- **Qwen3-8B**: 회의록 생성을 위한 AI 모델

## 🤝 기여하기

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📞 문의

문의사항이나 버그 리포트는 [Issues](https://github.com/back2zion/ex-GPT-STT/issues)를 통해 남겨주세요.

---

> **참고**: 이 프로젝트는 회의록 자동화를 위한 실험적 도구입니다. 중요한 회의의 경우 생성된 회의록을 검토하고 수정하여 사용하시기 바랍니다.
