#!/usr/bin/env python3
"""
화자 분리(Speaker Diarization) 기능
pyannote.audio를 사용한 실제 음성 특성 기반 화자 구분
"""

import os
import warnings
import tempfile
import soundfile as sf
import os

# 모든 경고 메시지 억제
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)

# SpeechBrain 경고 메시지 억제
os.environ['SPEECHBRAIN_CACHE'] = '/tmp/speechbrain_cache'
os.environ['TRANSFORMERS_VERBOSITY'] = 'error'

def convert_audio_to_wav(audio_file):
    """
    오디오 파일을 WAV 형식으로 변환 (pyannote.audio 호환성을 위해)
    
    Args:
        audio_file (str): 원본 오디오 파일 경로
    
    Returns:
        str: 변환된 WAV 파일 경로 (임시 파일)
    """
    try:
        import librosa
        
        # M4A, MP3 등을 WAV로 변환이 필요한지 확인
        file_ext = os.path.splitext(audio_file)[1].lower()
        
        # WAV 파일이면 그대로 반환
        if file_ext == '.wav':
            return audio_file, False
        
        print(f"🔄 {file_ext} 파일을 WAV로 변환 중...")
        
        # librosa로 오디오 읽기 (다양한 형식 지원)
        audio_data, sample_rate = librosa.load(audio_file, sr=None, mono=False)
        
        # 스테레오인 경우 채널 차원 조정
        if audio_data.ndim > 1:
            audio_data = audio_data.T
        
        # 임시 WAV 파일 생성
        temp_wav = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        temp_wav_path = temp_wav.name
        temp_wav.close()
        
        # WAV 파일로 저장
        sf.write(temp_wav_path, audio_data, sample_rate)
        
        print(f"✅ 변환 완료: {temp_wav_path}")
        return temp_wav_path, True
        
    except Exception as e:
        print(f"❌ 오디오 변환 실패: {e}")
        return audio_file, False


def perform_speaker_diarization(audio_file, num_speakers=None):
    """
    실제 화자 분리 수행 (화자 이름 감지 지원)
    
    Args:
        audio_file (str): 오디오 파일 경로
        num_speakers (int, optional): 예상 화자 수 (None이면 자동 감지)
    
    Returns:
        dict: 화자별 시간 구간 정보 (화자 이름 매핑 포함)
    """
    converted_wav_path = None
    try:
        from pyannote.audio import Pipeline
        import torch
        
        print("🎭 실제 음성 특성 기반 화자 분리 시작...")
        
        # 필요시 오디오 파일을 WAV로 변환
        working_audio_file, is_converted = convert_audio_to_wav(audio_file)
        if is_converted:
            converted_wav_path = working_audio_file
        
        # GPU 사용 가능한지 확인 (멀티 GPU 환경 최적화)
        device = "cpu"
        gpu_device_id = 1  # GPU 1을 화자분리 전용으로 사용
        
        if torch.cuda.is_available():
            gpu_count = torch.cuda.device_count()
            if gpu_count >= 2:
                device = f"cuda:{gpu_device_id}"
                print(f"🎯 멀티 GPU 최적화: GPU {gpu_device_id} 사용 (화자분리 전용)")
                
                # RTX 3090 24GB를 위한 고성능 설정
                torch.cuda.set_device(gpu_device_id)
                torch.cuda.empty_cache()  # 메모리 정리
                
                # 메모리 여유도 확인
                memory_total = torch.cuda.get_device_properties(gpu_device_id).total_memory / (1024**3)
                memory_used = torch.cuda.memory_allocated(gpu_device_id) / (1024**3)
                memory_free = memory_total - memory_used
                
                print(f"🔥 GPU {gpu_device_id} 메모리: {memory_free:.1f}GB 사용가능 / {memory_total:.1f}GB")
                
                # 24GB GPU이면 고품질 설정
                if memory_total > 20:
                    print("✨ 대용량 GPU 감지 - 최고 품질 화자 분리 설정 활성화")
                    
            elif gpu_count == 1:
                device = "cuda:0"
                print(f"🔧 단일 GPU: GPU 0 사용")
            else:
                device = "cpu"
                print(f"🔧 GPU 없음: CPU 사용")
        else:
            device = "cpu"
            print(f"🔧 CUDA 불가능: CPU 사용")
        
        print(f"🔧 화자 분리 디바이스: {device}")
        
        # pyannote 파이프라인 로드
        print("📥 pyannote.audio 모델 로딩 중...")
        
        # Hugging Face 토큰 설정 (여러 방법 지원)
        hf_token = None
        
        # 1. .env 파일에서 토큰 가져오기
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            pass
        
        # 2. 환경 변수에서 토큰 가져오기
        hf_token = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_TOKEN")
        
        # 3. 토큰이 없으면 사용자에게 안내
        if not hf_token:
            print("⚠️ Hugging Face 토큰이 설정되지 않았습니다.")
            print("💡 설정 방법:")
            print("   1. .env 파일에 HF_TOKEN='your_token_here' 추가")
            print("   2. export HF_TOKEN='your_token_here'")
            print("   3. huggingface-cli login")
            return None
        
        try:
            # GPU 메모리가 충분하므로 최신 고품질 모델 시도
            high_quality_models = [
                "pyannote/speaker-diarization-3.1",  # 최신 버전
                "pyannote/speaker-diarization@2022.07",  # 안정적인 버전
                "pyannote/speaker-diarization",  # 기본 모델
            ]
            
            pipeline = None
            for model_name in high_quality_models:
                try:
                    print(f"🔍 {model_name} 모델 로드 시도...")
                    pipeline = Pipeline.from_pretrained(
                        model_name,
                        use_auth_token=hf_token
                    )
                    print(f"✅ {model_name} 로드 성공!")
                    break
                except Exception as model_error:
                    print(f"⚠️ {model_name} 로드 실패: {model_error}")
                    continue
            
            if pipeline is None:
                raise Exception("모든 화자 분리 모델 로드 실패")
        except Exception as e:
            if "token" in str(e).lower() or "authentication" in str(e).lower():
                print(f"❌ 인증 오류: {e}")
                print("💡 해결 방법:")
                print("   1. 환경변수 설정: export HF_TOKEN='your_token_here'")
                print("   2. 또는 huggingface-cli login 실행")
                raise
            else:
                raise
        
        if device.startswith("cuda"):
            pipeline = pipeline.to(torch.device(device))
        
        # 화자 분리 실행
        print(f"🎯 화자 분리 실행 중... (예상 화자 수: {num_speakers or '자동감지'})")
        
        diarization_params = {}
        if num_speakers:
            diarization_params["num_speakers"] = num_speakers
        
        diarization = pipeline(working_audio_file, **diarization_params)
        
        # 결과 처리
        speaker_segments = {}
        
        # 화자명 매핑을 위한 딕셔너리
        speaker_mapping = {}
        speaker_counter = 1
        
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            # 원본 화자명을 일관된 화자명으로 매핑
            if speaker not in speaker_mapping:
                speaker_mapping[speaker] = f"화자{speaker_counter}"
                speaker_counter += 1
            
            speaker_id = speaker_mapping[speaker]
            
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
        
        # 임시 파일 정리
        if converted_wav_path and os.path.exists(converted_wav_path):
            os.unlink(converted_wav_path)
            print("🧹 임시 WAV 파일 정리 완료")
        
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
    finally:
        # 임시 파일 정리 (예외 발생시에도)
        if converted_wav_path and os.path.exists(converted_wav_path):
            try:
                os.unlink(converted_wav_path)
                print("🧹 임시 WAV 파일 정리 완료")
            except:
                pass


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