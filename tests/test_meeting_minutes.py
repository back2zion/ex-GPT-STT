"""회의록 생성 기능 테스트"""

import pytest
from unittest.mock import patch, MagicMock
import json


class TestMeetingMinutesGeneration:
    """회의록 생성 테스트"""
    
    @pytest.fixture
    def sample_transcription(self):
        """샘플 전사 내용"""
        return """
        안녕하세요. 오늘 프로젝트 진행 상황에 대해 논의하겠습니다. 
        현재 설계가 80% 완료되었고, 퍼블리싱 작업도 시작되었습니다.
        다음 주까지 개발 일정을 확정해야 합니다.
        이슈사항으로는 일부 API 연동에서 지연이 발생하고 있습니다.
        """
    
    @pytest.fixture 
    def mock_ollama_response(self):
        """모킹된 Ollama API 응답"""
        return {
            "response": """
            1. 회의 주제: 프로젝트 진행 상황 검토
            2. 주요 논의사항:
               - 설계 진행률 80% 달성
               - 퍼블리싱 작업 착수
            3. 결정사항:
               - 다음 주까지 개발 일정 확정
            4. 이슈/문제점:
               - API 연동 지연 발생
            5. 향후 계획:
               - 개발 팀과 일정 조율
            """
        }
    
    def test_ai_response_parsing(self, mock_ollama_response):
        """AI 응답 파싱 테스트"""
        from stt_simple import parse_ai_response
        
        ai_response = mock_ollama_response["response"]
        analysis = parse_ai_response(ai_response)
        
        assert analysis["topic"] == "프로젝트 진행 상황 검토"
        assert len(analysis["discussions"]) > 0
        assert "설계 진행률 80% 달성" in analysis["discussions"]
        assert len(analysis["issues"]) > 0
        assert "API 연동 지연 발생" in analysis["issues"]
    
    @patch('requests.post')
    def test_ollama_api_call(self, mock_post, sample_transcription):
        """Ollama API 호출 테스트"""
        from stt_simple import analyze_with_ai
        
        # 모킹된 응답 설정
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": "1. 회의 주제: 테스트 회의"
        }
        mock_post.return_value = mock_response
        
        # API 호출 테스트
        result = analyze_with_ai(sample_transcription)
        
        # API가 올바르게 호출되었는지 확인
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        
        assert call_args[0][0] == "http://localhost:11434/api/generate"
        assert "model" in call_args[1]["json"]
        assert call_args[1]["json"]["model"] == "qwen3:32b"
        assert "prompt" in call_args[1]["json"]
        assert sample_transcription in call_args[1]["json"]["prompt"]
    
    @patch('requests.post')
    def test_ollama_api_failure(self, mock_post, sample_transcription):
        """Ollama API 실패 처리 테스트"""
        from stt_simple import analyze_with_ai, create_simple_analysis
        
        # API 실패 시뮬레이션
        mock_post.side_effect = Exception("Connection failed")
        
        # 대체 분석 결과 반환되는지 테스트
        result = analyze_with_ai(sample_transcription)
        
        # 기본 분석 구조가 반환되는지 확인
        expected_keys = ['topic', 'discussions', 'decisions', 'issues', 'plans']
        for key in expected_keys:
            assert key in result
            assert isinstance(result[key], (str, list))
    
    def test_simple_analysis_fallback(self):
        """간단 분석 대체 기능 테스트"""
        from stt_simple import create_simple_analysis
        
        analysis = create_simple_analysis()
        
        # 필수 키 존재 확인
        required_keys = ['topic', 'discussions', 'decisions', 'issues', 'plans']
        for key in required_keys:
            assert key in analysis
        
        # 각 섹션에 기본값이 있는지 확인
        assert isinstance(analysis['topic'], str)
        assert len(analysis['topic']) > 0
        
        for key in ['discussions', 'decisions', 'issues', 'plans']:
            assert isinstance(analysis[key], list)
            assert len(analysis[key]) > 0


class TestDocumentGeneration:
    """문서 생성 테스트"""
    
    @pytest.fixture
    def sample_analysis(self):
        """샘플 분석 결과"""
        return {
            'topic': '프로젝트 진행 상황 회의',
            'discussions': [
                '설계 진행률 80% 달성',
                '퍼블리싱 작업 시작'
            ],
            'decisions': [
                '다음 주까지 개발 일정 확정'
            ],
            'issues': [
                'API 연동 지연'
            ],
            'plans': [
                '개발팀과 일정 조율'
            ]
        }
    
    def test_docx_structure_creation(self, sample_analysis, tmp_path):
        """DOCX 구조 생성 테스트"""
        from stt_simple import create_docx_structure
        import os
        
        temp_dir = str(tmp_path)
        base_name = "test_meeting"
        
        # DOCX 구조 생성
        create_docx_structure(temp_dir, sample_analysis, base_name)
        
        # 필수 파일들이 생성되었는지 확인
        assert os.path.exists(os.path.join(temp_dir, "[Content_Types].xml"))
        assert os.path.exists(os.path.join(temp_dir, "_rels", ".rels"))
        assert os.path.exists(os.path.join(temp_dir, "docProps", "core.xml"))
        assert os.path.exists(os.path.join(temp_dir, "word", "document.xml"))
        
        # document.xml 내용 확인
        with open(os.path.join(temp_dir, "word", "document.xml"), 'r', encoding='utf-8') as f:
            content = f.read()
            assert "프로젝트 진행 상황 회의" in content
            assert "설계 진행률 80% 달성" in content
            assert "API 연동 지연" in content


class TestErrorHandling:
    """에러 처리 테스트"""
    
    def test_empty_transcription_handling(self):
        """빈 전사 내용 처리 테스트"""
        from stt_simple import analyze_with_ai
        
        # 빈 전사 내용으로 테스트
        result = analyze_with_ai("")
        
        # 기본 분석이 반환되는지 확인
        assert "topic" in result
        assert isinstance(result["discussions"], list)
    
    def test_malformed_ai_response(self):
        """잘못된 AI 응답 처리 테스트"""
        from stt_simple import parse_ai_response
        
        # 형식이 맞지 않는 응답
        malformed_response = "이것은 형식이 맞지 않는 응답입니다."
        
        result = parse_ai_response(malformed_response)
        
        # 기본 구조는 유지되어야 함
        assert "topic" in result
        assert isinstance(result["discussions"], list)
        assert isinstance(result["decisions"], list)