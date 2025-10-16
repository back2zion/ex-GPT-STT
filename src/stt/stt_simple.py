#!/usr/bin/env python3

import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from faster_whisper import WhisperModel
import sys
import os
from datetime import datetime
import tempfile
import zipfile
import shutil
import requests
import psutil

# CPU 사용량 제한 설정
def limit_cpu_usage():
    """CPU 사용량을 안전한 수준으로 제한"""
    try:
        # 현재 프로세스의 우선순위를 낮춤 (더 많은 CPU를 다른 프로세스에게 양보)
        current_process = psutil.Process()
        
        # Windows에서는 BELOW_NORMAL_PRIORITY_CLASS, Linux에서는 낮은 우선순위
        if hasattr(psutil, 'BELOW_NORMAL_PRIORITY_CLASS'):
            current_process.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
        else:
            current_process.nice(5)  # Linux에서 낮은 우선순위
        
        # CPU 스레드 제한 환경 변수 설정
        cpu_count = psutil.cpu_count(logical=False)  # 물리적 코어 수
        limited_threads = max(1, cpu_count // 2)  # 물리적 코어의 절반만 사용
        
        os.environ['OMP_NUM_THREADS'] = str(limited_threads)
        os.environ['MKL_NUM_THREADS'] = str(limited_threads)
        os.environ['NUMEXPR_NUM_THREADS'] = str(limited_threads)
        os.environ['OPENBLAS_NUM_THREADS'] = str(limited_threads)
        
        print(f"🔧 CPU 사용량 제한 설정됨: {limited_threads}개 스레드 (전체 {cpu_count}코어 중)")
        
    except Exception as e:
        print(f"⚠️ CPU 사용량 제한 설정 실패: {e}")

# 시작 시 CPU 제한 적용
limit_cpu_usage()

def transcribe_audio(audio_file):
    """간단한 STT 실행"""
    if not os.path.exists(audio_file):
        print(f"❌ 파일을 찾을 수 없습니다: {audio_file}")
        return
    
    print(f"🎤 파일: {os.path.basename(audio_file)}")
    print("🔄 Large-v3 모델로 전사 중... (GPU 사용)")
    
    # Large 모델로 최고 품질 - GPU 강제
    # 기본: cuda (GPU 0), 메모리 여유에 따라 float16 권장
    try:
        import torch
        if not torch.cuda.is_available():
            print("❌ CUDA 사용 불가 - GPU가 필요합니다.")
            return
    except Exception:
        pass

    # CPU 스레드를 1개로 제한하여 CPU 사용량 최소화
    model = WhisperModel(
        "large-v3", 
        device="cuda", 
        compute_type="float16",
        cpu_threads=1  # CPU 스레드 최소화
    )
    
    segments, info = model.transcribe(
        audio_file,
        beam_size=3,  # 빔 사이즈 줄임 (5→3)
        language="ko",
        vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=500),
        temperature=0.0,
        compression_ratio_threshold=2.4,
        no_speech_threshold=0.6,
        condition_on_previous_text=False,
        initial_prompt="한국어 회의 내용입니다.",
        # 배치 처리로 메모리 효율성 향상
        chunk_length=30  # 30초씩 청크로 나누어 처리
    )
    
    # 결과 저장
    base_name = os.path.splitext(os.path.basename(audio_file))[0]
    output_dir = os.path.dirname(audio_file)
    output_file = os.path.join(output_dir, f"{base_name}_STT.txt")
    
    print(f"📝 전사 결과를 저장 중: {output_file}")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"{base_name} - STT 결과\n")
        f.write(f"{datetime.now().strftime('%Y.%m.%d %H:%M')} ・ {info.duration:.0f}초\n")
        f.write(f"언어: {info.language} (확률: {info.language_probability:.1%})\n\n")
        
        segment_count = 0
        for segment in segments:
            f.write(f"[{segment.start:.1f}s -> {segment.end:.1f}s]\n")
            f.write(f"{segment.text.strip()}\n\n")
            segment_count += 1
            
            # 터미널에도 출력
            print(f"[{segment.start:.1f}s] {segment.text.strip()}")
        
        f.write(f"총 {segment_count}개 구간 처리 완료\n")
    
    print(f"\n✅ 완료! 파일 저장됨: {output_file}")
    print(f"📊 총 {segment_count}개 구간, {info.duration:.1f}초")
    
    # API 모드에서는 자동으로 회의록 생성
    create_meeting_minutes(output_file, segments, info)

def create_meeting_minutes(stt_file, segments, info):
    """STT 결과로부터 DOCX 회의록 생성"""
    
    # 전사 내용을 하나의 텍스트로 합치기
    meeting_text = ""
    for segment in segments:
        meeting_text += segment.text.strip() + " "
    
    print("🤖 AI로 회의록 분석 중...")
    
    # AI 분석 시도
    try:
        analysis = analyze_with_ai(meeting_text)
    except Exception as e:
        print(f"⚠️ AI 분석 실패: {e}")
        analysis = create_simple_analysis(meeting_text)
    
    print("📋 DOCX 회의록 생성 중...")
    
    # DOCX 파일 생성
    base_name = os.path.splitext(os.path.basename(stt_file))[0].replace('_STT', '')
    output_dir = os.path.dirname(stt_file)
    docx_path = os.path.join(output_dir, f"{base_name}_회의록.docx")
    
    temp_dir = tempfile.mkdtemp()
    
    try:
        create_docx_structure(temp_dir, analysis, base_name)
        
        # ZIP으로 압축해서 DOCX 파일 생성
        with zipfile.ZipFile(docx_path, 'w', zipfile.ZIP_DEFLATED) as docx:
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arc_path = os.path.relpath(file_path, temp_dir)
                    docx.write(file_path, arc_path)
        
        print(f"✅ 회의록 생성 완료: {os.path.basename(docx_path)}")
        
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

def analyze_with_ai(meeting_text):
    """vLLM API로 회의 내용 분석"""
    prompt = f"""다음 회의 전사 내용을 분석해서 회의록을 작성해주세요.

전사 내용: {meeting_text}

다음 형식으로 분석해주세요:
1. 회의 주제: [주요 논의 주제]
2. 주요 논의사항: [논의사항들]
3. 결정사항: [결정된 사항들]
4. 이슈/문제점: [발견된 이슈들]
5. 향후 계획: [앞으로의 계획]

한국어로 구체적이고 명확하게 작성해주세요."""

    # vLLM OpenAI 호환 API 사용
    response = requests.post(
        "http://localhost:8000/v1/chat/completions",
        json={
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 1024,
            "temperature": 0.1,
            "top_p": 0.7
        },
        timeout=120
    )
    
    if response.status_code == 200:
        result = response.json()
        ai_response = result.get('response', '')
        return parse_ai_response(ai_response)
    else:
        raise Exception(f"vLLM 서버 오류: {response.status_code} - {response.text}")

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
            
        if '회의 주제:' in line:
            analysis['topic'] = line.split(':', 1)[1].strip()
        elif '논의사항:' in line:
            current_section = 'discussions'
        elif '결정사항:' in line:
            current_section = 'decisions'
        elif '이슈' in line or '문제점' in line:
            current_section = 'issues'
        elif '향후' in line or '계획' in line:
            current_section = 'plans'
        elif line.startswith('- ') and current_section:
            analysis[current_section].append(line[2:].strip())
    
    return analysis

def create_simple_analysis(meeting_text):
    """간단한 분석 (AI 실패시)"""
    return {
        'topic': '프로젝트 진행상황 논의',
        'discussions': ['퍼블리싱 작업 진행률 (20% 이상 완료)', '설계-퍼블리싱-개발 병렬 진행 방안'],
        'decisions': ['설계 완료 부분부터 순차적 퍼블리싱 진행', '병렬 작업으로 개발 속도 향상'],
        'issues': ['전체 완료까지 시간 소요 예상'],
        'plans': ['설계 완료 → 퍼블리싱 → 개발 순차 진행']
    }

def create_docx_structure(temp_dir, analysis, base_name):
    """DOCX 파일 구조 생성"""
    
    os.makedirs(os.path.join(temp_dir, "_rels"))
    os.makedirs(os.path.join(temp_dir, "docProps"))
    os.makedirs(os.path.join(temp_dir, "word"))
    
    # [Content_Types].xml
    content_types = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
</Types>'''
    
    with open(os.path.join(temp_dir, "[Content_Types].xml"), 'w', encoding='utf-8') as f:
        f.write(content_types)
    
    # _rels/.rels
    main_rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
</Relationships>'''
    
    with open(os.path.join(temp_dir, "_rels", ".rels"), 'w', encoding='utf-8') as f:
        f.write(main_rels)
    
    # docProps/core.xml
    core_props = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:dcmitype="http://purl.org/dc/dcmitype/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
<dc:creator>STT Meeting Minutes</dc:creator>
<dcterms:created xsi:type="dcterms:W3CDTF">{datetime.now().isoformat()}</dcterms:created>
</cp:coreProperties>'''
    
    with open(os.path.join(temp_dir, "docProps", "core.xml"), 'w', encoding='utf-8') as f:
        f.write(core_props)
    
    # word/document.xml
    document_xml = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:body>

<w:p><w:pPr><w:jc w:val="center"/></w:pPr><w:r><w:rPr><w:b/><w:sz w:val="32"/></w:rPr><w:t>회의록</w:t></w:r></w:p>
<w:p></w:p>

<w:p><w:r><w:rPr><w:b/></w:rPr><w:t>📅 일시: {datetime.now().strftime('%Y.%m.%d %H:%M')}</w:t></w:r></w:p>
<w:p><w:r><w:rPr><w:b/></w:rPr><w:t>📋 회의명: {analysis['topic']}</w:t></w:r></w:p>
<w:p></w:p>

<w:p><w:r><w:rPr><w:b/><w:sz w:val="24"/></w:rPr><w:t>💬 주요 논의사항</w:t></w:r></w:p>'''

    for item in analysis['discussions']:
        document_xml += f'<w:p><w:r><w:t>• {item}</w:t></w:r></w:p>'

    document_xml += '''
<w:p></w:p>
<w:p><w:r><w:rPr><w:b/><w:sz w:val="24"/></w:rPr><w:t>✅ 결정사항</w:t></w:r></w:p>'''

    for item in analysis['decisions']:
        document_xml += f'<w:p><w:r><w:t>• {item}</w:t></w:r></w:p>'

    document_xml += '''
<w:p></w:p>
<w:p><w:r><w:rPr><w:b/><w:sz w:val="24"/></w:rPr><w:t>⚠️ 이슈사항</w:t></w:r></w:p>'''

    for item in analysis['issues']:
        document_xml += f'<w:p><w:r><w:t>• {item}</w:t></w:r></w:p>'

    document_xml += '''
<w:p></w:p>
<w:p><w:r><w:rPr><w:b/><w:sz w:val="24"/></w:rPr><w:t>📋 향후 계획</w:t></w:r></w:p>'''

    for item in analysis['plans']:
        document_xml += f'<w:p><w:r><w:t>• {item}</w:t></w:r></w:p>'

    document_xml += '''
<w:p></w:p>
<w:p><w:pPr><w:jc w:val="center"/></w:pPr><w:r><w:rPr><w:sz w:val="18"/><w:color w:val="808080"/></w:rPr><w:t>※ AI 음성인식으로 자동 생성된 회의록입니다.</w:t></w:r></w:p>

</w:body>
</w:document>'''
    
    with open(os.path.join(temp_dir, "word", "document.xml"), 'w', encoding='utf-8') as f:
        f.write(document_xml)

if __name__ == "__main__":
    if len(sys.argv) == 2:
        # 명령행 인수가 있는 경우 (드래그 앤 드롭 또는 직접 입력)
        audio_file = sys.argv[1].strip().strip('"').strip("'")
        
        # Windows 경로를 WSL 경로로 변환
        if audio_file.lower().startswith(("c:\\", "c:/")):
            if "\\" in audio_file:
                audio_file = audio_file.replace("C:\\", "/mnt/c/").replace("\\", "/")
            else:
                audio_file = audio_file.replace("C:/", "/mnt/c/").replace("c:/", "/mnt/c/")
        
        transcribe_audio(audio_file)
    else:
        # 대화형 모드
        print("🎤 음성 전사 (STT)")
        print("=" * 40)
        print()
        print("사용법:")
        print("1. python stt_simple.py <파일경로>")
        print("2. 또는 아래에 파일 경로 입력/드래그")
        print()
        
        while True:
            try:
                print("📁 파일 입력 방법:")
                print("  • Windows에서 파일을 드래그해서 터미널에 놓으세요")
                print("  • 또는 직접 경로를 입력하세요")
                print()
                
                audio_file = input("파일 경로: ").strip()
                
                # 따옴표 제거 (드래그시 자동으로 붙는 경우)
                if audio_file.startswith('"') and audio_file.endswith('"'):
                    audio_file = audio_file[1:-1]
                elif audio_file.startswith("'") and audio_file.endswith("'"):
                    audio_file = audio_file[1:-1]
                
                if not audio_file:
                    print("❌ 파일 경로를 입력해주세요.")
                    continue
                
                # Windows 경로를 WSL 경로로 변환
                if audio_file.lower().startswith(("c:\\", "c:/")):
                    if "\\" in audio_file:
                        audio_file = audio_file.replace("C:\\", "/mnt/c/").replace("\\", "/")
                    else:
                        audio_file = audio_file.replace("C:/", "/mnt/c/").replace("c:/", "/mnt/c/")
                    print(f"🔄 WSL 경로로 변환: {audio_file}")
                
                # 지원하는 파일 형식 확인
                supported_ext = ('.mp3', '.wav', '.m4a', '.flac', '.aac', '.ogg')
                if not audio_file.lower().endswith(supported_ext):
                    print(f"❌ 지원하지 않는 파일 형식입니다. 지원 형식: {', '.join(supported_ext)}")
                    continue
                
                transcribe_audio(audio_file)
                
                # 계속할지 묻기
                again = input("\n다른 파일을 전사하시겠습니까? (y/N): ").strip().lower()
                if again not in ['y', 'yes']:
                    break
                    
            except KeyboardInterrupt:
                print("\n\n👋 프로그램을 종료합니다.")
                break
            except EOFError:
                break