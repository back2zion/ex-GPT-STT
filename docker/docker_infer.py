#!/usr/bin/env python3
"""
Docker용 STT 추론 스크립트
Korean STT with meeting minutes generation for containerized deployment
"""

import os
import sys
import time
import requests
from datetime import datetime
from pathlib import Path
from faster_whisper import WhisperModel

# 환경 변수
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
INPUT_DIR = Path("/app/input")
OUTPUT_DIR = Path("/app/output")
MODEL_SIZE = os.getenv("WHISPER_MODEL", "large-v3")
DEVICE = os.getenv("DEVICE", "cuda")
COMPUTE_TYPE = os.getenv("COMPUTE_TYPE", "float16")

def setup_directories():
    """디렉토리 설정"""
    INPUT_DIR.mkdir(exist_ok=True)
    OUTPUT_DIR.mkdir(exist_ok=True)
    print(f"📁 Input directory: {INPUT_DIR}")
    print(f"📁 Output directory: {OUTPUT_DIR}")

def wait_for_ollama():
    """Ollama 서비스 대기"""
    print("🤖 Ollama 서비스 연결 대기 중...")
    max_attempts = 30
    attempt = 0
    
    while attempt < max_attempts:
        try:
            response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
            if response.status_code == 200:
                print("✅ Ollama 서비스 연결 성공!")
                return True
        except requests.exceptions.RequestException:
            pass
        
        attempt += 1
        print(f"⏳ Ollama 연결 시도 {attempt}/{max_attempts}...")
        time.sleep(5)
    
    print("❌ Ollama 서비스 연결 실패")
    return False

def initialize_whisper():
    """Whisper 모델 초기화"""
    print(f"🎤 Whisper {MODEL_SIZE} 모델 로딩 중...")
    print(f"🔧 Device: {DEVICE}, Compute Type: {COMPUTE_TYPE}")
    
    try:
        model = WhisperModel(MODEL_SIZE, device=DEVICE, compute_type=COMPUTE_TYPE)
        print("✅ Whisper 모델 로딩 완료!")
        return model
    except Exception as e:
        print(f"❌ Whisper 모델 로딩 실패: {e}")
        sys.exit(1)

def transcribe_audio(model, audio_file):
    """오디오 파일 전사"""
    print(f"🎵 전사 시작: {audio_file.name}")
    
    segments, info = model.transcribe(
        str(audio_file),
        beam_size=5,
        language="ko",
        vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=500),
        temperature=0.0,
        compression_ratio_threshold=2.4,
        no_speech_threshold=0.6,
        condition_on_previous_text=False,
        initial_prompt="한국어 회의 내용입니다."
    )
    
    # 전사 결과 수집
    transcription = ""
    segment_list = []
    
    for segment in segments:
        transcription += segment.text.strip() + " "
        segment_list.append({
            'start': segment.start,
            'end': segment.end,
            'text': segment.text.strip()
        })
        print(f"[{segment.start:.1f}s] {segment.text.strip()}")
    
    return transcription.strip(), segment_list, info

def analyze_with_ai(transcription):
    """AI로 회의 내용 분석"""
    if not transcription:
        return create_simple_analysis()
    
    print("🤖 AI 분석 시작...")
    
    prompt = f"""다음 회의 전사 내용을 분석해서 구조화된 회의록을 작성해주세요.

전사 내용: {transcription}

다음 형식으로 분석해주세요:
1. 회의 주제: [주요 논의 주제]
2. 주요 논의사항: [논의사항들을 불릿 포인트로]
3. 결정사항: [결정된 사항들을 불릿 포인트로]
4. 이슈/문제점: [발견된 이슈들을 불릿 포인트로]
5. 향후 계획: [앞으로의 계획을 불릿 포인트로]

한국어로 구체적이고 명확하게 작성해주세요."""

    try:
        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={
                "model": "qwen3:32b",
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.3}
            },
            timeout=120
        )
        
        if response.status_code == 200:
            result = response.json()
            ai_response = result.get('response', '')
            print("✅ AI 분석 완료!")
            return parse_ai_response(ai_response)
        else:
            print(f"❌ AI 분석 실패: HTTP {response.status_code}")
            return create_simple_analysis()
            
    except Exception as e:
        print(f"❌ AI 분석 오류: {e}")
        return create_simple_analysis()

def parse_ai_response(ai_response):
    """AI 응답 파싱"""
    analysis = {
        'topic': '프로젝트 논의',
        'discussions': [],
        'decisions': [],
        'issues': [],
        'plans': []
    }
    
    lines = ai_response.split('\n')
    current_section = None
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        if '회의 주제:' in line or '주제:' in line:
            analysis['topic'] = line.split(':', 1)[1].strip()
        elif '논의사항:' in line or '논의' in line:
            current_section = 'discussions'
        elif '결정사항:' in line or '결정' in line:
            current_section = 'decisions'
        elif '이슈' in line or '문제점' in line:
            current_section = 'issues'
        elif '향후' in line or '계획' in line:
            current_section = 'plans'
        elif line.startswith('- ') and current_section:
            analysis[current_section].append(line[2:].strip())
        elif line.startswith('• ') and current_section:
            analysis[current_section].append(line[2:].strip())
    
    return analysis

def create_simple_analysis():
    """간단한 분석 (AI 실패시 대체)"""
    return {
        'topic': '회의 논의사항',
        'discussions': ['전사 내용 기반 논의사항'],
        'decisions': ['주요 결정사항'],
        'issues': ['확인된 이슈사항'],
        'plans': ['향후 진행 계획']
    }

def save_results(audio_file, transcription, segments, analysis, info):
    """결과 저장"""
    base_name = audio_file.stem
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # STT 결과 저장
    stt_file = OUTPUT_DIR / f"{base_name}_STT_{timestamp}.txt"
    with open(stt_file, 'w', encoding='utf-8') as f:
        f.write(f"{base_name} - STT 결과\n")
        f.write(f"처리일시: {datetime.now().strftime('%Y.%m.%d %H:%M')}\n")
        f.write(f"파일길이: {info.duration:.0f}초\n")
        f.write(f"언어: {info.language} (확률: {info.language_probability:.1%})\n")
        f.write("=" * 50 + "\n\n")
        
        for segment in segments:
            f.write(f"[{segment['start']:.1f}s -> {segment['end']:.1f}s]\n")
            f.write(f"{segment['text']}\n\n")
    
    # 회의록 저장
    minutes_file = OUTPUT_DIR / f"{base_name}_회의록_{timestamp}.md"
    with open(minutes_file, 'w', encoding='utf-8') as f:
        f.write(f"# 회의록 - {analysis['topic']}\n\n")
        f.write(f"**일시:** {datetime.now().strftime('%Y.%m.%d %H:%M')}\n")
        f.write(f"**파일:** {audio_file.name}\n")
        f.write(f"**길이:** {info.duration:.1f}초\n\n")
        
        f.write("## 💬 주요 논의사항\n")
        for item in analysis['discussions']:
            f.write(f"- {item}\n")
        f.write("\n")
        
        f.write("## ✅ 결정사항\n")
        for item in analysis['decisions']:
            f.write(f"- {item}\n")
        f.write("\n")
        
        f.write("## ⚠️ 이슈사항\n")
        for item in analysis['issues']:
            f.write(f"- {item}\n")
        f.write("\n")
        
        f.write("## 📋 향후 계획\n")
        for item in analysis['plans']:
            f.write(f"- {item}\n")
        f.write("\n")
        
        f.write("---\n*AI 음성인식으로 자동 생성된 회의록입니다.*\n")
    
    print(f"💾 STT 결과 저장: {stt_file.name}")
    print(f"💾 회의록 저장: {minutes_file.name}")
    
    return stt_file, minutes_file

def process_audio_files():
    """오디오 파일들 처리"""
    supported_formats = ('.mp3', '.wav', '.m4a', '.flac', '.aac', '.ogg')
    audio_files = []
    
    for ext in supported_formats:
        audio_files.extend(INPUT_DIR.glob(f"*{ext}"))
    
    if not audio_files:
        print(f"❌ {INPUT_DIR}에서 오디오 파일을 찾을 수 없습니다.")
        print(f"지원 형식: {', '.join(supported_formats)}")
        return
    
    print(f"🎵 {len(audio_files)}개 오디오 파일 발견")
    
    # Whisper 모델 초기화
    model = initialize_whisper()
    
    for audio_file in audio_files:
        try:
            print(f"\n{'='*60}")
            print(f"처리 중: {audio_file.name}")
            
            # STT 처리
            transcription, segments, info = transcribe_audio(model, audio_file)
            
            # AI 분석
            analysis = analyze_with_ai(transcription)
            
            # 결과 저장
            save_results(audio_file, transcription, segments, analysis, info)
            
            print(f"✅ {audio_file.name} 처리 완료")
            
        except Exception as e:
            print(f"❌ {audio_file.name} 처리 실패: {e}")

def main():
    """메인 함수"""
    print("🚀 Ex-GPT STT Docker 컨테이너 시작")
    print("=" * 60)
    
    # 디렉토리 설정
    setup_directories()
    
    # Ollama 서비스 대기
    if not wait_for_ollama():
        print("⚠️ Ollama 없이 STT만 실행합니다.")
    
    # 지속적 모니터링 모드
    if os.getenv("WATCH_MODE", "false").lower() == "true":
        print("👁️ 파일 감시 모드 시작...")
        processed_files = set()
        
        while True:
            try:
                # 새 파일 확인
                audio_files = []
                for ext in ('.mp3', '.wav', '.m4a', '.flac', '.aac', '.ogg'):
                    audio_files.extend(INPUT_DIR.glob(f"*{ext}"))
                
                new_files = [f for f in audio_files if f not in processed_files]
                
                if new_files:
                    print(f"🆕 새 파일 {len(new_files)}개 발견!")
                    for audio_file in new_files:
                        # 파일 처리 로직...
                        processed_files.add(audio_file)
                
                time.sleep(10)  # 10초마다 확인
                
            except KeyboardInterrupt:
                print("\n👋 파일 감시 중단")
                break
    else:
        # 일회성 처리 모드
        process_audio_files()
        print("\n🎉 모든 처리 완료!")

if __name__ == "__main__":
    main()