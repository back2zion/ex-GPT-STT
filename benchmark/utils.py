import logging
import os

from threading import Thread
from typing import Optional

from faster_whisper import WhisperModel

# 벤치마크 설정
model_path = os.getenv("BENCHMARK_MODEL", "large-v3")
device = os.getenv("BENCHMARK_DEVICE", "cuda")
compute_type = os.getenv("BENCHMARK_COMPUTE_TYPE", "float16")

# 모델 초기화 (지연 로딩)
model = None

def get_model():
    global model
    if model is None:
        print(f"Loading {model_path} model on {device} with {compute_type}...")
        model = WhisperModel(model_path, device=device, compute_type=compute_type)
    return model


def inference(audio_file="benchmark.m4a", language="ko"):
    """한국어 STT 추론"""
    model = get_model()
    segments, info = model.transcribe(
        audio_file, 
        language=language,
        beam_size=5,
        vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=500),
        temperature=0.0,
        compression_ratio_threshold=2.4,
        no_speech_threshold=0.6,
        condition_on_previous_text=False,
        initial_prompt="한국어 회의 내용입니다."
    )
    
    transcription = ""
    for segment in segments:
        print("[%.2fs -> %.2fs] %s" % (segment.start, segment.end, segment.text))
        transcription += segment.text.strip() + " "
    
    return transcription.strip(), info


def get_logger(name: Optional[str] = None) -> logging.Logger:
    formatter = logging.Formatter("%(levelname)s: %(message)s")
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


class MyThread(Thread):
    def __init__(self, func, params):
        super(MyThread, self).__init__()
        self.func = func
        self.params = params
        self.result = None

    def run(self):
        self.result = self.func(*self.params)

    def get_result(self):
        return self.result
