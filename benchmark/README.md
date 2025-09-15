# 벤치마크 도구

Ex-GPT STT 프로젝트의 성능 벤치마크 및 평가 도구들입니다.

## 📊 벤치마크 종류

### 1. 속도 벤치마크 (`speed_benchmark.py`)
- STT 처리 속도 측정
- 다양한 모델 크기별 성능 비교
- GPU vs CPU 성능 차이 분석

### 2. 메모리 벤치마크 (`memory_benchmark.py`)
- 메모리 사용량 프로파일링
- 배치 처리시 메모리 효율성 측정

### 3. WER 벤치마크 (`wer_benchmark.py`)
- Word Error Rate 측정
- 한국어 전사 정확도 평가

## 🚀 사용법

### 기본 사용
```bash
# 속도 벤치마크 실행
uv run python benchmark/speed_benchmark.py

# 메모리 벤치마크 실행
uv run python benchmark/memory_benchmark.py

# WER 평가 실행
uv run python benchmark/wer_benchmark.py
```

### 벤치마크 의존성 설치
```bash
# 벤치마크용 추가 패키지 설치
uv add transformers jiwer datasets memory-profiler pytubefix
```

## 📈 벤치마크 결과 해석

### 속도 측정
- **Real-time Factor (RTF)**: 오디오 길이 대비 처리 시간
- RTF < 1.0 = 실시간보다 빠름
- RTF > 1.0 = 실시간보다 느림

### 메모리 사용량
- Peak Memory Usage: 최대 메모리 사용량
- Memory Efficiency: 오디오 시간당 메모리 사용량

### WER (Word Error Rate)
- 낮을수록 좋음 (0% = 완벽)
- 일반적으로 10% 이하면 양호

## 🎯 테스트 데이터

- `benchmark.m4a`: 표준 테스트 오디오 파일
- 한국어 회의 내용 샘플
- 약 1-2분 길이의 음성 데이터

## ⚙️ 설정 옵션

### 모델 설정
```python
# utils.py에서 모델 변경
model_path = "large-v3"  # tiny, base, small, medium, large-v3
device = "cuda"          # cuda, cpu
compute_type = "float16" # float16, int8, float32
```

### 벤치마크 반복 횟수
```bash
# 더 정확한 측정을 위해 반복 횟수 증가
python speed_benchmark.py --repeat 5
```

## 📋 벤치마크 체크리스트

성능 최적화 후 다음 항목들을 확인하세요:

- [ ] RTF < 0.5 (실시간의 절반 이하 처리 시간)
- [ ] 메모리 사용량 < 4GB (large-v3 모델 기준)
- [ ] WER < 15% (한국어 회의 내용 기준)
- [ ] GPU 활용률 > 80% (GPU 사용시)
- [ ] CPU 사용률 < 90% (CPU 병목 방지)

## 🔧 문제 해결

### CUDA 메모리 부족
```bash
# 작은 모델 사용
python -c "from utils import *; model_path = 'base'"

# 배치 크기 조정
# compute_type을 int8로 변경
```

### 속도 저하 문제
```bash
# GPU 사용 확인
nvidia-smi

# 모델 캐시 확인
ls ~/.cache/huggingface/hub/
```