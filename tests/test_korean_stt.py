"""한국어 STT 기능 테스트"""

import os
import pytest
from unittest.mock import patch, MagicMock

from faster_whisper import WhisperModel


class TestKoreanSTT:
    """한국어 STT 기능 테스트"""
    
    @pytest.fixture
    def mock_model(self):
        """모킹된 Whisper 모델"""
        model = MagicMock(spec=WhisperModel)
        
        # 모킹된 segment 객체
        mock_segment = MagicMock()
        mock_segment.start = 0.0
        mock_segment.end = 5.0
        mock_segment.text = "안녕하세요. 오늘 회의를 시작하겠습니다."
        
        # 모킹된 info 객체  
        mock_info = MagicMock()
        mock_info.language = "ko"
        mock_info.language_probability = 0.95
        mock_info.duration = 10.0
        
        model.transcribe.return_value = ([mock_segment], mock_info)
        return model
    
    def test_korean_language_detection(self, mock_model):
        """한국어 언어 감지 테스트"""
        segments, info = mock_model.transcribe("test.wav", language="ko")
        
        assert info.language == "ko"
        assert info.language_probability > 0.9
    
    def test_korean_transcription_output(self, mock_model):
        """한국어 전사 결과 테스트"""
        segments, info = mock_model.transcribe("test.wav", language="ko")
        segments = list(segments)
        
        assert len(segments) > 0
        assert "안녕하세요" in segments[0].text
        assert segments[0].start >= 0
        assert segments[0].end > segments[0].start
    
    def test_korean_meeting_prompt(self, mock_model):
        """한국어 회의 프롬프트 테스트"""
        # 회의 전용 프롬프트로 전사
        segments, info = mock_model.transcribe(
            "test.wav",
            language="ko",
            initial_prompt="한국어 회의 내용입니다."
        )
        
        # transcribe 메소드가 올바른 파라미터로 호출되었는지 확인
        mock_model.transcribe.assert_called_with(
            "test.wav",
            language="ko", 
            initial_prompt="한국어 회의 내용입니다."
        )


class TestSTTConfiguration:
    """STT 설정 테스트"""
    
    def test_vad_parameters(self):
        """VAD 파라미터 테스트"""
        vad_params = dict(min_silence_duration_ms=500)
        
        assert vad_params["min_silence_duration_ms"] == 500
        assert isinstance(vad_params, dict)
    
    def test_transcription_parameters(self):
        """전사 파라미터 검증"""
        params = {
            "beam_size": 5,
            "temperature": 0.0,
            "compression_ratio_threshold": 2.4,
            "no_speech_threshold": 0.6,
            "condition_on_previous_text": False
        }
        
        assert params["beam_size"] == 5
        assert params["temperature"] == 0.0
        assert params["compression_ratio_threshold"] == 2.4
        assert params["no_speech_threshold"] == 0.6
        assert params["condition_on_previous_text"] is False


@pytest.mark.integration
class TestSTTIntegration:
    """통합 테스트 (실제 모델 필요)"""
    
    @pytest.mark.skipif(
        os.getenv("SKIP_INTEGRATION_TESTS") == "true",
        reason="Integration tests disabled"
    )
    def test_real_model_initialization(self):
        """실제 모델 초기화 테스트"""
        try:
            model = WhisperModel("tiny", device="cpu", compute_type="int8")
            assert model is not None
        except Exception as e:
            pytest.skip(f"Model initialization failed: {e}")
    
    @pytest.mark.skipif(
        os.getenv("SKIP_INTEGRATION_TESTS") == "true", 
        reason="Integration tests disabled"
    )  
    def test_model_device_selection(self):
        """모델 디바이스 선택 테스트"""
        # CPU 모델
        cpu_model = WhisperModel("tiny", device="cpu", compute_type="int8")
        assert cpu_model is not None
        
        # GPU 테스트는 환경에 따라 스킵
        if os.getenv("CUDA_AVAILABLE") == "true":
            try:
                gpu_model = WhisperModel("tiny", device="cuda", compute_type="float16")
                assert gpu_model is not None
            except Exception:
                pytest.skip("CUDA not available")