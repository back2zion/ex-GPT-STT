import os
import pytest
from unittest.mock import MagicMock


@pytest.fixture
def data_dir():
    """테스트 데이터 디렉토리"""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


@pytest.fixture
def jfk_path(data_dir):
    """JFK 연설 오디오 파일 경로 (영어)"""
    return os.path.join(data_dir, "jfk.flac")


@pytest.fixture
def physicsworks_path(data_dir):
    """Physics Works 오디오 파일 경로"""
    return os.path.join(data_dir, "physicsworks.wav")


@pytest.fixture
def multilingual_path(data_dir):
    """다국어 오디오 파일 경로"""
    return os.path.join(data_dir, "multilingual.mp3")


@pytest.fixture
def sample_korean_audio(data_dir):
    """한국어 샘플 오디오 (존재한다면)"""
    korean_file = os.path.join(data_dir, "korean_sample.wav")
    if os.path.exists(korean_file):
        return korean_file
    else:
        pytest.skip("Korean sample audio not available")


@pytest.fixture
def mock_whisper_model():
    """모킹된 WhisperModel"""
    model = MagicMock()
    
    # 기본 한국어 응답 설정
    mock_segment = MagicMock()
    mock_segment.start = 0.0
    mock_segment.end = 10.0
    mock_segment.text = "안녕하세요. 테스트 음성입니다."
    
    mock_info = MagicMock()
    mock_info.language = "ko"
    mock_info.language_probability = 0.95
    mock_info.duration = 10.0
    
    model.transcribe.return_value = ([mock_segment], mock_info)
    return model


@pytest.fixture
def sample_meeting_transcription():
    """샘플 회의 전사 내용"""
    return """
    안녕하세요, 오늘 프로젝트 진행 상황에 대해 이야기하겠습니다.
    현재 설계 단계가 거의 완료되었고, 개발 시작 준비가 되었습니다.
    예산 관련해서는 추가 논의가 필요합니다.
    다음 주까지 최종 계획을 수립하겠습니다.
    """


@pytest.fixture
def sample_ai_analysis():
    """샘플 AI 분석 결과"""
    return {
        'topic': '프로젝트 진행 상황 회의',
        'discussions': [
            '설계 단계 거의 완료',
            '개발 준비 완료'
        ],
        'decisions': [
            '다음 주까지 최종 계획 수립'
        ],
        'issues': [
            '예산 관련 추가 논의 필요'
        ],
        'plans': [
            '최종 계획 수립',
            '개발 단계 진입'
        ]
    }


# 환경 설정
@pytest.fixture(autouse=True)
def setup_test_environment():
    """테스트 환경 설정"""
    os.environ["SKIP_INTEGRATION_TESTS"] = os.getenv("SKIP_INTEGRATION_TESTS", "false")
    os.environ["CUDA_AVAILABLE"] = os.getenv("CUDA_AVAILABLE", "false")
    
    yield
    
    # 테스트 후 정리
    # 필요시 임시 파일 정리 등


# 마커 설정
def pytest_configure(config):
    """pytest 마커 설정"""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test (may be slow)"
    )
    config.addinivalue_line(
        "markers", "gpu: mark test as requiring GPU"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
