#!/usr/bin/env python3

"""
API 서버 전용 STT 처리 모듈 - app.py 기반 완전 구현
AI 회의록 생성 및 화자 분리 기능 포함
"""

import warnings
import os
import sys
import requests
import json
from datetime import datetime
import tempfile
import re

# 경고 메시지 억제
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning) 
warnings.filterwarnings("ignore", category=DeprecationWarning)

os.environ['TRANSFORMERS_VERBOSITY'] = 'error'
os.environ['SPEECHBRAIN_CACHE'] = '/tmp/speechbrain_cache'
os.environ['TOKENIZERS_PARALLELISM'] = 'false'

def analyze_meeting_with_ai(meeting_text):
    """AI를 사용해서 회의 내용 분석 (app.py에서 가져옴)"""
    import requests
    import json
    
    print("🔍 AI 분석 시작...")
    print(f"📝 분석할 텍스트 길이: {len(meeting_text):,}자")
    
    # 텍스트가 너무 짧으면 폴백 분석 사용
    if len(meeting_text.strip()) < 50:
        print("⚠️ 분석할 텍스트가 너무 짧음 - 폴백 분석 사용")
        return create_fallback_analysis(meeting_text)
    
    # Ollama 서버 연결 테스트
    try:
        print("🔗 Ollama 서버 연결 확인...")
        test_response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if test_response.status_code != 200:
            print(f"❌ Ollama 서버 응답 오류: {test_response.status_code}")
            return create_fallback_analysis(meeting_text)
        
        tags_info = test_response.json()
        models = tags_info.get('models', [])
        qwen_model = next((m for m in models if 'qwen3:8b' in m.get('name', '')), None)
        
        if qwen_model:
            print("🤖 Ollama 모델: qwen3:8b")
            print("📊 엔진 상태: 사용 가능")
        else:
            print("❌ qwen3:8b 모델을 찾을 수 없음")
            return create_fallback_analysis(meeting_text)
            
    except requests.exceptions.ConnectionError:
        print("❌ Ollama 서버에 연결할 수 없습니다. 서버가 실행되고 있는지 확인하세요.")
        return create_fallback_analysis(meeting_text)
    except Exception as e:
        print(f"❌ Ollama 서버 확인 중 오류: {str(e)}")
        return create_fallback_analysis(meeting_text)
    
    # 텍스트가 너무 크면 청크로 분할
    if len(meeting_text) > 10000:
        print("📊 긴 텍스트 감지 - 청크 단위로 분할 처리")
        chunks = chunk_text(meeting_text, max_chunk_size=8000)
        print(f"🔢 {len(chunks)}개 청크로 분할")
        
        chunk_results = []
        for i, chunk in enumerate(chunks):
            print(f"🔄 청크 {i+1}/{len(chunks)} 처리 중...")
            result = analyze_with_ollama(chunk)
            if result:
                chunk_results.append(result)
        
        # 청크 결과들을 합치기
        if chunk_results:
            return combine_chunk_results(chunk_results)
        else:
            print("❌ 모든 청크 처리 실패, fallback 사용")
            return create_fallback_analysis(meeting_text)
    else:
        # 작은 텍스트는 그대로 처리
        return analyze_with_ollama(meeting_text)

def analyze_with_ollama(meeting_text):
    """Ollama를 사용한 회의 내용 분석 (app.py에서 가져옴)"""
    import requests
    import json
    
    try:
        url = "http://localhost:11434/api/generate"
        print("🌐 Ollama API 연결 중...")
        
        prompt = f"""회의 전사 내용을 분석해서 아래 형식으로 회의록을 작성하세요.

전사 내용:
{meeting_text}

회의록 형식:
1. 회의 주제: [핵심 주제를 한 줄로]

2. 주요 내용:
   1. [첫 번째 논의사항]
      - [세부 내용]
   2. [두 번째 논의사항] 
      - [세부 내용]

3. 이슈사항(미결사항):
   ◦ [해결되지 않은 문제들]

4. 결정사항:
   ◦ [회의에서 결정된 내용들]

규칙: 추론 과정 없이 회의록만 출력하세요."""

        payload = {
            "model": "qwen3:8b",
            "prompt": prompt,
            "stream": False
        }
        
        print("🤖 qwen3-8b 모델로 분석 중...")
        response = requests.post(url, json=payload, timeout=180)
        
        if response.status_code == 200:
            result = response.json()
            ai_response = result.get('response', '')
            if ai_response:
                # <think> 태그와 추론 과정 제거
                cleaned_response = clean_ai_response(ai_response)
                return cleaned_response.strip() if cleaned_response else None
        
        print(f"❌ Ollama API 오류: {response.status_code}")
        return None
        
    except Exception as e:
        print(f"❌ Ollama 분석 실패: {e}")
        return None

def clean_ai_response(response):
    """AI 응답에서 불필요한 부분 제거"""
    if not response:
        return ""
    
    # <think>...</think> 태그 제거
    response = re.sub(r'<think>.*?</think>', '', response, flags=re.DOTALL)
    
    # 추론 과정이나 메타 텍스트 제거
    lines = response.split('\n')
    filtered_lines = []
    skip_patterns = [
        '분석하면', '생각해보면', '추론하면', '판단하면',
        '이 회의에서는', '전사 내용을 보면', '내용을 분석하면'
    ]
    
    for line in lines:
        line = line.strip()
        if not line:
            filtered_lines.append('')
            continue
            
        should_skip = any(pattern in line for pattern in skip_patterns)
        if not should_skip:
            filtered_lines.append(line)
    
    return '\n'.join(filtered_lines).strip()

def chunk_text(text, max_chunk_size=8000):
    """긴 텍스트를 적절한 크기로 분할"""
    if len(text) <= max_chunk_size:
        return [text]
    
    # 문장 단위로 분할 시도
    sentences = re.split(r'[.!?]\s+', text)
    chunks = []
    current_chunk = ""
    
    for sentence in sentences:
        if len(current_chunk) + len(sentence) < max_chunk_size:
            current_chunk += sentence + ". "
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = sentence + ". "
    
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    return chunks

def combine_chunk_results(chunk_results):
    """여러 청크의 분석 결과를 합치기"""
    if not chunk_results:
        return None
    
    if len(chunk_results) == 1:
        return chunk_results[0]
    
    # 여러 청크 결과 통합
    combined = f"# 회의록 (통합 분석)\n\n"
    
    for i, result in enumerate(chunk_results):
        if result:
            combined += f"## 부분 {i+1}\n{result}\n\n"
    
    return combined

def create_fallback_analysis(meeting_text):
    """기본 분석 결과 생성 (AI 서버 사용 불가 시)"""
    return f"""1. 회의 주제: 회의 내용 분석

2. 주요 내용:
   1. 음성 인식을 통한 회의 내용 전사 완료
      - 총 {len(meeting_text.split())}개 단어 인식
      - AI 분석 서버 연결 불가로 수동 검토 필요

3. 이슈사항(미결사항):
   ◦ AI 분석 기능 복구 필요
   ◦ Ollama qwen3:8b 서버 연결 상태 점검 필요
   ◦ 회의록 내용 수동 검토 및 보완 필요

4. 결정사항:
   ◦ 전사 내용 기반으로 수동 회의록 작성 진행
   ◦ AI 분석 시스템 복구 후 재분석 검토

---
**주의: 이 회의록은 AI 분석 없이 기본 형식으로 생성되었습니다. 정확한 내용 확인이 필요합니다.**"""

def apply_speaker_diarization(segments_list, audio_file):
    """화자 분리 적용 (app.py 로직 기반)"""
    try:
        print("🎭 화자 분리 시작...")
        
        # speaker_diarization 모듈 임포트 시도
        try:
            from speaker_diarization import perform_speaker_diarization, apply_speaker_diarization_to_transcription, simple_time_based_diarization
            
            # 실제 화자 분리 시도
            speaker_segments = perform_speaker_diarization(audio_file, num_speakers=None)
            
            if speaker_segments:
                # 실제 화자 분리 성공
                segments_list = apply_speaker_diarization_to_transcription(segments_list, speaker_segments)
                print("✅ 실제 음성 특성 기반 화자 분리 적용 완료")
                return segments_list, True
            else:
                # 실패시 시간 기반 화자 구분
                segments_list = simple_time_based_diarization(segments_list, gap_threshold=5.0, max_speakers=4)
                print("✅ 시간 기반 화자 구분 적용 완료")
                return segments_list, True
        
        except ImportError:
            # pyannote.audio 없으면 시간 기반 사용
            from speaker_diarization import simple_time_based_diarization
            segments_list = simple_time_based_diarization(segments_list, gap_threshold=5.0, max_speakers=4)
            print("✅ 시간 기반 화자 구분 적용 완료 (pyannote.audio 미설치)")
            return segments_list, True
            
    except Exception as e:
        print(f"⚠️ 화자 분리 실패: {e}")
        print("📝 화자 정보 없이 진행")
        
        # 기본 화자명 할당
        for i, segment in enumerate(segments_list):
            segment.speaker = f"화자{((i//10)%4)+1}"
        
        return segments_list, False

def transcribe_audio_api(audio_file_path, progress_callback=None):
    """API 전용 STT 처리 - AI 분석 및 화자 분리 포함"""
    
    try:
        from faster_whisper import WhisperModel
        
        if not os.path.exists(audio_file_path):
            return {
                "success": False,
                "error": f"파일을 찾을 수 없습니다: {audio_file_path}"
            }
        
        print(f"🎤 고급 STT 시작: {os.path.basename(audio_file_path)}")
        
        # Whisper 모델 초기화
        print("🤖 Whisper Large-v3 모델 로딩...")
        model = WhisperModel(
            "large-v3", 
            device="cuda", 
            compute_type="float16"
        )
        
        if progress_callback:
            progress_callback("🎯 GPU에서 음성 전사 중...")
        else:
            print("🎯 GPU에서 음성 전사 중...")
            
        # 전사 실행 (스트리밍 방식)
        segments, info = model.transcribe(
            audio_file_path,
            beam_size=5,  # 품질 향상
            language="ko",
            vad_filter=True,
            temperature=0.0,
            initial_prompt="한국어 회의 내용입니다. 정확한 전사를 위해 띄어쓰기와 문장부호를 정확히 표시해주세요.",
            word_timestamps=True  # 단어별 타임스탬프
        )
        
        # 실시간 전사 결과 수집
        segments_list = []
        current_text = ""
        
        for i, segment in enumerate(segments):
            segment_text = segment.text.strip()
            current_text += segment_text + " "
            segments_list.append(segment)
            
            # 실시간 전사 업데이트
            if progress_callback:
                progress_callback(f"💬 [{segment.start:.1f}s] {segment_text}")
            else:
                print(f"💬 [{segment.start:.1f}s-{segment.end:.1f}s] {segment_text}")
            
            # 진행 상황 업데이트
            if i % 5 == 0 and i > 0:
                if progress_callback:
                    progress_callback(f"📊 전사 진행: {i+1}개 구간 완료...")
        
        print(f"✅ 전사 완료: {len(segments_list)}개 구간, {info.duration:.1f}초")
        
        # 화자 분리 적용
        if progress_callback:
            progress_callback("🎭 화자 분리 처리 중...")
        
        segments_list, diarization_success = apply_speaker_diarization(segments_list, audio_file_path)
        
        # 전체 텍스트 생성 (화자 정보 포함)
        full_text = ""
        detailed_text = ""
        
        for i, segment in enumerate(segments_list):
            speaker_info = getattr(segment, 'speaker', f"화자{((i//10)%4)+1}")
            full_text += f"{speaker_info}: {segment.text.strip()}\n"
            detailed_text += f"[{segment.start:.1f}s-{segment.end:.1f}s] {speaker_info}: {segment.text.strip()}\n"
        
        # AI 분석 실행
        if progress_callback:
            progress_callback("🤖 AI가 회의 내용을 분석하여 회의록 생성 중...")
        else:
            print("🤖 AI가 회의 내용을 분석하여 회의록 생성 중...")
        
        ai_analysis = analyze_meeting_with_ai(full_text)
        
        # 파일 저장
        base_name = os.path.splitext(os.path.basename(audio_file_path))[0]
        timestamp = datetime.now().strftime("%m%d_%H%M")
        
        # 전사 결과 파일 (화자 정보 포함)
        stt_filename = f"{timestamp}_{base_name}_전사결과.txt"
        stt_filepath = os.path.join(os.getcwd(), stt_filename)
        
        with open(stt_filepath, 'w', encoding='utf-8') as f:
            f.write(f"{base_name} - STT 전사 결과 (화자 분리 포함)\n")
            f.write(f"{datetime.now().strftime('%Y.%m.%d %H:%M')} ・ {info.duration:.0f}초\n")
            f.write(f"언어: {info.language} (확률: {info.language_probability:.1%})\n")
            f.write(f"화자 분리: {'✅ 성공' if diarization_success else '❌ 기본값 사용'}\n")
            f.write("="*60 + "\n\n")
            f.write(detailed_text)
        
        # AI 분석 기반 회의록 생성
        minutes_filename = f"{timestamp}_{base_name}_회의록.txt"
        minutes_filepath = os.path.join(os.getcwd(), minutes_filename)
        
        with open(minutes_filepath, 'w', encoding='utf-8') as f:
            f.write("# 회의록 (AI 분석)\n\n")
            f.write(f"## 기본 정보\n")
            f.write(f"- **일시**: {datetime.now().strftime('%Y년 %m월 %d일 %H시 %M분')}\n")
            f.write(f"- **파일명**: {os.path.basename(audio_file_path)}\n")
            f.write(f"- **회의 시간**: {info.duration:.1f}초\n")
            f.write(f"- **언어**: 한국어 ({info.language_probability:.1%})\n")
            f.write(f"- **화자 분리**: {'적용됨' if diarization_success else '기본값 사용'}\n")
            f.write(f"- **AI 분석**: Ollama qwen3:8b\n\n")
            
            if ai_analysis:
                f.write(f"## AI 분석 결과\n\n")
                f.write(ai_analysis)
                f.write(f"\n\n")
            else:
                f.write(f"## 회의 내용 (AI 분석 실패)\n\n")
                f.write(f"### 전사 내용\n")
                f.write(full_text)
                f.write(f"\n\n")
            
            f.write(f"## 상세 전사 내용 (화자별)\n")
            f.write(f"```\n")
            f.write(detailed_text)
            f.write(f"```\n\n")
            f.write(f"---\n")
            f.write(f"**이 회의록은 AI 음성인식 및 자동 분석 시스템에 의해 생성되었습니다.**\n")
        
        success_msg = f"✅ 고급 처리 완료!"
        print(success_msg)
        print(f"   전사 파일: {stt_filename}")
        print(f"   AI 회의록: {minutes_filename}")
        print(f"   화자 분리: {'✅' if diarization_success else '❌'}")
        print(f"   AI 분석: {'✅' if ai_analysis else '❌'}")
        
        if progress_callback:
            progress_callback(success_msg)
        
        return {
            "success": True,
            "transcription_file": stt_filepath,
            "minutes_file": minutes_filepath,
            "transcription_text": detailed_text,
            "minutes_text": open(minutes_filepath, 'r', encoding='utf-8').read(),
            "duration": info.duration,
            "language": info.language,
            "segment_count": len(segments_list),
            "diarization_success": diarization_success,
            "ai_analysis_success": ai_analysis is not None
        }
        
    except Exception as e:
        print(f"❌ STT 처리 오류: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e)
        }

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("사용법: python stt_api.py <audio_file>")
        sys.exit(1)
    
    audio_file = sys.argv[1]
    result = transcribe_audio_api(audio_file)
    
    if result["success"]:
        print(f"✅ 성공: {result['segment_count']}개 구간 처리")
        print(f"   화자 분리: {result.get('diarization_success', False)}")
        print(f"   AI 분석: {result.get('ai_analysis_success', False)}")
    else:
        print(f"❌ 실패: {result['error']}")
        sys.exit(1)