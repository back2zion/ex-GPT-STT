#!/usr/bin/env python3
"""
화자 분리(Speaker Diarization) 기능
pyannote.audio를 사용한 실제 음성 특성 기반 화자 구분
"""

import os
import warnings
warnings.filterwarnings("ignore", category=UserWarning)

def perform_speaker_diarization(audio_file, num_speakers=None):
    """
    실제 화자 분리 수행
    
    Args:
        audio_file (str): 오디오 파일 경로
        num_speakers (int, optional): 예상 화자 수 (None이면 자동 감지)
    
    Returns:
        dict: 화자별 시간 구간 정보
    """
    try:
        from pyannote.audio import Pipeline
        import torch
        
        print("🎭 실제 음성 특성 기반 화자 분리 시작...")
        
        # GPU 사용 가능한지 확인
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"🔧 화자 분리 디바이스: {device}")
        
        # pyannote 파이프라인 로드
        print("📥 pyannote.audio 모델 로딩 중...")
        
        # Hugging Face 토큰 설정 (여러 방법 지원)
        hf_token = None
        
        # 1. 환경 변수에서 토큰 가져오기
        hf_token = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_TOKEN")
        
        # 2. 토큰이 없으면 사용자에게 안내
        if not hf_token:
            print("⚠️ Hugging Face 토큰이 설정되지 않았습니다.")
            print("💡 설정 방법:")
            print("   export HF_TOKEN='your_token_here'")
            print("   또는 huggingface-cli login")
            return None
        
        try:
            pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-3.1",
                use_auth_token=hf_token
            )
        except Exception as e:
            if "token" in str(e).lower() or "authentication" in str(e).lower():
                print(f"❌ 인증 오류: {e}")
                print("💡 해결 방법:")
                print("   1. 환경변수 설정: export HF_TOKEN='your_token_here'")
                print("   2. 또는 huggingface-cli login 실행")
                raise
            else:
                raise
        
        if device == "cuda":
            pipeline = pipeline.to(torch.device("cuda"))
        
        # 화자 분리 실행
        print(f"🎯 화자 분리 실행 중... (예상 화자 수: {num_speakers or '자동감지'})")
        
        diarization_params = {}
        if num_speakers:
            diarization_params["num_speakers"] = num_speakers
        
        diarization = pipeline(audio_file, **diarization_params)
        
        # 결과 처리
        speaker_segments = {}
        
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            speaker_id = f"화자{speaker.split('_')[-1] if '_' in speaker else speaker}"
            
            if speaker_id not in speaker_segments:
                speaker_segments[speaker_id] = []
            
            speaker_segments[speaker_id].append({
                'start': turn.start,
                'end': turn.end,
                'duration': turn.end - turn.start
            })
        
        print(f"✅ 화자 분리 완료! 감지된 화자 수: {len(speaker_segments)}")
        
        # 화자별 통계
        for speaker, segments in speaker_segments.items():
            total_time = sum(seg['duration'] for seg in segments)
            print(f"   📊 {speaker}: {len(segments)}개 구간, 총 {total_time:.1f}초")
        
        return speaker_segments
        
    except ImportError:
        print("⚠️ pyannote.audio가 설치되지 않았습니다.")
        print("   실행 명령: uv sync --extra diarization")
        return None
        
    except Exception as e:
        print(f"❌ 화자 분리 실패: {str(e)}")
        if "token" in str(e).lower():
            print("💡 Hugging Face 토큰이 필요할 수 있습니다:")
            print("   1. https://huggingface.co/settings/tokens 에서 토큰 생성")
            print("   2. huggingface-cli login 실행")
        return None


def apply_speaker_diarization_to_transcription(segments_list, speaker_segments):
    """
    STT 결과에 화자 정보 적용
    
    Args:
        segments_list: STT 세그먼트 리스트
        speaker_segments: 화자 분리 결과
    
    Returns:
        list: 화자 정보가 포함된 세그먼트 리스트
    """
    if not speaker_segments:
        return segments_list
    
    print("🔗 STT 결과와 화자 정보 연결 중...")
    
    # 화자 정보를 시간 순으로 정렬
    speaker_timeline = []
    for speaker, segments in speaker_segments.items():
        for segment in segments:
            speaker_timeline.append({
                'speaker': speaker,
                'start': segment['start'],
                'end': segment['end']
            })
    
    speaker_timeline.sort(key=lambda x: x['start'])
    
    # STT 세그먼트에 화자 정보 매핑
    enhanced_segments = []
    
    for segment in segments_list:
        segment_start = segment.start
        segment_end = segment.end
        
        # 가장 겹치는 화자 찾기
        best_speaker = "화자1"  # 기본값
        max_overlap = 0
        
        for speaker_info in speaker_timeline:
            # 겹치는 구간 계산
            overlap_start = max(segment_start, speaker_info['start'])
            overlap_end = min(segment_end, speaker_info['end'])
            overlap = max(0, overlap_end - overlap_start)
            
            if overlap > max_overlap:
                max_overlap = overlap
                best_speaker = speaker_info['speaker']
        
        # 세그먼트에 화자 정보 추가
        enhanced_segment = type('EnhancedSegment', (), {
            'start': segment.start,
            'end': segment.end,
            'text': segment.text,
            'speaker': best_speaker
        })()
        
        enhanced_segments.append(enhanced_segment)
    
    # 화자별 통계
    speaker_counts = {}
    for seg in enhanced_segments:
        speaker = seg.speaker
        speaker_counts[speaker] = speaker_counts.get(speaker, 0) + 1
    
    print("📊 STT-화자 매핑 완료:")
    for speaker, count in speaker_counts.items():
        print(f"   {speaker}: {count}개 세그먼트")
    
    return enhanced_segments


def simple_time_based_diarization(segments_list, gap_threshold=5.0, max_speakers=4):
    """
    간단한 시간 기반 화자 구분 (기존 방식)
    
    Args:
        segments_list: STT 세그먼트 리스트  
        gap_threshold: 화자 변경으로 간주할 최소 공백 시간(초)
        max_speakers: 최대 화자 수
    
    Returns:
        list: 화자 정보가 포함된 세그먼트 리스트
    """
    print(f"🕐 시간 기반 간단 화자 구분 (공백 {gap_threshold}초 기준)")
    
    current_speaker_num = 1
    enhanced_segments = []
    
    for i, segment in enumerate(segments_list):
        # 이전 세그먼트와 공백이 큰 경우 화자 변경
        if i > 0:
            prev_segment = segments_list[i-1]
            gap = segment.start - prev_segment.end
            
            if gap > gap_threshold:
                current_speaker_num += 1
                if current_speaker_num > max_speakers:
                    current_speaker_num = 1
        
        speaker = f"화자{current_speaker_num}"
        
        # 세그먼트에 화자 정보 추가
        enhanced_segment = type('EnhancedSegment', (), {
            'start': segment.start,
            'end': segment.end, 
            'text': segment.text,
            'speaker': speaker
        })()
        
        enhanced_segments.append(enhanced_segment)
    
    # 통계
    speaker_counts = {}
    for seg in enhanced_segments:
        speaker = seg.speaker
        speaker_counts[speaker] = speaker_counts.get(speaker, 0) + 1
    
    print("📊 시간 기반 화자 구분 완료:")
    for speaker, count in speaker_counts.items():
        print(f"   {speaker}: {count}개 세그먼트")
    
    return enhanced_segments


if __name__ == "__main__":
    # 테스트 코드
    import sys
    
    if len(sys.argv) != 2:
        print("사용법: python speaker_diarization.py <audio_file>")
        sys.exit(1)
    
    audio_file = sys.argv[1]
    
    if not os.path.exists(audio_file):
        print(f"파일을 찾을 수 없습니다: {audio_file}")
        sys.exit(1)
    
    # 화자 분리 테스트
    speaker_segments = perform_speaker_diarization(audio_file)
    
    if speaker_segments:
        print("\n🎭 화자 분리 결과:")
        for speaker, segments in speaker_segments.items():
            print(f"\n{speaker}:")
            for i, seg in enumerate(segments[:3]):  # 처음 3개만 표시
                print(f"  {i+1}. {seg['start']:.1f}s - {seg['end']:.1f}s ({seg['duration']:.1f}s)")
            if len(segments) > 3:
                print(f"  ... 총 {len(segments)}개 구간")
    else:
        print("화자 분리를 사용할 수 없습니다. 시간 기반 구분을 사용하세요.")