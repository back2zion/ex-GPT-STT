# Contributing to Ex-GPT STT

Ex-GPT STT 프로젝트에 기여해 주셔서 감사합니다! 이 가이드는 개발 환경 설정부터 PR 제출까지의 과정을 안내합니다.

## 🚀 개발 환경 설정

### 1. 저장소 클론 및 의존성 설치

```bash
git clone https://github.com/back2zion/ex-GPT-STT.git
cd ex-GPT-STT/

# UV 패키지 매니저 사용 (권장)
uv sync --dev

# 또는 전통적인 pip 사용
pip install -e .
```

### 2. 개발 도구 설정

프로젝트는 다음 도구들을 사용합니다:

- **UV**: 빠른 Python 패키지 관리
- **Black**: 코드 포맷팅
- **isort**: import 정렬
- **flake8**: 코드 스타일 검사
- **pytest**: 테스트 실행

## 🔧 개발 워크플로우

### 1. 브랜치 생성

```bash
git checkout -b feature/your-feature-name
```

### 2. 코드 작성

프로젝트의 주요 구조:
- `stt_simple.py`: 핵심 STT + 회의록 생성 기능
- `app.py`: GUI 애플리케이션
- `faster_whisper/`: Whisper 모델 라이브러리
- `docker/`: 컨테이너화 설정
- `tests/`: 테스트 코드
- `benchmark/`: 성능 벤치마크

### 3. 코드 품질 검사

변경사항을 커밋하기 전에 다음 명령어들을 실행하세요:

```bash
# 코드 포맷팅
uv run black .
uv run isort .

# 코드 스타일 검사
uv run flake8 .

# 테스트 실행
uv run pytest tests/ -v

# 통합 테스트 (선택사항)
SKIP_INTEGRATION_TESTS=false uv run pytest tests/ -m integration
```

### 4. Docker 테스트 (선택사항)

```bash
# Docker 빌드 테스트
cd docker/
docker compose build

# 컨테이너 실행 테스트
docker compose up -d
```

## 📝 기여 유형

### 🐛 버그 수정

1. 이슈에서 버그를 확인하거나 새 이슈를 생성
2. 버그를 재현하는 테스트 작성
3. 수정 사항 구현
4. 테스트 통과 확인

### ✨ 새 기능 추가

1. 기능 제안 이슈 생성 및 논의
2. 기능 구현
3. 테스트 코드 작성
4. 문서 업데이트

### 📚 문서 개선

1. README, 가이드, 코드 주석 개선
2. 예제 코드 추가
3. API 문서 업데이트

### 🚀 성능 최적화

1. 벤치마크 실행하여 성능 기준 설정
2. 최적화 구현
3. 성능 개선 검증
4. 벤치마크 결과 공유

## 🧪 테스트 가이드

### 테스트 실행

```bash
# 전체 테스트
uv run pytest tests/

# 특정 테스트 파일
uv run pytest tests/test_korean_stt.py

# 특정 테스트 클래스
uv run pytest tests/test_meeting_minutes.py::TestMeetingMinutesGeneration

# 마커로 필터링
uv run pytest tests/ -m "not integration"  # 통합 테스트 제외
uv run pytest tests/ -m "gpu"              # GPU 테스트만
```

### 새 테스트 작성

```python
import pytest
from unittest.mock import MagicMock

def test_your_feature():
    """기능 테스트 설명"""
    # Given
    input_data = "test input"
    
    # When  
    result = your_function(input_data)
    
    # Then
    assert result is not None
    assert "expected" in result
```

## 🔍 코드 리뷰 기준

### 코드 품질

- [ ] 코드가 PEP 8 스타일 가이드를 따름
- [ ] 함수와 클래스에 docstring 작성
- [ ] 복잡한 로직에 주석 추가
- [ ] 하드코딩된 값 제거 (설정 파일 또는 상수 사용)

### 테스트

- [ ] 새 기능에 대한 테스트 추가
- [ ] 기존 테스트 통과
- [ ] 엣지 케이스 고려
- [ ] 모킹 적절히 사용

### 문서화

- [ ] README 업데이트 (필요시)
- [ ] 코드 주석 추가
- [ ] API 변경사항 문서화

### 성능

- [ ] 메모리 누수 확인
- [ ] 대용량 파일 처리 테스트
- [ ] 병목지점 최적화

## 📋 PR 체크리스트

PR을 생성하기 전에 다음 항목들을 확인하세요:

- [ ] 코드 포맷팅 완료 (`black`, `isort`)
- [ ] 코드 스타일 검사 통과 (`flake8`)
- [ ] 테스트 통과 (`pytest`)
- [ ] 의미 있는 커밋 메시지 작성
- [ ] PR 설명에 변경사항 상세히 기술
- [ ] 관련 이슈에 링크
- [ ] 문서 업데이트 (필요시)

## 🚨 주의사항

### 보안

- API 키나 민감한 정보를 커밋하지 마세요
- `.env` 파일이나 설정 파일을 통해 민감한 데이터 관리
- 외부 API 호출시 에러 처리 강화

### 성능

- 대용량 오디오 파일 처리시 메모리 사용량 고려
- GPU 메모리 부족 상황에 대한 예외 처리
- Ollama API 타임아웃 및 재시도 로직 구현

### 호환성

- Python 3.10+ 지원
- Windows, macOS, Linux 호환성 고려
- CUDA/CPU 모드 모두 지원

## 💬 소통

### 이슈 생성

- 버그 리포트: 재현 방법, 예상 결과, 실제 결과
- 기능 제안: 사용 사례, 구현 방안, 기대 효과
- 질문: 명확한 질문과 컨텍스트 제공

### PR 리뷰

- 건설적인 피드백 제공
- 코드 개선 제안시 구체적인 예시 포함
- 긍정적이고 협력적인 태도 유지

## 🎯 기여 우선순위

현재 프로젝트에서 특히 환영하는 기여 유형:

1. **한국어 STT 정확도 개선**
   - 전문 용어 사전 확장
   - 후처리 알고리즘 최적화

2. **회의록 생성 품질 향상**
   - AI 프롬프트 개선
   - 템플릿 다양화

3. **성능 최적화**
   - GPU 메모리 효율성 개선
   - 배치 처리 최적화

4. **사용성 개선**
   - GUI 개선
   - CLI 도구 기능 확장

5. **문서화**
   - 사용 가이드 개선
   - API 문서 작성

감사합니다! 🙏