#!/usr/bin/env python3

from faster_whisper import WhisperModel
import os
import sys
from datetime import datetime
import tempfile
import zipfile
import shutil
import tkinter as tk
from tkinter import messagebox, ttk
import threading
import psutil
import platform

# cuDNN 환경 변수 설정
def setup_cudnn_env():
    """cuDNN 환경 변수 자동 설정"""
    try:
        import nvidia.cudnn
        cudnn_path = os.path.dirname(nvidia.cudnn.__file__)
        lib_path = os.path.join(cudnn_path, "lib")
        
        if os.path.exists(lib_path):
            current_ld_path = os.environ.get("LD_LIBRARY_PATH", "")
            if lib_path not in current_ld_path:
                os.environ["LD_LIBRARY_PATH"] = f"{lib_path}:{current_ld_path}"
            os.environ["CUDNN_PATH"] = cudnn_path
            print(f"✅ cuDNN 환경 설정 완료: {lib_path}")
            return True
    except ImportError:
        print("⚠️ nvidia-cudnn-cu12 패키지가 없습니다 (CPU 모드로 실행)")
        return False
    except Exception as e:
        print(f"⚠️ cuDNN 환경 설정 실패: {e} (CPU 모드로 실행)")
        return False

# 시작 시 cuDNN 환경 설정
setup_cudnn_env()

def select_file():
    """파일 선택 UI"""
    download_dir = "/mnt/c/Users/KwakDaniel/Documents/KakaoTalk Downloads"
    onedrive_dir = "/mnt/c/Users/KwakDaniel/OneDrive/첨부 파일"
    
    print("\nFile Selection Options:")
    print("1. Enter file path directly")
    print("2. Browse KakaoTalk Downloads folder")
    print("3. Browse OneDrive attachments folder")  
    print("4. GUI drag & drop selector")
    print("5. Terminal drag & drop (simple)")
    
    choice = input("\nSelect (1-5): ").strip()
    
    if choice == "2":
        return browse_directory(download_dir)
    elif choice == "3":
        return browse_directory(onedrive_dir)
    elif choice == "4":
        return drag_drop_file_selector()
    elif choice == "5":
        return terminal_drag_drop()
    else:
        return input_file_path()

def drag_drop_file_selector():
    """드래그 앤 드롭 파일 선택 GUI"""
    selected_file = [None]  # 선택된 파일을 저장할 리스트 (mutable)
    
    def on_drop(event):
        """파일이 드롭되었을 때 호출되는 함수"""
        files = root.tk.splitlist(event.data)
        if files:
            file_path = files[0]
            
            # Windows 경로를 WSL 경로로 변환
            if file_path.lower().startswith(("c:\\", "c:/")):
                if "\\" in file_path:
                    file_path = file_path.replace("C:\\", "/mnt/c/").replace("\\", "/")
                else:
                    file_path = file_path.replace("C:/", "/mnt/c/").replace("c:/", "/mnt/c/")
            
            # 지원되는 파일 형식 확인
            supported_extensions = ('.mp3', '.wav', '.m4a', '.flac', '.aac', '.ogg', '.txt')
            if file_path.lower().endswith(supported_extensions):
                selected_file[0] = file_path
                file_name = os.path.basename(file_path)
                try:
                    size_mb = os.path.getsize(file_path) / (1024 * 1024) if os.path.exists(file_path) else 0
                except:
                    size_mb = 0
                
                # 파일 정보 업데이트
                if file_path.endswith('.txt') and 'STT' in file_name:
                    file_type = "📄 STT 파일"
                else:
                    file_type = "🎵 오디오 파일"
                    
                info_label.config(text=f"✅ {file_type}\\n파일명: {file_name}\\n크기: {size_mb:.1f} MB")
                select_button.config(state="normal")
            else:
                messagebox.showerror("지원되지 않는 파일", "지원되는 파일 형식:\\n오디오: .mp3, .wav, .m4a, .flac, .aac, .ogg\\nSTT: .txt")
    
    def on_browse():
        """찾아보기 버튼"""
        from tkinter import filedialog
        file_types = [
            ("모든 지원 파일", "*.mp3;*.wav;*.m4a;*.flac;*.aac;*.ogg;*.txt"),
            ("오디오 파일", "*.mp3;*.wav;*.m4a;*.flac;*.aac;*.ogg"),
            ("STT 파일", "*.txt"),
            ("모든 파일", "*.*")
        ]
        
        file_path = filedialog.askopenfilename(
            title="파일 선택",
            filetypes=file_types,
            initialdir="/mnt/c/Users/KwakDaniel/Documents/KakaoTalk Downloads"
        )
        
        if file_path:
            # Mock event object for on_drop function
            class MockEvent:
                def __init__(self, data):
                    self.data = data
            
            # Use existing on_drop logic
            mock_event = MockEvent(file_path)
            root.tk.splitlist = lambda x: [x]  # Mock splitlist
            on_drop(mock_event)
    
    def on_select():
        """선택 버튼을 눌렀을 때"""
        root.destroy()
    
    def on_cancel():
        """취소 버튼을 눌렀을 때"""
        selected_file[0] = None
        root.destroy()
    
    try:
        from tkinterdnd2 import TkinterDnD, DND_FILES
        
        # TkinterDnD 활성화
        root = TkinterDnD.Tk()
        root.title("🎤 파일 선택 - 드래그 앤 드롭")
        root.geometry("550x350")
        root.resizable(False, False)
        
        # 메인 프레임
        main_frame = ttk.Frame(root, padding="20")
        main_frame.pack(fill="both", expand=True)
        
        # 제목
        title_label = ttk.Label(main_frame, text="🎤 음성 파일 또는 STT 파일 선택", font=("Arial", 14, "bold"))
        title_label.pack(pady=(0, 20))
        
        # 드래그 앤 드롭 영역
        drop_frame = ttk.Frame(main_frame, relief="solid", borderwidth=2)
        drop_frame.pack(fill="both", expand=True, pady=10)
        
        drop_label = ttk.Label(drop_frame, 
                              text="📁\\n\\n여기에 파일을 드래그하거나\\n아래 '찾아보기' 버튼을 클릭하세요\\n\\n지원 형식: .mp3, .wav, .m4a, .flac, .aac, .ogg, .txt", 
                              font=("Arial", 11), justify="center")
        drop_label.pack(expand=True)
        
        # 파일 정보 표시 영역
        info_label = ttk.Label(main_frame, text="파일을 선택해주세요")
        info_label.pack(pady=10)
        
        # 버튼 프레임
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=10)
        
        browse_button = ttk.Button(button_frame, text="📁 찾아보기", command=on_browse)
        browse_button.pack(side="left", padx=5)
        
        select_button = ttk.Button(button_frame, text="✅ 선택", command=on_select, state="disabled")
        select_button.pack(side="left", padx=5)
        
        cancel_button = ttk.Button(button_frame, text="❌ 취소", command=on_cancel)
        cancel_button.pack(side="left", padx=5)
        
        # 드래그 앤 드롭 이벤트 등록
        drop_frame.drop_target_register(DND_FILES)
        drop_frame.dnd_bind('<<Drop>>', on_drop)
        
        print("\\n🖱️  드래그 앤 드롭 GUI가 열렸습니다.")
        print("   파일을 창에 드래그하거나 '찾아보기' 버튼을 클릭하세요.")
        
    except ImportError:
        # tkinterdnd2가 없으면 기본 파일 대화상자만 사용
        print("\\n📁 파일 대화상자를 엽니다...")
        from tkinter import filedialog
        
        root = tk.Tk()
        root.withdraw()  # 메인 창 숨기기
        
        file_types = [
            ("모든 지원 파일", "*.mp3;*.wav;*.m4a;*.flac;*.aac;*.ogg;*.txt"),
            ("오디오 파일", "*.mp3;*.wav;*.m4a;*.flac;*.aac;*.ogg"),
            ("STT 파일", "*.txt"),
            ("모든 파일", "*.*")
        ]
        
        file_path = filedialog.askopenfilename(
            title="파일 선택",
            filetypes=file_types,
            initialdir="/mnt/c/Users/KwakDaniel/Documents/KakaoTalk Downloads"
        )
        
        root.destroy()
        return file_path if file_path else None
    
    # GUI 실행
    root.mainloop()
    
    return selected_file[0]

def terminal_drag_drop():
    """Terminal drag and drop file selection"""
    print("\n** Terminal Drag & Drop **")
    print("=" * 40)
    print("Drag file from Windows Explorer to this terminal")
    print("(File path will be auto-filled)")
    print()
    
    while True:
        try:
            audio_file = input("File path: ").strip()
            
            # Remove quotes (automatically added when dragging)
            if audio_file.startswith('"') and audio_file.endswith('"'):
                audio_file = audio_file[1:-1]
            elif audio_file.startswith("'") and audio_file.endswith("'"):
                audio_file = audio_file[1:-1]
            
            if not audio_file:
                print("ERROR: Please drag a file or enter path.")
                continue
            
            # Convert Windows path to WSL path
            if audio_file.lower().startswith(("c:\\", "c:/")):
                if "\\" in audio_file:
                    audio_file = audio_file.replace("C:\\", "/mnt/c/").replace("\\", "/")
                else:
                    audio_file = audio_file.replace("C:/", "/mnt/c/").replace("c:/", "/mnt/c/")
                
                print(f"Converted to WSL path: {audio_file}")
            
            # Check supported file format
            supported_ext = ('.mp3', '.wav', '.m4a', '.flac', '.aac', '.ogg', '.txt')
            if not audio_file.lower().endswith(supported_ext):
                print(f"ERROR: Unsupported format. Supported: {', '.join(supported_ext)}")
                continue
            
            # Check file exists
            if os.path.exists(audio_file):
                print(f"OK: File found - {os.path.basename(audio_file)}")
                return audio_file
            else:
                print(f"ERROR: File not found - {audio_file}")
                retry = input("Try again? (y/n): ").strip().lower()
                if retry not in ['y', 'yes', '']:
                    return None
                    
        except KeyboardInterrupt:
            print("\n\nCancelled.")
            return None
        except EOFError:
            return None

def browse_directory(directory):
    """디렉토리 브라우징"""
    if not os.path.exists(directory):
        print(f"❌ 폴더를 찾을 수 없습니다: {directory}")
        return input_file_path()
    
    # 오디오 및 텍스트 파일 찾기
    files = []
    for file in os.listdir(directory):
        if file.lower().endswith(('.mp3', '.wav', '.m4a', '.flac', '.aac', '.ogg', '.txt')):
            files.append(file)
    
    if not files:
        print("❌ 지원되는 파일이 없습니다.")
        return input_file_path()
    
    # 파일 목록 표시
    files.sort()
    print(f"\n📂 {os.path.basename(directory)} 폴더의 파일들:")
    print("-" * 60)
    
    for i, file in enumerate(files, 1):
        file_path = os.path.join(directory, file)
        size_mb = os.path.getsize(file_path) / (1024 * 1024)
        if file.endswith('.txt') and 'STT' in file:
            print(f"{i:2d}. 📄 {file} ({size_mb:.1f} MB) [STT 파일]")
        else:
            print(f"{i:2d}. 🎵 {file} ({size_mb:.1f} MB)")
    
    print(f"{len(files)+1:2d}. 🔙 다른 폴더 선택")
    
    while True:
        try:
            choice = input(f"\n파일 선택 (1-{len(files)+1}): ").strip()
            if choice == str(len(files)+1):
                return select_file()
            
            file_index = int(choice) - 1
            if 0 <= file_index < len(files):
                selected_file = os.path.join(directory, files[file_index])
                print(f"\n✅ 선택된 파일: {files[file_index]}")
                return selected_file
            else:
                print("❌ 잘못된 선택입니다.")
        except ValueError:
            print("❌ 숫자를 입력해주세요.")

def input_file_path():
    """파일 경로 직접 입력"""
    while True:
        print("\n📁 음성 파일 경로를 입력하세요:")
        print("   (Windows 경로 예: C:\\Users\\사용자명\\Documents\\파일.m4a)")
        print("   (또는 파일을 드래그해서 경로를 붙여넣으세요)")
        
        audio_file = input("\n파일 경로: ").strip().strip('"').strip("'")
        
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
        
        # 파일 존재 확인
        if os.path.exists(audio_file):
            return audio_file
        else:
            print(f"❌ 파일을 찾을 수 없습니다: {audio_file}")
            retry = input("다시 시도하시겠습니까? (y/n): ").strip().lower()
            if retry not in ['y', 'yes', '']:
                print("프로그램을 종료합니다.")
                return None

def show_system_info():
    """시스템 자원 정보 표시"""
    print("\n💻 시스템 정보")
    print("-" * 40)
    print(f"OS: {platform.system()} {platform.release()}")
    print(f"CPU: {psutil.cpu_count(logical=False)}코어 / {psutil.cpu_count()}스레드")
    
    memory = psutil.virtual_memory()
    print(f"RAM: {memory.total / (1024**3):.1f}GB (사용가능: {memory.available / (1024**3):.1f}GB)")
    
    # GPU 확인 시도
    try:
        import torch
        if torch.cuda.is_available():
            gpu_count = torch.cuda.device_count()
            print(f"GPU: {gpu_count}개 사용가능 (CUDA {torch.version.cuda})")
            for i in range(gpu_count):
                gpu_name = torch.cuda.get_device_name(i)
                gpu_memory = torch.cuda.get_device_properties(i).total_memory / (1024**3)
                memory_allocated = torch.cuda.memory_allocated(i) / (1024**3)
                memory_cached = torch.cuda.memory_reserved(i) / (1024**3)
                print(f"  GPU {i}: {gpu_name} ({gpu_memory:.1f}GB)")
                print(f"         사용중: {memory_allocated:.1f}GB, 캐시: {memory_cached:.1f}GB")
        else:
            print("GPU: CUDA 사용 불가 (CPU만 사용)")
    except ImportError:
        print("GPU: PyTorch 미설치 (CPU만 사용)")
    
    print("-" * 40)

def monitor_resources():
    """자원 사용량 모니터링"""
    process = psutil.Process()
    
    # 시작 시점 정보
    initial_memory = process.memory_info().rss / (1024**2)  # MB
    initial_cpu = psutil.cpu_percent()
    
    print(f"📊 시작 시점 - 메모리: {initial_memory:.1f}MB, CPU: {initial_cpu:.1f}%")
    
    return process

def show_resource_usage(process, stage=""):
    """현재 자원 사용량 표시"""
    try:
        memory_mb = process.memory_info().rss / (1024**2)
        cpu_percent = process.cpu_percent()
        
        # 시스템 전체 정보
        system_memory = psutil.virtual_memory()
        system_cpu = psutil.cpu_percent()
        
        print(f"📊 {stage} - 프로세스: {memory_mb:.1f}MB, {cpu_percent:.1f}% CPU")
        print(f"   시스템: {system_memory.percent:.1f}% RAM, {system_cpu:.1f}% CPU")
        
        # GPU 메모리 정보
        try:
            import torch
            if torch.cuda.is_available():
                for i in range(torch.cuda.device_count()):
                    memory_allocated = torch.cuda.memory_allocated(i) / (1024**3)
                    memory_cached = torch.cuda.memory_reserved(i) / (1024**3)
                    total_memory = torch.cuda.get_device_properties(i).total_memory / (1024**3)
                    usage_percent = (memory_allocated / total_memory) * 100
                    print(f"   GPU {i}: {memory_allocated:.1f}GB/{total_memory:.1f}GB ({usage_percent:.1f}%)")
        except:
            pass
        
    except Exception as e:
        print(f"⚠️ 자원 모니터링 오류: {e}")

def complete_transcription_and_minutes():
    """완전한 STT + 표 형식 회의록 생성"""
    
    print("STT & Meeting Minutes Generator")
    print("=" * 60)
    
    # 시스템 정보 표시
    show_system_info()
    
    # 자원 모니터링 시작
    process = monitor_resources()
    
    # 터미널에서 바로 드래그 받기
    print("Drag audio file to terminal:")
    
    while True:
        try:
            audio_file = input("File path: ").strip()
            
            # 따옴표 제거
            if audio_file.startswith('"') and audio_file.endswith('"'):
                audio_file = audio_file[1:-1]
            elif audio_file.startswith("'") and audio_file.endswith("'"):
                audio_file = audio_file[1:-1]
            
            if not audio_file:
                print("Please drag a file")
                continue
            
            # Windows → WSL 경로 변환
            if audio_file.lower().startswith(("c:\\", "c:/")):
                if "\\" in audio_file:
                    audio_file = audio_file.replace("C:\\", "/mnt/c/").replace("\\", "/")
                else:
                    audio_file = audio_file.replace("C:/", "/mnt/c/").replace("c:/", "/mnt/c/")
                print(f"Converted: {audio_file}")
            
            # 파일 존재 확인
            if os.path.exists(audio_file):
                print(f"File found: {os.path.basename(audio_file)}")
                break
            else:
                print(f"File not found: {audio_file}")
                continue
                
        except KeyboardInterrupt:
            print("\nCancelled")
            return
    
    # 파일명과 출력 경로 설정
    base_name = os.path.splitext(os.path.basename(audio_file))[0]
    output_dir = os.path.dirname(audio_file)
    
    stt_output = os.path.join(output_dir, f"{base_name}_전사결과.txt")
    minutes_output = os.path.join(output_dir, f"{base_name}_회의록.txt")
    
    # 파일 정보 출력
    size_mb = os.path.getsize(audio_file) / (1024 * 1024)
    print(f"\n{'='*60}")
    print(f"✅ 선택된 파일: {os.path.basename(audio_file)}")
    print(f"💾 파일 크기: {size_mb:.1f} MB")
    print(f"📁 저장 위치: {output_dir}")
    print(f"{'='*60}")
    
    print("=== 음성 전사 및 회의록 생성 ===")
    
    # Check if file is already a text file (STT result)
    if audio_file.endswith('.txt') and 'STT' in os.path.basename(audio_file):
        print("📄 기존 STT 파일을 사용합니다...")
        # Read existing STT content
        with open(audio_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse the STT format to extract segments
        from types import SimpleNamespace
        segments = []
        lines = content.split('\n')
        
        for i, line in enumerate(lines):
            line = line.strip()
            if line:
                # Skip header lines and speaker timestamp lines
                if any(skip_word in line for skip_word in ['언어:', '2025.', '0분', 'STT', '완전한', '화자', '총']):
                    continue
                if '00:' in line:  # Skip timestamp lines
                    continue
                    
                # This should be actual speech content
                if line and len(line) > 1:  # Skip very short lines
                    segment = SimpleNamespace()
                    segment.text = line
                    segment.start = 0.0
                    segment.end = 0.0
                    segments.append(segment)
        
        # Create mock info object
        info = SimpleNamespace()
        info.language = "ko"
        info.language_probability = 1.0
        info.duration = 31.0  # From the file: 0분 31초
        
        print(f"✅ {len(segments)}개 문장 로드 완료")
    else:
        print("🔄 Large-v3 모델로 고품질 전사 시작...")
        show_resource_usage(process, "모델 로드 전")
        
        # Large 모델로 최고 품질 GPU 가속
        gpu_success = False
        
        # GPU 자동 감지 및 활성화
        try:
            import torch
            use_gpu = torch.cuda.is_available()
            if use_gpu:
                gpu_count = torch.cuda.device_count()
                gpu_name = torch.cuda.get_device_name(0)
                print(f"🎯 CUDA GPU 감지됨: {gpu_count}개 ({gpu_name})")
            else:
                print("⚠️ CUDA GPU를 사용할 수 없습니다.")
        except ImportError:
            use_gpu = False
            print("⚠️ PyTorch가 없습니다. CPU 모드로 실행합니다.")
            
        print(f"🔧 GPU 사용 설정: {'활성화' if use_gpu else '비활성화'}")
        
        if use_gpu:
            try:
                print(f"🚀 GPU 가속 사용 ({gpu_name})")
                print("📥 Large-v3 모델을 GPU로 로딩 중...")
                model = WhisperModel("large-v3", device="cuda", compute_type="float16")
                gpu_success = True
                print("✅ GPU 모델 로드 성공!")
                
                # GPU 메모리 사용량 확인
                if torch.cuda.is_available():
                    gpu_memory_used = torch.cuda.memory_allocated(0) / (1024**3)
                    gpu_memory_total = torch.cuda.get_device_properties(0).total_memory / (1024**3)
                    print(f"🎯 GPU 메모리 사용: {gpu_memory_used:.1f}GB / {gpu_memory_total:.1f}GB")
            except Exception as e:
                print(f"⚠️ GPU 실패 - CPU Large 모델로 전환: {str(e)[:50]}...")
                gpu_success = False
        
        # GPU를 사용할 수 없거나 실패한 경우 CPU 모드로 fallback
        if not use_gpu or not gpu_success:
            print("🖥️ CPU 모드 사용 (Large-v3 모델)")
            
            # Large 모델 사용하되 시스템 보호 설정 적용
            cpu_count = psutil.cpu_count(logical=False)  # 물리 코어 수
            max_workers = max(1, min(4, cpu_count // 2))  # 물리 코어의 절반만 사용
            
            print(f"🔧 Large-v3 모델 로드 중... (워커: {max_workers}개, CPU 제한)")
            model = WhisperModel(
                "large-v3", 
                device="cpu", 
                compute_type="int8",
                num_workers=max_workers
            )
        show_resource_usage(process, "모델 로드 완료")
        
        if gpu_success:
            print("🎤 GPU 가속 전사 시작... (Large-v3 모델)")
        else:
            print("🎤 CPU 전사 시작... (Large-v3 모델, 시스템 보호 설정)")
        
        # 실시간 진행 상태 표시
        print("📊 전사 진행 중... (세그먼트별로 실시간 표시됩니다)")
        print("=" * 60)
        
        segment_count = 0
        start_time = datetime.now()
        
        segments, info = model.transcribe(
            audio_file,
            beam_size=3,                    # 정확도와 속도 균형 (5→3)
            language="ko",                  # 한국어 설정
            vad_filter=True,               # 음성 활동 감지
            vad_parameters=dict(min_silence_duration_ms=500),  # VAD 세부 설정
            temperature=0.0,               # 일관성을 위해 고정
            compression_ratio_threshold=2.4,  # 더 엄격한 압축 임계값
            no_speech_threshold=0.6,       # 더 엄격한 무음 임계값
            condition_on_previous_text=False,  # 이전 텍스트에 의존하지 않음
            initial_prompt="한국어 회의 내용입니다. 정확한 전사가 필요합니다."
        )
        
        # 실시간 세그먼트 처리 및 진행 표시
        print("📝 전사 결과 처리 중...")
        segments_list = []
        
        for i, segment in enumerate(segments):
            segments_list.append(segment)
            
            # 실시간 진행 표시 (GPU 사용률 포함)
            elapsed = (datetime.now() - start_time).total_seconds()
            
            # GPU 메모리 사용량 표시 (10개마다)
            gpu_info = ""
            if gpu_success and i % 10 == 0 and torch.cuda.is_available():
                try:
                    gpu_memory_used = torch.cuda.memory_allocated(0) / (1024**3)
                    gpu_info = f" [GPU: {gpu_memory_used:.1f}GB]"
                except Exception:
                    # GPU 정보 가져오기 실패시 무시
                    pass
            
            print(f"✅ [{i+1:3d}] [{segment.start:6.1f}s → {segment.end:6.1f}s] {segment.text.strip()[:50]}{'...' if len(segment.text.strip()) > 50 else ''}{gpu_info}")
            
            # 5개 세그먼트마다 진행 상황 요약
            if (i + 1) % 5 == 0:
                print(f"📊 진행 상황: {i+1}개 세그먼트 완료 | 경과시간: {elapsed:.1f}초")
                print("-" * 60)
        
        total_elapsed = (datetime.now() - start_time).total_seconds()
        print("=" * 60)
        print(f"🎉 전사 완료! 총 {len(segments_list)}개 세그먼트 | 소요시간: {total_elapsed:.1f}초")
        
        show_resource_usage(process, "전사 완료")
        
        # GPU 메모리 정리 (안전하게)
        if gpu_success:
            try:
                import torch
                torch.cuda.empty_cache()
                print("🧹 GPU 메모리 정리 완료")
            except:
                pass
    
    print("🔧 STT 후처리 중...")
    # STT 후처리 - 용어 교정 및 개선
    segments_list = post_process_stt(segments_list)
    
    # STT 파일 저장 (UTF-8)
    with open(stt_output, 'w', encoding='utf-8') as f:
        f.write(f"{base_name} - 전사 결과\n")
        f.write(f"{datetime.now().strftime('%Y.%m.%d %H:%M')} ・ ")
        f.write(f"{int(info.duration//60)}분 {int(info.duration%60)}초\n")
        f.write(f"언어: {info.language} (확률: {info.language_probability:.1%})\n\n")
        
        # 화자 분리 수행
        print("🎭 화자 분리 시작...")
        try:
            from speaker_diarization import perform_speaker_diarization, apply_speaker_diarization_to_transcription, simple_time_based_diarization
            
            # 실제 화자 분리 시도
            speaker_segments = perform_speaker_diarization(audio_file, num_speakers=None)
            
            if speaker_segments:
                # 실제 화자 분리 성공
                segments_list = apply_speaker_diarization_to_transcription(segments_list, speaker_segments)
                print("✅ 실제 음성 특성 기반 화자 분리 적용 완료")
            else:
                # 실패시 시간 기반 화자 구분
                segments_list = simple_time_based_diarization(segments_list, gap_threshold=5.0, max_speakers=4)
                print("✅ 시간 기반 화자 구분 적용 완료")
        
        except ImportError:
            # pyannote.audio 없으면 시간 기반 사용
            from speaker_diarization import simple_time_based_diarization
            segments_list = simple_time_based_diarization(segments_list, gap_threshold=5.0, max_speakers=4)
            print("✅ 시간 기반 화자 구분 적용 완료 (pyannote.audio 미설치)")
        
        # 화자 정보를 포함한 STT 파일 저장
        for i, segment in enumerate(segments_list):
            
            start_min = int(segment.start // 60)
            start_sec = int(segment.start % 60)
            time_str = f"{start_min:02d}:{start_sec:02d}"
            
            # 화자 정보 사용 (있으면 segment.speaker, 없으면 기본값)
            speaker = getattr(segment, 'speaker', f"화자{((i//10)%4)+1}")
            
            f.write(f"{speaker} {time_str}\n")
            f.write(f"{segment.text.strip()}\n\n")
            
            if i % 50 == 0 and i > 0:
                print(f"   - {i}번째 구간 처리 중...")
        
        f.write(f"총 {len(segments_list)}개 구간 처리 완료\n")
    
    print("📊 회의 내용 분석 중...")
    
    # 전체 텍스트 분석
    all_text = " ".join([seg.text for seg in segments_list])
    
    print("🤖 AI를 사용해서 회의록 생성 중...")
    show_resource_usage(process, "AI 분석 전")
    
    # AI를 사용해서 회의록 생성
    meeting_analysis = analyze_meeting_with_ai(all_text)
    show_resource_usage(process, "AI 분석 완료")
    
    print("📄 회의록 파일 생성 중...")
    
    # 회의록 생성 (TXT 형식)
    create_meeting_minutes_txt(minutes_output, len(segments_list), info, meeting_analysis, base_name)
    
    print(f"\n{'='*60}")
    print(f"🎉 전사 및 회의록 생성 완료!")
    print(f"{'='*60}")
    print(f"📄 전사 파일: {os.path.basename(stt_output)}")
    print(f"📋 회의록 파일: {os.path.basename(minutes_output)}")
    print(f"📊 처리된 구간: {len(segments_list)}개")
    print(f"⏱️  총 길이: {int(info.duration//60)}분 {int(info.duration%60)}초")
    print(f"🌏 언어: {info.language} (확률: {info.language_probability:.1%})")
    print(f"📂 저장 위치: {output_dir}")
    print(f"{'='*60}")
    
    # 최종 자원 사용량
    show_resource_usage(process, "처리 완료")
    
    # GPU 사용 시 안전한 종료
    if 'gpu_success' in locals() and gpu_success:
        try:
            import torch
            torch.cuda.empty_cache()
            # 강제로 CUDA context 정리
            torch.cuda.synchronize()
            print("🧹 CUDA 컨텍스트 정리 완료")
        except:
            pass
        
        # 모델 객체 정리
        try:
            del model
            import gc
            gc.collect()
        except:
            pass
    
    # 처리 완료 안내
    print("\n✨ 프로그램 완료")

def post_process_stt(segments_list):
    """STT 후처리 - 용어 교정 및 개선"""
    try:
        # 사전 파일들에서 용어 사전 구축
        correction_dict = build_correction_dictionary()
        
        # 각 segment의 텍스트 교정
        processed_segments = []
        for segment in segments_list:
            corrected_text = apply_corrections(segment.text, correction_dict)
            # segment 객체를 새로운 텍스트로 업데이트 (속성 복사)
            processed_segment = type('Segment', (), {
                'start': segment.start,
                'end': segment.end,
                'text': corrected_text
            })()
            processed_segments.append(processed_segment)
        
        print(f"✅ STT 후처리 완료 - {len(correction_dict)}개 용어 교정 적용")
        return processed_segments
        
    except Exception as e:
        print(f"⚠️ STT 후처리 오류: {str(e)} - 원본 사용")
        return segments_list

def build_correction_dictionary():
    """참고 사전에서 교정 사전 구축"""
    correction_dict = {}
    
    try:
        # STT 참고 파일 경로
        stt_reference_path = "/mnt/c/Users/KwakDaniel/OneDrive/첨부 파일/interview_STT"
        
        if not os.path.exists(stt_reference_path):
            print(f"⚠️ 참고 사전 폴더를 찾을 수 없습니다: {stt_reference_path}")
            return correction_dict
        
        # 모든 .txt 파일 읽기
        txt_files = [f for f in os.listdir(stt_reference_path) if f.endswith('.txt')]
        
        # 조직명, 부서명, 전문용어 수집
        terms = set()
        
        for txt_file in txt_files[:5]:  # 처리 속도를 위해 상위 5개 파일만 사용
            file_path = os.path.join(stt_reference_path, txt_file)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                    # 부서명 추출
                    departments = ['기획처', '도로처', '구조물처', '기술마켓처', '미래전략처', 
                                 '안전혁신처', '설계처', '성과혁신처', '사업개발처', '인력처',
                                 '통행료시스템처', '재무처', '통행료정산센터', '통행료정책처',
                                 '해외사업처', '시설처', '기술심사처', 'ITS처', 'ITS지원센터',
                                 '교통처', '품질환경처', '건설처', '재난관리처', '토지공간실',
                                 '휴게사업처', '법무처', '총무처', '감사처', 'AI데이터부']
                    
                    for dept in departments:
                        if dept in content:
                            terms.add(dept)
                    
                    # 기술 용어 추출 (예시)
                    tech_terms = ['모바일오피스', '디지털관리처', '기술자문', '컨설팅',
                                '지역본부', '순회', '프라이버시', '학습데이터', 'xGP']
                    
                    for term in tech_terms:
                        if term in content:
                            terms.add(term)
                            
            except Exception as e:
                print(f"⚠️ 파일 읽기 오류 {txt_file}: {str(e)}")
                continue
        
        # 일반적인 오류 교정 사전 추가
        common_corrections = {
            # 조직명 교정
            '기획 처': '기획처',
            '도로 처': '도로처',
            '구조물 처': '구조물처',
            'AI 데이터부': 'AI데이터부',
            'AI데이터 부': 'AI데이터부',
            '미래 전략처': '미래전략처',
            '안전 혁신처': '안전혁신처',
            
            # 기술 용어 교정
            '모바일 오피스': '모바일오피스',
            '디지털 관리처': '디지털관리처',
            '기술 자문': '기술자문',
            '지역 본부': '지역본부',
            '학습 데이터': '학습데이터',
            'x GP': 'xGP',
            'X GP': 'xGP',
            
            # 일반적인 오류
            '그거를': '그것을',
            '그래 가지고': '그래서',
            '뭐 그런': '그런',
            '이제 뭐': '뭐',
        }
        
        correction_dict.update(common_corrections)
        
        print(f"📚 교정 사전 구축 완료: {len(correction_dict)}개 항목")
        return correction_dict
        
    except Exception as e:
        print(f"⚠️ 교정 사전 구축 오류: {str(e)}")
        return correction_dict

def apply_corrections(text, correction_dict):
    """텍스트에 교정 사전 적용"""
    corrected_text = text
    
    for wrong, correct in correction_dict.items():
        corrected_text = corrected_text.replace(wrong, correct)
    
    return corrected_text

def analyze_meeting_with_ai(meeting_text):
    """AI를 사용해서 회의 내용 분석"""
    import requests
    import json
    
    print("🔍 AI 분석 시작...")
    print(f"📝 분석할 텍스트 길이: {len(meeting_text):,}자")
    
    try:
        # qwen3-32b API 호출
        url = "http://localhost:11434/api/generate"
        print("🌐 Ollama API 연결 중...")
        
        prompt = f"""다음 회의 전사 내용을 분석해서 회의록을 작성해주세요.

회의 전사 내용:
{meeting_text}

다음 형식으로 회의록을 작성해주세요:

1. 회의 주제: (회의의 핵심 주제를 한 줄로 요약)

2. 주요 내용: (중요한 논의사항들을 번호별로 정리)
   1. 첫 번째 주요 논의사항
      - 세부 내용 1
      - 세부 내용 2
      - 세부 내용 3
   2. 두 번째 주요 논의사항
      - 세부 내용 1
      - 세부 내용 2

3. 이슈사항(미결사항): (해결되지 않은 문제나 추후 논의가 필요한 사항들)
   ◦ 첫 번째 이슈
   ◦ 두 번째 이슈

4. 결정사항: (회의에서 결정된 내용들)
   ◦ 첫 번째 결정사항
   ◦ 두 번째 결정사항

한국어로 작성하고, 구체적이고 명확하게 작성해주세요."""

        payload = {
            "model": "qwen3:8b",
            "prompt": prompt,
            "stream": False
        }
        
        print("🤖 qwen3-8b 모델로 분석 중... (1-2분 소요)")
        print("⏳ AI가 회의 내용을 분석하고 있습니다...")
        
        import time
        start_time = time.time()
        
        response = requests.post(url, json=payload, timeout=120)
        
        elapsed = time.time() - start_time
        
        print(f"🔍 API 응답 상태: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            analysis = result.get('response', '')
            print(f"✅ AI 분석 완료! (소요시간: {elapsed:.1f}초)")
            print(f"📊 AI 응답 길이: {len(analysis)}자")
            print(f"🔍 AI 응답 미리보기: {analysis[:200]}...")
            print("📋 회의록 구조화 중...")
            return parse_meeting_analysis(analysis)
        else:
            print(f"❌ AI analysis failed: {response.status_code}")
            print(f"🔍 Response text: {response.text}")
            return create_fallback_analysis(meeting_text)
            
    except Exception as e:
        print(f"❌ AI analysis error: {str(e)}")
        print(f"🔍 Error type: {type(e).__name__}")
        import traceback
        print(f"🔍 Traceback: {traceback.format_exc()}")
        print("🔄 Fallback 분석으로 전환...")
        return create_fallback_analysis(meeting_text)

def parse_meeting_analysis(ai_response):
    """AI 응답을 파싱해서 구조화된 데이터로 변환"""
    try:
        print(f"🔍 파싱 시작, 응답 길이: {len(ai_response)}")
        print(f"🔍 응답 내용 미리보기: {ai_response[:500]}...")
        lines = ai_response.strip().split('\n')
        analysis = {
            'subject': '',
            'main_contents': [],
            'issues': [],
            'decisions': []
        }
        
        current_section = None
        current_main_item = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            if '회의 주제:' in line or '주제:' in line:
                analysis['subject'] = line.split(':', 1)[-1].strip()
            elif '주요 내용:' in line or line.startswith('2.'):
                current_section = 'main_contents'
            elif '이슈사항' in line or '미결사항' in line:
                current_section = 'issues'
            elif '결정사항' in line:
                current_section = 'decisions'
            elif line.startswith(('1.', '2.', '3.', '4.', '5.')):
                if current_section == 'main_contents':
                    current_main_item = {
                        'title': line.split('.', 1)[-1].strip(),
                        'details': []
                    }
                    analysis['main_contents'].append(current_main_item)
            elif line.startswith(('- ', '◦ ', '• ')):
                if current_section == 'main_contents' and current_main_item:
                    current_main_item['details'].append(line[2:].strip())
                elif current_section == 'issues':
                    analysis['issues'].append(line[2:].strip())
                elif current_section == 'decisions':
                    analysis['decisions'].append(line[2:].strip())
        
        return analysis
        
    except Exception as e:
        print(f"❌ AI 응답 파싱 오류: {str(e)}")
        return create_fallback_analysis("")

def create_fallback_analysis(meeting_text):
    """AI 분석 실패시 폴백 분석"""
    return {
        'subject': '회의 내용 논의',
        'main_contents': [
            {
                'title': '주요 논의사항',
                'details': ['회의 내용이 논의되었습니다.', '추가 검토가 필요합니다.']
            }
        ],
        'issues': ['세부 사항 검토 필요'],
        'decisions': ['추후 논의 예정']
    }

def create_meeting_minutes_txt(output_path, segment_count, info, analysis, base_name):
    """PDF 양식에 맞는 회의록 TXT 생성"""
    
    with open(output_path, 'w', encoding='utf-8') as f:
        # 제목
        f.write("=" * 60 + "\n")
        f.write(" " * 25 + "회의록" + " " * 25 + "\n")
        f.write("=" * 60 + "\n\n")
        
        # 기본 정보
        f.write("┌─────────────────────────────────────────────────────────┐\n")
        f.write(f"│ 일시    : {datetime.now().strftime('%Y.%m.%d, %H:%M'):<45} │\n")
        f.write(f"│ 장소    : {'회의실':<45} │\n") 
        f.write(f"│ 회의주제 : {analysis['subject']:<44} │\n")
        f.write(f"│ 참석자   : 기관명 이름 직위 (인)                           │\n")
        f.write(f"│ 작성자   : AI 음성인식 시스템                             │\n")
        f.write("└─────────────────────────────────────────────────────────┘\n\n")
        
        # 회의 내용
        f.write("┌─────────────────────────────────────────────────────────┐\n")
        f.write("│                     회 의 내 용                        │\n")
        f.write("├─────────────────────────────────────────────────────────┤\n")
        f.write("│ 주요 내용 기술                                          │\n")
        f.write("├─────────────────────────────────────────────────────────┤\n")
        
        for i, content in enumerate(analysis['main_contents'], 1):
            f.write(f"│ {i}. {content['title']:<51} │\n")
            for detail in content['details']:
                f.write(f"│    - {detail[:49]:<49} │\n")
        
        f.write("└─────────────────────────────────────────────────────────┘\n\n")
        
        # 이슈사항
        f.write("┌─────────────────────────────────────────────────────────┐\n")
        f.write("│                이슈사항(미결사항)                        │\n")
        f.write("├─────────────────────────────────────────────────────────┤\n")
        
        for issue in analysis['issues']:
            f.write(f"│ ◦ {issue[:53]:<53} │\n")
        
        f.write("└─────────────────────────────────────────────────────────┘\n\n")
        
        # 첨부파일
        f.write("┌─────────────────────────────────────────────────────────┐\n")
        f.write("│                      첨부파일                           │\n")
        f.write("├─────────────────────────────────────────────────────────┤\n")
        f.write(f"│ ◦ {base_name}_전사결과.txt{'':<31} │\n")
        f.write(f"│ ◦ 음성파일: {base_name[:41]:<41} │\n")
        f.write("└─────────────────────────────────────────────────────────┘\n")

def create_meeting_minutes_docx_legacy(output_path, segment_count, info, analysis, base_name):
    """PDF 양식에 맞는 회의록 DOCX 생성"""
    
    temp_dir = tempfile.mkdtemp()
    
    try:
        # DOCX 구조 생성
        word_dir = os.path.join(temp_dir, "word")
        rels_dir = os.path.join(temp_dir, "_rels")
        docProps_dir = os.path.join(temp_dir, "docProps")
        
        os.makedirs(word_dir)
        os.makedirs(rels_dir) 
        os.makedirs(docProps_dir)
        
        # 기본 DOCX 파일들 생성
        create_basic_docx_structure(temp_dir, base_name)
        
        # PDF 양식에 맞는 회의록 문서 생성
        create_meeting_document(word_dir, base_name, info, analysis)
        
        # DOCX 파일로 압축
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arc_name = os.path.relpath(file_path, temp_dir)
                    zf.write(file_path, arc_name)
        
    finally:
        shutil.rmtree(temp_dir)

def create_basic_docx_structure(temp_dir, base_name):
    """기본 DOCX 파일 구조 생성"""
    
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
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/">
<dc:title>{base_name} 회의록</dc:title>
<dc:creator>AI 회의록 생성기</dc:creator>
<dcterms:created>{datetime.now().isoformat()}Z</dcterms:created>
</cp:coreProperties>'''
    
    with open(os.path.join(temp_dir, "docProps", "core.xml"), 'w', encoding='utf-8') as f:
        f.write(core_props)

def create_meeting_document(word_dir, base_name, info, analysis):
    """PDF 양식 기반 회의록 문서 생성"""
    
    # 주요 내용 문자열 생성
    main_content_str = ""
    for i, content in enumerate(analysis['main_contents'], 1):
        main_content_str += f"{i}. {content['title']}\n"
        for detail in content['details']:
            main_content_str += f"   - {detail}\n"
        main_content_str += "\n"
    
    # 이슈사항 문자열 생성
    issues_str = ""
    for issue in analysis['issues']:
        issues_str += f"◦ {issue}\n"
    
    # 결정사항이나 첨부파일 정보
    decisions_str = ""
    for decision in analysis.get('decisions', []):
        decisions_str += f"◦ {decision}\n"
    
    # word/document.xml - PDF 양식에 맞는 표 형태
    document_xml = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:body>

<!-- 제목 -->
<w:p>
<w:pPr><w:jc w:val="center"/></w:pPr>
<w:r><w:rPr><w:b/><w:sz w:val="32"/></w:rPr><w:t>회의록</w:t></w:r>
</w:p>

<w:p></w:p>

<!-- 기본 정보 표 -->
<w:tbl>
<w:tblPr>
<w:tblW w:w="5000" w:type="pct"/>
<w:tblBorders>
<w:top w:val="single" w:sz="4"/>
<w:left w:val="single" w:sz="4"/>
<w:bottom w:val="single" w:sz="4"/>
<w:right w:val="single" w:sz="4"/>
<w:insideH w:val="single" w:sz="4"/>
<w:insideV w:val="single" w:sz="4"/>
</w:tblBorders>
</w:tblPr>

<w:tr>
<w:tc>
<w:tcPr><w:tcW w:w="800" w:type="pct"/><w:shd w:val="clear" w:fill="D3D3D3"/></w:tcPr>
<w:p><w:r><w:t>일 시</w:t></w:r></w:p>
</w:tc>
<w:tc>
<w:tcPr><w:tcW w:w="1500" w:type="pct"/></w:tcPr>
<w:p><w:r><w:t>{datetime.now().strftime('%Y.%m.%d, %H:%M')}</w:t></w:r></w:p>
</w:tc>
<w:tc>
<w:tcPr><w:tcW w:w="800" w:type="pct"/><w:shd w:val="clear" w:fill="D3D3D3"/></w:tcPr>
<w:p><w:r><w:t>장 소</w:t></w:r></w:p>
</w:tc>
<w:tc>
<w:tcPr><w:tcW w:w="1900" w:type="pct"/></w:tcPr>
<w:p><w:r><w:t></w:t></w:r></w:p>
</w:tc>
</w:tr>

<w:tr>
<w:tc>
<w:tcPr><w:shd w:val="clear" w:fill="D3D3D3"/></w:tcPr>
<w:p><w:r><w:t>회의주제</w:t></w:r></w:p>
</w:tc>
<w:tc>
<w:tcPr><w:gridSpan w:val="3"/></w:tcPr>
<w:p><w:r><w:t>{analysis['subject']}</w:t></w:r></w:p>
</w:tc>
</w:tr>

<w:tr>
<w:tc>
<w:tcPr><w:shd w:val="clear" w:fill="D3D3D3"/></w:tcPr>
<w:p><w:r><w:t>참 석 자</w:t></w:r></w:p>
</w:tc>
<w:tc>
<w:tcPr><w:gridSpan w:val="3"/></w:tcPr>
<w:p><w:r><w:t>기관명 이름 직위 (인)</w:t></w:r></w:p>
</w:tc>
</w:tr>

<w:tr>
<w:tc>
<w:tcPr><w:shd w:val="clear" w:fill="D3D3D3"/></w:tcPr>
<w:p><w:r><w:t>작 성 자</w:t></w:r></w:p>
</w:tc>
<w:tc>
<w:tcPr><w:gridSpan w:val="3"/></w:tcPr>
<w:p><w:r><w:t>AI 음성인식 시스템</w:t></w:r></w:p>
</w:tc>
</w:tr>

</w:tbl>

<w:p></w:p>

<!-- 회의 내용 -->
<w:tbl>
<w:tblPr>
<w:tblW w:w="5000" w:type="pct"/>
<w:tblBorders>
<w:top w:val="single" w:sz="4"/>
<w:left w:val="single" w:sz="4"/>
<w:bottom w:val="single" w:sz="4"/>
<w:right w:val="single" w:sz="4"/>
<w:insideH w:val="single" w:sz="4"/>
<w:insideV w:val="single" w:sz="4"/>
</w:tblBorders>
</w:tblPr>

<w:tr>
<w:tc>
<w:tcPr><w:shd w:val="clear" w:fill="D3D3D3"/></w:tcPr>
<w:p><w:r><w:rPr><w:b/></w:rPr><w:t>회 의 내 용</w:t></w:r></w:p>
</w:tc>
</w:tr>

<w:tr>
<w:tc>
<w:tcPr><w:shd w:val="clear" w:fill="F5F5F5"/></w:tcPr>
<w:p><w:r><w:t>주요 내용 기술</w:t></w:r></w:p>
</w:tc>
</w:tr>

<w:tr>
<w:tc>
<w:p><w:r><w:t>{main_content_str.strip()}</w:t></w:r></w:p>
</w:tc>
</w:tr>

</w:tbl>

<w:p></w:p>

<!-- 이슈사항 -->
<w:tbl>
<w:tblPr>
<w:tblW w:w="5000" w:type="pct"/>
<w:tblBorders>
<w:top w:val="single" w:sz="4"/>
<w:left w:val="single" w:sz="4"/>
<w:bottom w:val="single" w:sz="4"/>
<w:right w:val="single" w:sz="4"/>
<w:insideH w:val="single" w:sz="4"/>
</w:tblBorders>
</w:tblPr>

<w:tr>
<w:tc>
<w:tcPr><w:shd w:val="clear" w:fill="D3D3D3"/></w:tcPr>
<w:p><w:r><w:rPr><w:b/></w:rPr><w:t>이슈사항(미결사항)</w:t></w:r></w:p>
</w:tc>
</w:tr>

<w:tr>
<w:tc>
<w:p><w:r><w:t>{issues_str.strip()}</w:t></w:r></w:p>
</w:tc>
</w:tr>

</w:tbl>

<w:p></w:p>

<!-- 첨부파일 -->
<w:tbl>
<w:tblPr>
<w:tblW w:w="5000" w:type="pct"/>
<w:tblBorders>
<w:top w:val="single" w:sz="4"/>
<w:left w:val="single" w:sz="4"/>
<w:bottom w:val="single" w:sz="4"/>
<w:right w:val="single" w:sz="4"/>
<w:insideH w:val="single" w:sz="4"/>
</w:tblBorders>
</w:tblPr>

<w:tr>
<w:tc>
<w:tcPr><w:shd w:val="clear" w:fill="D3D3D3"/></w:tcPr>
<w:p><w:r><w:rPr><w:b/></w:rPr><w:t>첨부파일</w:t></w:r></w:p>
</w:tc>
</w:tr>

<w:tr>
<w:tc>
<w:p><w:r><w:t>◦ {base_name}_전사결과.txt</w:t></w:r></w:p>
<w:p><w:r><w:t>◦ 음성파일: {base_name}</w:t></w:r></w:p>
</w:tc>
</w:tr>

</w:tbl>

</w:body>
</w:document>'''
    
    with open(os.path.join(word_dir, "document.xml"), 'w', encoding='utf-8') as f:
        f.write(document_xml)

if __name__ == "__main__":
    try:
        complete_transcription_and_minutes()
    except KeyboardInterrupt:
        print("\n❌ 사용자 중단")
    except Exception as e:
        print(f"\n❌ 오류 발생: {str(e)}")
        # GPU 정리 시도
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.synchronize()
        except:
            pass
    finally:
        # 안전한 종료를 위한 추가 정리
        import sys
        sys.exit(0)
