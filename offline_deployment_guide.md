# 내부망 배포 가이드

## 1. 현재 시스템 (Ollama 기반)
- **장점**: 안정적, 설치 간단, 32B 모델 지원
- **단점**: 단일 GPU만 사용

### 배포 준비물
```bash
# 필수 패키지 (offline wheel 다운로드)
pip download -r requirements.txt --dest ./offline_packages

# Ollama 설치 파일
curl -fsSL https://ollama.com/install.sh > ollama_install.sh

# 모델 파일 (사전 다운로드)
ollama pull qwen2.5:32b
# ~/.ollama/models 디렉터리 전체 백업
```

## 2. vLLM 기반 시스템 (내부망 필수)

### A. vLLM 오프라인 설치
```bash
# 현재 환경에서 wheel 다운로드
pip download vllm --dest ./vllm_offline
pip download torch --dest ./vllm_offline  
pip download transformers --dest ./vllm_offline

# 내부망에서 설치
pip install --no-index --find-links ./vllm_offline vllm
```

### B. 듀얼 GPU 설정
```python
# 텐서 병렬처리 설정
from vllm import LLM, SamplingParams

llm = LLM(
    model="Qwen/Qwen2.5-32B-Instruct",
    tensor_parallel_size=2,  # 듀얼 GPU
    gpu_memory_utilization=0.85,
    dtype="float16"
)
```

### C. 모델 파일 준비
```bash
# HuggingFace 모델 다운로드 (외부망에서)
git clone https://huggingface.co/Qwen/Qwen2.5-32B-Instruct
# 또는
huggingface-cli download Qwen/Qwen2.5-32B-Instruct --local-dir ./models/qwen2.5-32b

# 내부망에서 로컬 경로 사용
llm = LLM(model="./models/qwen2.5-32b", tensor_parallel_size=2)
```

## 3. 전환 전략

### Phase 1: 현재 Ollama 시스템 완성
- ✅ 안정적인 32B 모델 동작
- ✅ 회의록 품질 검증
- ✅ 전체 파이프라인 테스트

### Phase 2: vLLM 병렬 구축  
- 🔄 오프라인 설치 패키지 준비
- 🔄 듀얼 GPU 설정 및 테스트
- 🔄 성능 비교 및 최적화

### Phase 3: 내부망 배포
- 🔄 모든 의존성 오프라인 패키지화
- 🔄 설치 스크립트 자동화
- 🔄 운영 환경 검증

## 4. 권장 사항

**단기**: 현재 Ollama 기반 시스템으로 배포
- 안정성이 검증됨
- 32B 모델로 충분한 성능
- 빠른 배포 가능

**중기**: vLLM 전환 준비
- 오프라인 설치 환경 구축
- 듀얼 GPU 활용으로 2배 성능 향상
- 배치 처리 최적화

이 접근법으로 내부망 환경에서도 안정적으로 운영할 수 있습니다.