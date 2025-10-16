#!/usr/bin/env python3

"""
STT 처리 모듈 (API 서버용)
기존 app.py의 STT 처리 로직을 API에서 사용할 수 있도록 분리
"""

import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import os
from datetime import datetime
import tempfile
from pathlib import Path
import traceback

# 기존 모듈들 임포트
try:
    from src.stt.app import (
        complete_transcription_and_minutes, 
        post_process_stt, 
        build_correction_dictionary,
        initialize_multi_gpu_whisper_model
    )
    from faster_whisper import WhisperModel
    STT_MODULES_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ STT 모듈 임포트 실패: {e}")
    STT_MODULES_AVAILABLE = False

def process_audio_to_meeting_minutes(
    audio_file_path: str,
    output_dir: str = None,
    meeting_title: str = None,
    sender_name: str = None,
    progress_callback=None
) -> dict:
    """
    오디오 파일을 처리하여 STT → 후처리 → 회의록 생성
    
    Args:
        audio_file_path: 오디오 파일 경로
        output_dir: 출력 디렉토리 (None이면 임시 디렉토리 사용)
        meeting_title: 회의 제목
        sender_name: 발신자 이름
        progress_callback: 진행 상황 콜백 함수
        
    Returns:
        dict: 처리 결과
        {
            "success": bool,
            "transcription": str,
            "meeting_minutes": str,
            "stt_file": str,
            "minutes_file": str,
            "duration": float,
            "language": str,
            "segment_count": int,
            "error": str (실패 시)
        }
    """
    
    if not STT_MODULES_AVAILABLE:
        return {
            "success": False,
            "error": "STT 모듈을 사용할 수 없습니다"
        }
    
    try:
        # 진행 상황 업데이트
        if progress_callback:
            progress_callback("STT 모델 로딩 중...")
        
        # 파일 검증
        if not os.path.exists(audio_file_path):
            return {
                "success": False,
                "error": f"오디오 파일을 찾을 수 없습니다: {audio_file_path}"
            }
        
        # 출력 디렉토리 설정
        if output_dir is None:
            output_dir = tempfile.mkdtemp(prefix="stt_api_")
        else:
            os.makedirs(output_dir, exist_ok=True)
        
        # 파일명 설정
        base_name = meeting_title or Path(audio_file_path).stem
        stt_output = os.path.join(output_dir, f"{base_name}_전사결과.txt")
        minutes_output = os.path.join(output_dir, f"{base_name}_회의록.txt")
        
        # 1. STT 처리
        if progress_callback:
            progress_callback("음성 전사 중...")
        
        print(f"🎤 STT 처리 시작: {os.path.basename(audio_file_path)}")
        
        # Whisper 모델 로드 및 전사
        model = WhisperModel(
            "large-v3", 
            device="cuda", 
            compute_type="float16",
            cpu_threads=1
        )
        
        segments, info = model.transcribe(
            audio_file_path,
            beam_size=3,
            language="ko",
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500),
            temperature=0.0,
            compression_ratio_threshold=2.4,
            no_speech_threshold=0.6,
            condition_on_previous_text=False,
            initial_prompt="한국어 회의 내용입니다.",
            chunk_length=30
        )
        
        # 세그먼트 리스트로 변환
        segments_list = list(segments)
        
        print(f"✅ STT 완료: {len(segments_list)}개 구간, {info.duration:.1f}초")
        
        # 2. 전사 텍스트 추출 및 후처리
        if progress_callback:
            progress_callback("텍스트 후처리 중...")
        
        # 전체 텍스트 추출
        full_text = " ".join([segment.text.strip() for segment in segments_list])
        
        # 한국어 후처리 적용
        corrected_text = post_process_korean_text(full_text)
        
        # 3. 화자 분리 (시간 기반)
        if progress_callback:
            progress_callback("화자 분리 중...")
        
        # 시간 기반 간단 화자 분리 적용
        segments_with_speakers = apply_speaker_diarization_time_based(segments_list)
        
        # 4. STT 결과 파일 생성
        if progress_callback:
            progress_callback("STT 결과 저장 중...")
        
        with open(stt_output, 'w', encoding='utf-8') as f:
            f.write(f"{base_name} - STT 결과\n")
            f.write(f"{datetime.now().strftime('%Y.%m.%d %H:%M')} ・ {info.duration:.0f}초\n")
            f.write(f"언어: {info.language} (확률: {info.language_probability:.1%})\n\n")
            
            for segment in segments_with_speakers:
                speaker_info = f"[{segment.get('speaker', 'Speaker')}] " if 'speaker' in segment else ""
                f.write(f"[{segment.start:.1f}s -> {segment.end:.1f}s]\n")
                f.write(f"{speaker_info}{segment.text.strip()}\n\n")
        
        print(f"📄 STT 파일 저장: {stt_output}")
        
        # 5. AI 회의록 분석
        if progress_callback:
            progress_callback("AI 회의록 생성 중...")
        
        print("🤖 AI 회의록 분석 시작...")
        meeting_analysis = analyze_meeting_with_ai(corrected_text)
        
        if not meeting_analysis:
            meeting_analysis = "AI 분석을 사용할 수 없어 기본 회의록을 생성합니다."
            print("⚠️ AI 분석 실패 - 기본 회의록 사용")
        else:
            print("✅ AI 회의록 분석 완료")
        
        # 6. 회의록 파일 생성
        if progress_callback:
            progress_callback("회의록 저장 중...")
        
        create_meeting_minutes_txt(
            minutes_output, 
            len(segments_list), 
            info, 
            meeting_analysis, 
            base_name,
            sender_name=sender_name
        )
        
        print(f"📋 회의록 파일 저장: {minutes_output}")
        
        # 7. 결과 반환
        result = {
            "success": True,
            "transcription": corrected_text,
            "meeting_minutes": meeting_analysis,
            "stt_file": stt_output,
            "minutes_file": minutes_output,
            "duration": info.duration,
            "language": info.language,
            "language_probability": info.language_probability,
            "segment_count": len(segments_list)
        }
        
        if progress_callback:
            progress_callback("처리 완료!")
        
        print(f"🎉 모든 처리 완료!")
        return result
        
    except Exception as e:
        error_msg = f"STT 처리 중 오류 발생: {str(e)}"
        print(f"❌ {error_msg}")
        print(f"상세 오류: {traceback.format_exc()}")
        
        return {
            "success": False,
            "error": error_msg,
            "error_details": traceback.format_exc()
        }

def test_stt_processor():
    """STT 프로세서 테스트"""
    print("🧪 STT 프로세서 테스트")
    print("=" * 50)
    
    if not STT_MODULES_AVAILABLE:
        print("❌ STT 모듈을 사용할 수 없습니다")
        return False
    
    # 테스트용 더미 오디오 파일 (실제 테스트시 진짜 오디오 파일 사용)
    test_audio = "/tmp/test_audio.wav"  # 실제 파일로 교체 필요
    
    if not os.path.exists(test_audio):
        print(f"❌ 테스트 오디오 파일이 없습니다: {test_audio}")
        print("💡 실제 오디오 파일 경로로 수정하여 테스트하세요.")
        return False
    
    # 진행 상황 콜백
    def progress_update(message):
        print(f"📊 {message}")
    
    # STT 처리 실행
    result = process_audio_to_meeting_minutes(
        audio_file_path=test_audio,
        meeting_title="테스트_회의",
        sender_name="테스트사용자",
        progress_callback=progress_update
    )
    
    # 결과 출력
    if result["success"]:
        print("\n✅ STT 처리 성공!")
        print(f"   전사 길이: {len(result['transcription'])}자")
        print(f"   회의록 길이: {len(result['meeting_minutes'])}자") 
        print(f"   음성 길이: {result['duration']:.1f}초")
        print(f"   언어: {result['language']}")
        print(f"   구간 수: {result['segment_count']}개")
        print(f"   STT 파일: {result['stt_file']}")
        print(f"   회의록 파일: {result['minutes_file']}")
        return True
    else:
        print("\n❌ STT 처리 실패!")
        print(f"   오류: {result['error']}")
        return False

if __name__ == "__main__":
    test_stt_processor()