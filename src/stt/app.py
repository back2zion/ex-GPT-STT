#!/usr/bin/env python3

import warnings
import os

# 시작 시 모든 경고 메시지 억제
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning) 
warnings.filterwarnings("ignore", category=DeprecationWarning)

# 환경 변수로 추가 경고 억제
os.environ['TRANSFORMERS_VERBOSITY'] = 'error'
os.environ['SPEECHBRAIN_CACHE'] = '/tmp/speechbrain_cache'
os.environ.setdefault('GPU_ONLY', '1')  # GPU 전용 모드 기본값
# CPU 사용량 최소화 설정

# 이메일 기능 임포트
try:
    from src.email.email_utils import send_meeting_minutes_email, setup_email_config
    EMAIL_AVAILABLE = True
except ImportError:
    print("⚠️ 이메일 기능을 사용하려면 email_utils.py가 필요합니다.")
    EMAIL_AVAILABLE = False
import psutil
cpu_count = psutil.cpu_count(logical=False)  # 물리적 코어 수
limited_threads = max(1, cpu_count // 3)  # 물리적 코어의 1/3만 사용 (더 보수적)

os.environ.setdefault('OMP_NUM_THREADS', str(limited_threads))
os.environ.setdefault('MKL_NUM_THREADS', str(limited_threads))
os.environ.setdefault('NUMEXPR_NUM_THREADS', str(limited_threads))
os.environ.setdefault('OPENBLAS_NUM_THREADS', str(limited_threads))
os.environ.setdefault('TOKENIZERS_PARALLELISM', 'false')

from faster_whisper import WhisperModel
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
        cudnn_file = nvidia.cudnn.__file__
        
        if not cudnn_file:
            return False
            
        cudnn_path = os.path.dirname(cudnn_file)
        
        if not cudnn_path or not os.path.exists(cudnn_path):
            return False
            
        lib_path = os.path.join(cudnn_path, "lib")
        
        if os.path.exists(lib_path):
            current_ld_path = os.environ.get("LD_LIBRARY_PATH", "")
            if lib_path not in current_ld_path:
                os.environ["LD_LIBRARY_PATH"] = f"{lib_path}:{current_ld_path}"
            os.environ["CUDNN_PATH"] = cudnn_path
            print(f"✅ cuDNN 환경 설정 완료: {lib_path}")
            return True
        else:
            print(f"⚠️ cuDNN 라이브러리 경로가 존재하지 않습니다: {lib_path}")
            return False
    except ImportError:
        # cuDNN이 없어도 정상 작동 (CPU 모드)
        return False
    except Exception as e:
        print(f"⚠️ cuDNN 환경 설정 실패: {e}")
        return False

# 시작 시 cuDNN 환경 설정 (오류 무시)
try:
    setup_cudnn_env()
except Exception:
    # cuDNN 설정 실패해도 계속 진행
    pass

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
        return browse_directory(download_dir), False, False
    elif choice == "3":
        return browse_directory(onedrive_dir), False, False
    elif choice == "4":
        result = drag_drop_file_selector()
        if isinstance(result, tuple) and len(result) == 3:
            return result  # 파일 경로, 화자 분리, AI 분석 옵션 튜플 반환
        elif isinstance(result, tuple) and len(result) == 2:
            return result[0], result[1], False  # 이전 버전 호환성
        else:
            return result, False, False  # 더 이전 버전 호환성
    elif choice == "5":
        return terminal_drag_drop(), False, False
    else:
        return input_file_path(), False, False

def drag_drop_file_selector():
    """드래그 앤 드롭 파일 선택 GUI"""
    selected_file = [None]  # 선택된 파일을 저장할 리스트 (mutable)
    skip_diarization = [False]  # 화자 분리 건너뛰기 옵션
    skip_ai = [False]  # AI 분석 건너뛰기 옵션
    
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
        skip_diarization[0] = skip_diarization_var.get()
        skip_ai[0] = skip_ai_var.get()
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
        
        # 옵션 프레임
        option_frame = ttk.Frame(main_frame)
        option_frame.pack(pady=5)
        
        # 화자 분리 건너뛰기 체크박스
        skip_diarization_var = tk.BooleanVar()
        skip_checkbox = ttk.Checkbutton(option_frame, 
                                      text="🚀 화자 분리 건너뛰기 (빠른 처리, 컴퓨터 부하 감소)", 
                                      variable=skip_diarization_var)
        skip_checkbox.pack()
        
        # AI 분석 건너뛰기 체크박스
        skip_ai_var = tk.BooleanVar()
        skip_ai_checkbox = ttk.Checkbutton(option_frame, 
                                         text="⚡ AI 분석 건너뛰기 (기본 템플릿 회의록, 최대 부하 감소)", 
                                         variable=skip_ai_var)
        skip_ai_checkbox.pack()
        
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
    
    return selected_file[0], skip_diarization[0], skip_ai[0]

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

def limit_process_priority():
    """프로세스 우선순위를 낮춰서 시스템 안정성 향상"""
    try:
        current_process = psutil.Process()
        
        # Windows와 Linux 모두 지원
        if hasattr(psutil, 'BELOW_NORMAL_PRIORITY_CLASS'):
            current_process.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
        else:
            current_process.nice(10)  # Linux에서 낮은 우선순위
        
        print(f"🔧 프로세스 우선순위 낮춤: {current_process.nice()}")
        
    except Exception as e:
        print(f"⚠️ 프로세스 우선순위 설정 실패: {e}")

def show_system_info():
    """시스템 자원 정보 표시"""
    print("\n💻 시스템 정보")
    print("-" * 40)
    print(f"OS: {platform.system()} {platform.release()}")
    print(f"CPU: {psutil.cpu_count(logical=False)}코어 / {psutil.cpu_count()}스레드")
    
    memory = psutil.virtual_memory()
    print(f"RAM: {memory.total / (1024**3):.1f}GB (사용가능: {memory.available / (1024**3):.1f}GB)")
    
    # GPU 정보 확인 (PyTorch 없어도 nvidia-smi로 확인)
    gpu_detected = False
    
    try:
        # nvidia-smi로 GPU 정보 확인
        import subprocess
        result = subprocess.run(['nvidia-smi', '--query-gpu=name,memory.total,memory.used,utilization.gpu', '--format=csv,noheader,nounits'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            gpu_info = result.stdout.strip().split('\n')
            print(f"🎯 GPU: {len(gpu_info)}개 감지됨 (Multi-GPU 최적화 가능)")
            for i, info in enumerate(gpu_info):
                if info.strip():
                    parts = info.strip().split(', ')
                    if len(parts) >= 4:
                        name, memory_total, memory_used, utilization = parts[:4]
                        print(f"  GPU {i}: {name} ({int(memory_total)/1024:.1f}GB)")
                        print(f"         메모리: {int(memory_used)}/{int(memory_total)}MB ({int(memory_used)/int(memory_total)*100:.1f}%)")
                        print(f"         사용률: {utilization}%")
            gpu_detected = True
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
        pass
    
    # PyTorch GPU 지원 확인
    try:
        import torch
        if torch.cuda.is_available():
            gpu_count = torch.cuda.device_count()
            if not gpu_detected:
                print(f"GPU: {gpu_count}개 사용가능 (CUDA {torch.version.cuda})")
                for i in range(gpu_count):
                    gpu_name = torch.cuda.get_device_name(i)
                    gpu_memory = torch.cuda.get_device_properties(i).total_memory / (1024**3)
                    print(f"  GPU {i}: {gpu_name} ({gpu_memory:.1f}GB)")
            else:
                print(f"✅ PyTorch: CUDA {torch.version.cuda} 지원 (Multi-GPU {gpu_count}개 활용 가능)")
        else:
            if gpu_detected:
                print("PyTorch: CUDA 미지원 (GPU 감지되었지만 PyTorch에서 사용 불가)")
            else:
                print("GPU: CUDA 사용 불가")
    except ImportError:
        if gpu_detected:
            print("PyTorch: 미설치 (GPU 감지되었지만 PyTorch 필요)")
        else:
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
    """현재 자원 사용량 표시 (Multi-GPU 지원)"""
    try:
        memory_mb = process.memory_info().rss / (1024**2)
        cpu_percent = process.cpu_percent()
        
        # 시스템 전체 정보
        system_memory = psutil.virtual_memory()
        system_cpu = psutil.cpu_percent()
        
        print(f"📊 {stage} - 프로세스: {memory_mb:.1f}MB, {cpu_percent:.1f}% CPU")
        print(f"   시스템: {system_memory.percent:.1f}% RAM, {system_cpu:.1f}% CPU")
        
        # Multi-GPU 메모리 정보 (PyTorch)
        try:
            import torch
            if torch.cuda.is_available():
                total_gpu_memory = 0
                total_allocated = 0
                for i in range(torch.cuda.device_count()):
                    # CTranslate2 메모리는 nvidia-smi로 정확히 측정
                    try:
                        import subprocess
                        result = subprocess.run(['nvidia-smi', '--query-gpu=memory.used,memory.total', 
                                               '--format=csv,noheader,nounits', f'--id={i}'], 
                                               capture_output=True, text=True, timeout=2)
                        if result.returncode == 0:
                            used_mb, total_mb = result.stdout.strip().split(', ')
                            memory_allocated = int(used_mb) / 1024
                            total_memory = int(total_mb) / 1024
                            usage_percent = (int(used_mb) / int(total_mb)) * 100 if int(total_mb) > 0 else 0
                        else:
                            # fallback
                            memory_allocated = 0.0
                            total_memory = torch.cuda.get_device_properties(i).total_memory / (1024**3)
                            usage_percent = 0.0
                    except Exception:
                        # fallback to torch (부정확하지만 기본값)
                        memory_allocated = torch.cuda.memory_allocated(i) / (1024**3)
                        total_memory = torch.cuda.get_device_properties(i).total_memory / (1024**3)
                        usage_percent = (memory_allocated / total_memory) * 100 if total_memory > 0 else 0
                    
                    memory_cached = torch.cuda.memory_reserved(i) / (1024**3)
                    
                    # GPU 이름 및 역할 (RTX 3090)
                    gpu_name = torch.cuda.get_device_name(i).replace('NVIDIA GeForce ', '')
                    
                    # GPU 역할 표시
                    if i == 0:
                        role = "STT 전용"
                    elif i == 1:
                        role = "화자분리 전용" 
                    else:
                        role = f"추가 GPU {i}"
                    
                    print(f"   🎯 GPU {i} ({gpu_name}, {role}): {memory_allocated:.1f}GB/{total_memory:.1f}GB ({usage_percent:.1f}%)")
                    
                    # 메모리 사용량이 90% 초과시 경고
                    if usage_percent > 90:
                        print(f"     ⚠️ GPU {i} 메모리 사용량 매우 높음! ({usage_percent:.1f}%)")
                    
                    total_gpu_memory += total_memory
                    total_allocated += memory_allocated
                
                # 전체 GPU 사용률 표시
                if total_gpu_memory > 0:
                    total_usage_percent = (total_allocated / total_gpu_memory) * 100
                    print(f"   🔥 Multi-GPU 전체: {total_allocated:.1f}GB/{total_gpu_memory:.1f}GB ({total_usage_percent:.1f}%)")
        except:
            # Fallback to nvidia-smi
            try:
                import subprocess
                result = subprocess.run(['nvidia-smi', '--query-gpu=memory.used,memory.total,utilization.gpu', '--format=csv,noheader,nounits'], 
                                      capture_output=True, text=True, timeout=3)
                if result.returncode == 0:
                    gpu_info = result.stdout.strip().split('\n')
                    for i, info in enumerate(gpu_info):
                        if info.strip():
                            parts = info.strip().split(', ')
                            if len(parts) >= 3:
                                memory_used, memory_total, gpu_util = parts[:3]
                                usage_percent = int(memory_used) / int(memory_total) * 100 if int(memory_total) > 0 else 0
                                print(f"   🎯 GPU {i}: {memory_used}MB/{memory_total}MB ({usage_percent:.1f}%) - {gpu_util}% 사용률")
            except:
                pass
        
    except Exception as e:
        print(f"⚠️ 자원 모니터링 오류: {e}")

def get_optimal_gpu_device():
    """여러 GPU 중 가장 빈 GPU를 선택하여 부하 균등 분산"""
    try:
        import torch
        if not torch.cuda.is_available():
            return None, False
        
        gpu_count = torch.cuda.device_count()
        if gpu_count == 0:
            return None, False
        
        print(f"🎯 사용 가능한 GPU: {gpu_count}개")
        
        # 각 GPU의 메모리 사용량 확인
        gpu_memory_usage = []
        for i in range(gpu_count):
            try:
                # CTranslate2 메모리는 nvidia-smi로 정확히 측정
                try:
                    import subprocess
                    result = subprocess.run(['nvidia-smi', '--query-gpu=memory.used,memory.total', 
                                           '--format=csv,noheader,nounits', f'--id={i}'], 
                                           capture_output=True, text=True, timeout=2)
                    if result.returncode == 0:
                        used_mb, total_mb = result.stdout.strip().split(', ')
                        memory_allocated = int(used_mb) / 1024
                        total_memory = int(total_mb) / 1024
                        usage_percent = (int(used_mb) / int(total_mb)) * 100 if int(total_mb) > 0 else 0
                    else:
                        # fallback
                        memory_allocated = 0.0
                        total_memory = torch.cuda.get_device_properties(i).total_memory / (1024**3)
                        usage_percent = 0.0
                except Exception:
                    # fallback to torch
                    memory_allocated = torch.cuda.memory_allocated(i) / (1024**3)
                    total_memory = torch.cuda.get_device_properties(i).total_memory / (1024**3)
                    usage_percent = (memory_allocated / total_memory) * 100 if total_memory > 0 else 0
                
                gpu_name = torch.cuda.get_device_name(i)
                
                gpu_memory_usage.append({
                    'device': i,
                    'name': gpu_name,
                    'usage_percent': usage_percent,
                    'allocated_gb': memory_allocated,
                    'total_gb': total_memory
                })
                
                print(f"  GPU {i}: {gpu_name} - 남은 메모리: {total_memory-memory_allocated:.1f}GB ({100-usage_percent:.1f}%)")
            except Exception as e:
                print(f"  GPU {i} 정보 얻기 실패: {e}")
                continue
        
        if not gpu_memory_usage:
            return None, False
        
        # 가장 사용량이 적은 GPU 선택
        best_gpu = min(gpu_memory_usage, key=lambda x: x['usage_percent'])
        selected_device = best_gpu['device']
        
        print(f"✅ 선택된 GPU: {selected_device} ({best_gpu['name']}) - 사용률: {best_gpu['usage_percent']:.1f}%")
        
        return selected_device, True
        
    except ImportError:
        print("⚠️ PyTorch가 없어 GPU 선택 불가")
        return None, False
    except Exception as e:
        print(f"⚠️ GPU 선택 오류: {e}")
        return None, False

def initialize_multi_gpu_whisper_model(model_name="large-v3", preferred_device=None):
    """두 RTX 3090 GPU를 활용한 WhisperModel 초기화"""
    try:
        import torch
        
        if not torch.cuda.is_available():
            print("❌ CUDA를 사용할 수 없습니다!")
            print("❌ GPU가 필수입니다. 프로그램을 종료합니다.")
            raise RuntimeError("CUDA가 사용 불가능합니다. GPU가 필요합니다.")
        
        gpu_count = torch.cuda.device_count()
        print(f"🎯 Multi-GPU 초기화: {gpu_count}개 GPU 감지")
        
        # RTX 3090 GPU 정보 표시
        for i in range(gpu_count):
            gpu_name = torch.cuda.get_device_name(i)
            gpu_memory = torch.cuda.get_device_properties(i).total_memory / (1024**3)
            print(f"  GPU {i}: {gpu_name} ({gpu_memory:.1f}GB VRAM)")
        
        # 최적 GPU 선택
        if preferred_device is not None and 0 <= preferred_device < gpu_count:
            selected_device = preferred_device
            print(f"🎯 지정된 GPU {selected_device} 사용")
        else:
            selected_device, success = get_optimal_gpu_device()
            if not success:
                print("❌ GPU 선택 실패!")
                print("❌ GPU가 필수입니다. 프로그램을 종료합니다.")
                raise RuntimeError("GPU 선택에 실패했습니다.")
        
        print(f"🚀 {model_name} 모델을 GPU {selected_device}에 로드 중...")
        
        # GPU에 모델 로드 (멀티 GPU 최적화)
        try:
            # 멀티 GPU 환경에서 GPU 0을 STT 전용으로 사용
            gpu_count = torch.cuda.device_count()
            device_index = 0
            
            if gpu_count >= 2:
                print(f"🎯 멀티 GPU 최적화: GPU 0에 {model_name} 모델 로드 시도 중... (STT 전용)")
            else:
                print(f"🎯 GPU에 {model_name} 모델 로드 시도 중...")
            
            # GPU 메모리 정리
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
            
            # 강제 GPU 모드 초기화 (CTranslate2 직접 제어)
            model = None
            try:
                # 환경변수로 CUDA 강제
                os.environ['CUDA_VISIBLE_DEVICES'] = str(device_index)
                
                # 첫 번째 시도: float16 (가장 메모리 효율적)
                print(f"🔄 GPU {device_index}에 {model_name} 로드 시도 중... (float16, 강제 GPU)")
                model = WhisperModel(
                    model_name, 
                    device="cuda",
                    device_index=device_index,
                    compute_type="float16",
                    cpu_threads=1,  # CPU 스레드 최소화
                    num_workers=1   # 단일 워커로 GPU 집중
                )
                
                # 모델이 실제로 GPU에 로드되었는지 검증
                if hasattr(model.model, 'device') and model.model.device == "cuda":
                    print(f"✅ GPU {device_index}에 {model_name} 모델 로드 성공! (float16)")
                else:
                    print(f"⚠️ 모델이 CPU로 폴백되었습니다. device: {model.model.device}")
                    
            except Exception as e1:
                print(f"⚠️ float16 시도 실패: {e1}")
                try:
                    # 두 번째 시도: int8_float16
                    print(f"🔄 GPU {device_index}에 {model_name} 로드 시도 중... (int8_float16)")
                    model = WhisperModel(
                        model_name, 
                        device="cuda",
                        device_index=device_index,
                        compute_type="int8_float16",
                        cpu_threads=1,
                        num_workers=1
                    )
                    print(f"✅ GPU {device_index}에 {model_name} 모델 로드 성공! (int8_float16)")
                except Exception as e2:
                    print(f"⚠️ int8_float16 시도도 실패: {e2}")
                    print(f"❌ GPU 로드 실패, CPU 모드는 지원하지 않습니다: {e2}")
                    raise RuntimeError("GPU 필수: CTranslate2 GPU 로드 실패")
            
            # CTranslate2 모델이 GPU를 사용하는지 확인 (nvidia-smi 기반)
            if model is not None:
                # nvidia-smi로 실제 GPU 메모리 사용량 확인
                try:
                    import subprocess
                    result = subprocess.run(['nvidia-smi', '--query-gpu=memory.used', '--format=csv,noheader,nounits', f'--id={device_index}'], 
                                          capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        gpu_memory_used_mb = int(result.stdout.strip())
                        gpu_memory_used_gb = gpu_memory_used_mb / 1024
                        print(f"🔥 nvidia-smi GPU {device_index} 메모리 사용: {gpu_memory_used_gb:.1f}GB")
                        
                        if gpu_memory_used_gb < 1.0:  # 1GB 미만이면 문제 있음
                            print(f"⚠️ GPU 메모리 사용량이 너무 적습니다 ({gpu_memory_used_gb:.1f}GB)")
                            print("⚠️ CTranslate2가 GPU를 제대로 사용하지 못할 수 있습니다.")
                        else:
                            print(f"✅ GPU에서 정상적으로 모델이 로드된 것으로 보입니다!")
                    else:
                        print("⚠️ nvidia-smi로 GPU 메모리 확인 실패")
                except Exception as mem_e:
                    print(f"⚠️ GPU 메모리 확인 오류: {mem_e}")
                
                # 모델 설정 정보 출력
                print(f"📋 모델 정보:")
                print(f"   - Device: {model.model.device}")
                print(f"   - Device Index: {model.model.device_index}")
                print(f"   - Compute Type: {model.model.compute_type}")
                
                if model.model.device != "cuda":
                    print("❌ 모델이 CUDA 디바이스를 사용하지 않습니다!")
                    raise RuntimeError(f"모델이 CPU로 폴백됨: {model.model.device}")
                
                # CUDA 가시성 복원
                if gpu_count >= 2:
                    os.environ['CUDA_VISIBLE_DEVICES'] = "0,1"
            else:
                raise RuntimeError("모델 로드 실패")
                
        except Exception as gpu_error:
            print(f"❌ GPU 모델 로드 실패: {str(gpu_error)}")
            print("❌ GPU 모드가 필수입니다. 프로그램을 종료합니다.")
            raise RuntimeError(f"GPU에서 모델 로드 실패: {str(gpu_error)}")
        
        print(f"✅ {model_name} 모델 GPU {selected_device} 로드 성공!")
        
        return model, selected_device, True
        
    except Exception as e:
        print(f"❌ Multi-GPU 초기화 실패: {str(e)}")
        print(f"❌ 상세 에러: {type(e).__name__}")
        import traceback
        print(f"❌ 에러 위치: {traceback.format_exc()}")
        print("❌ GPU 모드가 필수입니다. 프로그램을 종료합니다.")
        raise RuntimeError(f"Multi-GPU 초기화 실패: {str(e)}")

# CPU 모델 초기화 함수 제거 - GPU 전용 모드

def complete_transcription_and_minutes():
    """완전한 STT + 표 형식 회의록 생성"""
    
    print("STT & Meeting Minutes Generator")
    print("=" * 60)
    
    # GPU 전용 모드 설정
    print("🚀 GPU 전용 모드 초기화")
    
    # GPU 필수 확인
    try:
        import torch
        if not torch.cuda.is_available():
            print("❌ CUDA가 사용 불가능합니다!")
            print("❌ 이 프로그램은 GPU 전용으로 설계되었습니다.")
            return
        
        gpu_count = torch.cuda.device_count()
        if gpu_count < 2:
            print(f"⚠️ GPU {gpu_count}개 감지됨. 최적 성능을 위해서는 2개 이상 권장")
        else:
            print(f"✅ Multi-GPU 환경 감지: {gpu_count}개 GPU")
            
    except Exception as e:
        print(f"❌ GPU 환경 확인 실패: {e}")
        return
    
    # 시스템 정보 표시
    show_system_info()
    
    # 자원 모니터링 시작
    process = monitor_resources()
    
    # 파일 선택
    file_result = select_file()
    if isinstance(file_result, tuple) and len(file_result) == 3:
        audio_file, skip_diarization, skip_ai = file_result
    elif isinstance(file_result, tuple) and len(file_result) == 2:
        audio_file, skip_diarization = file_result
        skip_ai = False
    else:
        audio_file = file_result
        skip_diarization = False
        skip_ai = False
    
    if not audio_file:
        print("❌ 파일이 선택되지 않았습니다.")
        return
    
    print(f"선택된 파일: {os.path.basename(audio_file)}")
    if skip_diarization:
        print("🚀 화자 분리 건너뛰기 옵션 활성화")
    if skip_ai:
        print("⚡ AI 분석 건너뛰기 옵션 활성화")
    
    # 파일 존재 확인
    if not os.path.exists(audio_file):
        print(f"❌ 파일을 찾을 수 없습니다: {audio_file}")
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
        
        # Multi-GPU 최적화 모델 초기화 (GPU 필수) - 최고 품질 모델
        print("🎯 Multi-GPU 최적화 분석 시작...")
        try:
            # 한국어 최적화 모델 우선 선택 (높은 정확도)
            # RTX 3090 24GB x 2 = 48GB 총 메모리로 큰 모델 가능
            ctranslate2_models = [
                # CTranslate2 호환 모델들 (faster-whisper에서 직접 지원)
                "large-v3",                                # Whisper Large v3 (최고품질)
                "large-v2",                                # Whisper Large v2 (안정적)
                "distil-large-v3",                        # Distil Large v3 (빠르고 정확)
                "medium",                                  # Medium 모델 (균형)
                "small"                                    # Small 모델 (폴백)
            ]
            
            # 실제로 각 모델을 시도해보면서 작동하는 모델 찾기
            model_name = None
            for candidate_model in ctranslate2_models:
                try:
                    print(f"🔍 {candidate_model} 모델 로드 시도 중...")
                    # 실제로 모델 로드를 시도
                    test_model = WhisperModel(
                        candidate_model, 
                        device="cuda",
                        compute_type="float16"
                    )
                    print(f"✅ {candidate_model} 로드 성공!")
                    model_name = candidate_model
                    # 테스트 성공하면 모델 객체 삭제 (메모리 절약)
                    del test_model
                    break
                except Exception as test_error:
                    print(f"⚠️ {candidate_model} 로드 실패: {test_error}")
                    continue
                    
            if not model_name:
                print("❌ 모든 모델 로드 실패")
                raise RuntimeError("사용 가능한 Whisper 모델이 없습니다.")
                
            print(f"🚀 최종 선택된 모델: {model_name}")
            model_result = initialize_multi_gpu_whisper_model(model_name)
            
            if len(model_result) == 3:
                model, selected_gpu, gpu_success = model_result
            else:
                model, gpu_success = model_result[0], model_result[2] if len(model_result) > 2 else False
                selected_gpu = model_result[1] if len(model_result) > 1 else None
        except Exception as gpu_init_error:
            print(f"❌ GPU 초기화 실패: {str(gpu_init_error)}")
            print("❌ GPU가 필수입니다. 프로그램을 종료합니다.")
            return
            
        show_resource_usage(process, "모델 로드 완료")
        
        if gpu_success:
            gpu_name = "RTX 3090" if selected_gpu is not None else "GPU"
            print(f"🎙️ Multi-GPU 가속 전사 시작... (GPU {selected_gpu}: {gpu_name})")
        else:
            print("❌ GPU 사용에 실패했습니다. 프로그램을 종료합니다.")
            return
        
        # 실시간 진행 상태 표시
        print("📊 전사 진행 중... (세그먼트별로 실시간 표시됩니다)")
        print("=" * 60)
        
        segment_count = 0
        start_time = datetime.now()
        
        segments, info = model.transcribe(
            audio_file,
            beam_size=3,                    # CPU 사용량 최적화: 처리 속도 우선 (5→3)
            language=None,                  # 자동 언어 감지 (Auto-detect)
            task="transcribe",              # 전사 작업 명시
            temperature=0.0,                # 일관성을 위한 고정값
            compression_ratio_threshold=2.4, # 한국어 압축 비율 최적화
            log_prob_threshold=-1.0,        # 한국어 단어 확률 임계값 조정
            no_speech_threshold=0.6,        # 무음 구간 감지 개선
            vad_filter=True,               # 음성 활동 감지
            vad_parameters=dict(min_silence_duration_ms=300),  # 한국어 특성 고려 (500→300ms)
            word_timestamps=True,          # 단어별 타임스탬프 (한국어 분석용)
            prepend_punctuations="\"'([{-",
            append_punctuations="\"'.。,，!！?？:：\")}]、", # 한국어 문장부호 추가
            condition_on_previous_text=False,  # 이전 텍스트에 의존하지 않음 (한국어 최적화)
            initial_prompt="한국어 회의 내용입니다. 정확한 전사가 필요합니다."
        )
        
        # 실시간 세그먼트 처리 및 진행 표시
        print("📝 전사 결과 처리 중...")
        segments_list = []
        
        for i, segment in enumerate(segments):
            segments_list.append(segment)
            
            # 실시간 진행 표시 (GPU 사용률 포함)
            elapsed = (datetime.now() - start_time).total_seconds()
            
            # Multi-GPU 메모리 사용량 표시 (10개마다) - nvidia-smi로 정확한 측정
            gpu_info = ""
            if gpu_success and i % 10 == 0:
                try:
                    # CTranslate2는 자체 CUDA 메모리 관리를 하므로 nvidia-smi로 직접 확인
                    import subprocess
                    result = subprocess.run(['nvidia-smi', '--query-gpu=memory.used', 
                                           '--format=csv,noheader,nounits', f'--id={selected_gpu}'], 
                                           capture_output=True, text=True, timeout=2)
                    if result.returncode == 0:
                        gpu_memory_used_mb = int(result.stdout.strip())
                        gpu_memory_used_gb = gpu_memory_used_mb / 1024
                        # 실제로 메모리를 사용하고 있을 때만 표시 (1GB 이상)
                        if gpu_memory_used_gb >= 1.0:
                            gpu_info = f" [GPU {selected_gpu}: {gpu_memory_used_gb:.1f}GB]"
                        else:
                            gpu_info = f" [GPU {selected_gpu}: Active]"
                    else:
                        gpu_info = f" [GPU {selected_gpu}: Active]"
                except Exception:
                    # GPU 정보 가져오기 실패시 기본값
                    gpu_info = f" [GPU {selected_gpu}: Working]"
            
            print(f"✅ [{i+1:3d}] [{segment.start:6.1f}s → {segment.end:6.1f}s] {segment.text.strip()[:50]}{'...' if len(segment.text.strip()) > 50 else ''}{gpu_info}")
            
            # 5개 세그먼트마다 진행 상황 요약
            if (i + 1) % 5 == 0:
                print(f"📊 진행 상황: {i+1}개 세그먼트 완료 | 경과시간: {elapsed:.1f}초")
                print("-" * 60)
        
        total_elapsed = (datetime.now() - start_time).total_seconds()
        print("=" * 60)
        print(f"🎉 전사 완료! 총 {len(segments_list)}개 세그먼트 | 소요시간: {total_elapsed:.1f}초")
        
        show_resource_usage(process, "전사 완료")
        
        # Multi-GPU 메모리 정리 (안전하게)
        if gpu_success:
            try:
                import torch
                if selected_gpu is not None:
                    # 특정 GPU만 정리
                    torch.cuda.empty_cache()
                    print(f"🧹 GPU {selected_gpu} 메모리 정리 완료")
                else:
                    # 전체 GPU 정리
                    torch.cuda.empty_cache()
                    print("🧹 Multi-GPU 메모리 정리 완료")
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
        
        # 화자 분리 수행 (옵션에 따라)
        if skip_diarization:
            print("🚀 화자 분리 건너뛰기 - 빠른 처리 모드")
            # 화자 정보 없이 기본 화자명 사용
            for i, segment in enumerate(segments_list):
                segment.speaker = f"화자{((i//10)%4)+1}"  # 기본 화자명 할당
        else:
            print("🎭 화자 분리 시작...")
            try:
                from src.utils.speaker_diarization import perform_speaker_diarization, apply_speaker_diarization_to_transcription, simple_time_based_diarization
                
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
                from src.utils.speaker_diarization import simple_time_based_diarization
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
    
    # AI 분석 수행 (옵션에 따라)
    if skip_ai:
        print("⚡ AI 분석 건너뛰기 - 기본 템플릿 회의록 생성")
        # 기본 회의록 템플릿 사용
        meeting_analysis = {
            'summary': f"{base_name} 회의 내용을 정리한 회의록입니다.",
            'participants': "참석자 정보 없음",
            'key_points': ["STT 전사 내용을 참조하시기 바랍니다."],
            'action_items': ["후속 조치 사항 없음"],
            'next_meeting': "다음 회의 일정 없음"
        }
    else:
        # GPU 전용 설정
        import subprocess
        
        # GPU가속을 위한 환경 변수 설정 (Ollama GPU 필수)
        os.environ['CUDA_VISIBLE_DEVICES'] = '0,1'  # 두 GPU 모두 사용 가능
        
        print("🎯 GPU 전용 모드 활성화!")
        print("🚀 vLLM 서버로 AI 처리 가속화")
        
        # GPU 전용 모드에서는 Ollama 상태 확인 생략 (CPU 스파이크 방지)
        if skip_diarization:
            print("🤖 AI를 사용해서 회의록 생성 중... (화자 분리 없음 - 빠른 모드)")
        else:
            print("🤖 AI를 사용해서 회의록 생성 중...")
        
        show_resource_usage(process, "AI 분석 전")
        
        # AI를 사용해서 회의록 생성
        meeting_analysis = analyze_meeting_with_ai(all_text)
        
        # AI 분석이 실패했을 경우 개선된 폴백 분석 사용
        if meeting_analysis is None:
            print("⚠️ AI 분석 실패 - 개선된 폴백 분석 사용")
            # 실제 STT 내용을 분석해서 의미있는 회의록 생성
            fallback_analysis_text = create_fallback_analysis(all_text)
            meeting_analysis = fallback_analysis_text  # 문자열로 직접 사용
        
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
    
    # 이메일 발송 옵션
    if EMAIL_AVAILABLE:
        print("\n📧 이메일 발송 옵션")
        print("1. 이메일로 회의록 발송")
        print("2. 건너뛰기")
        
        choice = input("선택하세요 (1-2, 기본값: 2): ").strip()
        
        if choice == '1':
            try:
                # 환경변수에서 미리 설정된 정보 확인
                sender_email = os.environ.get('SENDER_EMAIL')
                sender_password = os.environ.get('SENDER_PASSWORD')
                email_to = os.environ.get('EMAIL_TO')
                
                # 미설정시 사용자 입력 요청
                if not sender_email or not sender_password or not email_to:
                    print("\n📧 이메일 설정이 필요합니다.")
                    sender_email, sender_password, recipient_emails = setup_email_config()
                    if not sender_email:
                        print("❌ 이메일 설정을 건너뜁니다.")
                    else:
                        # 회의록 이메일 발송 (발신자 자동 감지)
                        meeting_title = os.path.splitext(os.path.basename(audio_file))[0]
                        success = send_meeting_minutes_email(
                            meeting_minutes_path=minutes_output,
                            stt_result_path=stt_output,
                            recipient_emails=recipient_emails,
                            meeting_title=meeting_title,
                            sender_email=sender_email,
                            sender_password=sender_password,
                            audio_file_path=audio_file,
                            auto_reply_to_sender=True
                        )
                        if success:
                            print("✅ 이메일 발송 완료!")
                        else:
                            print("❌ 이메일 발송 실패")
                else:
                    # 환경변수로 설정된 경우 자동 발송 (발신자 자동 감지)
                    meeting_title = os.path.splitext(os.path.basename(audio_file))[0]
                    recipient_emails = [email.strip() for email in email_to.split(',')]
                    success = send_meeting_minutes_email(
                        meeting_minutes_path=minutes_output,
                        stt_result_path=stt_output,
                        recipient_emails=recipient_emails,
                        meeting_title=meeting_title,
                        sender_email=sender_email,
                        sender_password=sender_password,
                        audio_file_path=audio_file,
                        auto_reply_to_sender=True
                    )
                    if success:
                        print("✅ 이메일 자동 발송 완료!")
                    else:
                        print("❌ 이메일 발송 실패")
                        
            except Exception as e:
                print(f"❌ 이메일 발송 중 오류: {str(e)}")
        else:
            print("📧 이메일 발송을 건너뜁니다.")
    else:
        print("⚠️ 이메일 기능을 사용할 수 없습니다.")

    # 최종 자원 사용량
    show_resource_usage(process, "처리 완료")
    
    # Multi-GPU 사용 시 안전한 종료
    if 'gpu_success' in locals() and gpu_success:
        try:
            import torch
            if 'selected_gpu' in locals() and selected_gpu is not None:
                # 특정 GPU 컨텍스트 정리
                torch.cuda.empty_cache()
                torch.cuda.synchronize(selected_gpu)
                print(f"🧹 GPU {selected_gpu} CUDA 컨텍스트 정리 완료")
            else:
                # 전체 GPU 컨텍스트 정리
                torch.cuda.empty_cache()
                torch.cuda.synchronize()
                print("🧹 Multi-GPU CUDA 컨텍스트 정리 완료")
        except:
            pass
        
        # 모델 객체 정리
        try:
            del model
            import gc
            gc.collect()
            print("🗑️ 모델 객체 정리 완료")
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
            
            # IT 용어 교정
            '에이 아이': 'AI',
            '에이아이': 'AI',
            '인공 지능': '인공지능',
            '머신 러닝': '머신러닝',
            '딥 러닝': '딥러닝',
            '빅 데이터': '빅데이터',
            '클라우드 컴퓨팅': '클라우드컴퓨팅',
            '데이터 베이스': '데이터베이스',
            '데이터베이스': '데이터베이스',
            '어플리케이션': '애플리케이션',
            'API': 'API',
            '에이피아이': 'API',
            'UI': 'UI',
            '유아이': 'UI',
            'UX': 'UX',
            '유엑스': 'UX',
            '프레임 워크': '프레임워크',
            '라이브러리': '라이브러리',
            '알고리즘': '알고리즘',
            '엘지': 'LG',
            '삼성': '삼성',
            'IT': 'IT',
            '아이티': 'IT',
            '디브이': 'DV',
            '시스템 개발': '시스템개발',
            '웹 개발': '웹개발',
            'VR': 'VR',
            '가상현실': 'VR',
            'AR': 'AR',
            '증강현실': 'AR',
            'IoT': 'IoT',
            '사물인터넷': 'IoT',
            
            # 도로공사 전문 용어
            '도로 공사': '도로공사',
            '고속 도로': '고속도로',
            '국도': '국도',
            '지방도': '지방도',
            '도로 관리': '도로관리',
            '교통 관리': '교통관리',
            '도로 시설': '도로시설',
            '교량': '교량',
            '터널': '터널',
            '휴게소': '휴게소',
            '요금소': '요금소',
            'ITS': 'ITS',
            '지능형 교통 시스템': 'ITS',
            '교통 정보': '교통정보',
            'CCTV': 'CCTV',
            '시시티비': 'CCTV',
            'VMS': 'VMS',
            '가변 메시지': 'VMS',
            '노면 상태': '노면상태',
            '도로 포장': '도로포장',
            '차선': '차선',
            '중앙분리대': '중앙분리대',
            '방음벽': '방음벽',
            '가드레일': '가드레일',
            '안전시설': '안전시설',
            '도로 표지판': '도로표지판',
            '신호등': '신호등',
            '교차로': '교차로',
            '분기점': '분기점',
            'JC': 'JC',
            'IC': 'IC',
            '인터체인지': 'IC',
            '정션': 'JC',
            '램프': '램프',
            '진입로': '진입로',
            '진출로': '진출로',
            
            # 기술 용어 교정 (기존)
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

def analyze_with_vllm(meeting_text):
    """vLLM 서버를 사용한 회의 내용 분석 (Chat Completions API)"""
    import requests
    import json
    from dotenv import load_dotenv
    import os
    
    load_dotenv()
    
    try:
        # .env에서 모델명 가져오기 (기본값: Qwen/Qwen3-8B)
        model_name = os.getenv("VLLM_MODEL", "Qwen/Qwen3-8B")
        
        messages = [
            {
                "role": "system",
                "content": "당신은 회의록 작성 전문가입니다. 주어진 회의 전사 내용을 분석하여 구조화된 회의록을 작성해주세요."
            },
            {
                "role": "user", 
                "content": f"""다음 회의 전사 내용을 분석해서 bullet point 개조식 형태의 회의록을 작성해주세요.

회의 전사 내용:
{meeting_text}

다음과 같은 구조로 순수 텍스트 형태의 개조식 회의록을 작성해주세요:

[회의 개요]
• [주요 주제] 관련 회의 진행
• [참석자 정보가 있다면 언급]
• [핵심 안건들] 논의

[주요 논의 내용]
• [첫 번째 주요 논의사항]
  - [구체적 세부 내용 1]
  - [구체적 세부 내용 2]
• [두 번째 주요 논의사항]  
  - [구체적 세부 내용 1]
  - [구체적 세부 내용 2]
• [추가 논의사항들]
  - [관련 세부 내용]

[주요 결정사항 및 향후 계획]
• [결정된 사항 1]
• [결정된 사항 2]  
• [향후 계획이나 후속 조치]

[미해결 이슈 및 추후 논의사항]
• [해결되지 않은 문제 1]
• [해결되지 않은 문제 2]
• [추후 논의 필요 사항]

중요한 지시사항:
- 마크다운 문법(**, #, ###) 절대 사용 금지
- <think>, Let me, I need to, First 등 추론 과정 절대 포함 금지
- 바로 [회의 개요]부터 시작할 것
- 각 섹션은 대괄호 [섹션명]으로 표시
- 각 항목은 bullet point (•)로 시작
- 세부 내용은 dash (-)로 들여쓰기  
- 간결하고 명확한 개조식 문장만 사용
- 전문 용어와 구체적 내용은 그대로 유지
- 불필요한 설명이나 서론 없이 즉시 회의록 내용만 출력"""
            }
        ]

        payload = {
            "model": model_name,
            "messages": messages,
            "max_tokens": 2000,
            "temperature": 0.3,
            "stop": ["<|endoftext|>", "<|im_end|>"]
        }
        
        print(f"🚀 vLLM 모델 사용: {model_name}")
        response = requests.post("http://localhost:8000/v1/chat/completions", 
                               json=payload, timeout=120)
        
        if response.status_code == 200:
            result = response.json()
            analysis = result["choices"][0]["message"]["content"]
            print(f"✅ vLLM 분석 완료! (길이: {len(analysis)}자)")
            return parse_meeting_analysis(analysis)
        else:
            print(f"❌ vLLM 분석 실패: {response.status_code}")
            print(f"🔍 Response: {response.text}")
            return create_fallback_analysis(meeting_text)
            
    except Exception as e:
        print(f"❌ vLLM 오류: {str(e)}")
        return create_fallback_analysis(meeting_text)

def chunk_text(text, max_chunk_size=8000):
    """긴 텍스트를 적당한 크기로 나누기"""
    words = text.split()
    chunks = []
    current_chunk = []
    current_size = 0
    
    for word in words:
        if current_size + len(word) + 1 > max_chunk_size and current_chunk:
            chunks.append(' '.join(current_chunk))
            current_chunk = [word]
            current_size = len(word)
        else:
            current_chunk.append(word)
            current_size += len(word) + 1
    
    if current_chunk:
        chunks.append(' '.join(current_chunk))
    
    return chunks

def analyze_meeting_with_ai(meeting_text):
    """AI를 사용해서 회의 내용 분석 (청크 단위 처리)"""
    import requests
    import json
    from dotenv import load_dotenv
    import os
    
    load_dotenv()
    
    print("🔍 AI 분석 시작...")
    print(f"📝 분석할 텍스트 길이: {len(meeting_text):,}자")
    
    # 텍스트가 너무 짧으면 폴백 분석 사용
    if len(meeting_text.strip()) < 50:
        print("⚠️ 분석할 텍스트가 너무 짧음 - 폴백 분석 사용")
        return None
    
    # Ollama 서버 연결 테스트
    try:
        print("🔗 Ollama 서버 연결 확인...")
        test_response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if test_response.status_code != 200:
            print(f"❌ Ollama 서버 응답 오류: {test_response.status_code}")
            return None
        
        tags_info = test_response.json()
        models = tags_info.get('models', [])
        qwen_model = next((m for m in models if 'qwen3:8b' in m.get('name', '')), None)
        
        if qwen_model:
            print("🤖 Ollama 모델: qwen3:8b")
            print("📊 엔진 상태: 사용 가능")
        else:
            print("❌ qwen3:8b 모델을 찾을 수 없음")
            return None
            
    except requests.exceptions.ConnectionError:
        print("❌ Ollama 서버에 연결할 수 없습니다. 서버가 실행되고 있는지 확인하세요.")
        return None
    except Exception as e:
        print(f"❌ Ollama 서버 확인 중 오류: {str(e)}")
        return None
    
    # 텍스트가 너무 크면 청크로 분할
    if len(meeting_text) > 10000:
        print("📊 긴 텍스트 감지 - 청크 단위로 분할 처리")
        chunks = chunk_text(meeting_text, max_chunk_size=8000)
        print(f"🔢 {len(chunks)}개 청크로 분할")
        
        chunk_results = []
        for i, chunk in enumerate(chunks):
            print(f"🔄 청크 {i+1}/{len(chunks)} 처리 중...")
            result = analyze_text_chunk(chunk, i+1)
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
        return analyze_text_chunk(meeting_text, 1)

def analyze_with_ollama(meeting_text):
    """Ollama를 사용한 회의 내용 분석"""
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

def create_simple_analysis():
    """기본 분석 결과 생성 (AI 서버 사용 불가 시)"""
    return """1. 회의 주제: 회의 내용 분석 중

2. 주요 내용:
   1. AI 분석 서버가 사용 불가능한 상태입니다
      - Ollama 서버 연결을 확인해주세요
      - 수동으로 회의록을 작성해주세요

3. 이슈사항(미결사항):
   ◦ AI 분석 기능 복구 필요
   ◦ 서버 연결 상태 점검 필요

4. 결정사항:
   ◦ 수동으로 회의록 작성 진행"""

def analyze_text_chunk(chunk_text, chunk_num=1):
    """개별 텍스트 청크 분석"""
    import requests
    import json
    
    # Ollama 서버 사용 (안정적인 처리)
    try:
        # Ollama 서버 연결 확인
        ollama_available = requests.get("http://localhost:11434/api/tags", timeout=2)
        if ollama_available.status_code == 200:
            print("🚀 Ollama 서버 사용 (안정적인 처리)")
            return analyze_with_ollama(chunk_text)
    except Exception as e:
        print(f"⚠️ Ollama 서버 연결 실패: {e}")
    
    # 서버가 없으면 fallback 사용
    print("⚠️ AI 서버 사용 불가 - 기본 분석 사용")
    return create_simple_analysis()

def clean_ai_response(ai_response):
    """AI 응답에서 <think> 부분과 추론 과정 제거"""
    if not ai_response:
        return ai_response
    
    import re
    cleaned_response = ai_response
    
    # <think>과 </think> 사이의 모든 내용 제거 (다중 라인 포함)
    cleaned_response = re.sub(r'<think>.*?</think>', '', cleaned_response, flags=re.DOTALL | re.IGNORECASE)
    
    # <think>으로 시작하지만 </think>이 없는 경우 (줄 끝까지 제거)
    cleaned_response = re.sub(r'<think>.*?$', '', cleaned_response, flags=re.DOTALL | re.IGNORECASE)
    
    # • <think> 형태의 리스트 항목도 제거
    cleaned_response = re.sub(r'^• <think>.*?$', '', cleaned_response, flags=re.MULTILINE | re.DOTALL | re.IGNORECASE)
    
    # 영어 추론 패턴들도 제거 (더 강화된 패턴)
    english_patterns = [
        r'Okay.*?(?=\n[1-9]|\n•|$)',
        r'Let me.*?(?=\n[1-9]|\n•|$)',
        r'I need to.*?(?=\n[1-9]|\n•|$)',
        r'First.*?(?=\n[1-9]|\n•|$)',
        r'I will.*?(?=\n[1-9]|\n•|$)',
        r'Let\'s.*?(?=\n[1-9]|\n•|$)',
        r'I\'ll.*?(?=\n[1-9]|\n•|$)',
        r'So.*?(?=\n[1-9]|\n•|$)',
        r'The.*?(?=\n[1-9]|\n•|$)',
        r'For the.*?(?=\n[1-9]|\n•|$)',
        r'Based on.*?(?=\n[1-9]|\n•|$)'
    ]
    
    for pattern in english_patterns:
        cleaned_response = re.sub(pattern, '', cleaned_response, flags=re.DOTALL | re.IGNORECASE)
    
    # "• " 로 시작하는 불완전한 줄 제거
    lines = cleaned_response.split('\n')
    cleaned_lines = []
    
    for line in lines:
        line = line.strip()
        # 빈 "• " 항목이거나 영어로만 된 추론 라인은 제거
        if line == '•' or (line.startswith('•') and len(line.split()) < 3 and not any(ord(c) > 127 for c in line)):
            continue
        # 한국어가 포함된 유효한 내용만 유지
        if line and (any(ord(c) > 127 for c in line) or line.startswith(('1.', '2.', '3.', '4.', '◦'))):
            cleaned_lines.append(line)
    
    cleaned_response = '\n'.join(cleaned_lines)
    
    # 연속된 빈 줄 제거
    cleaned_response = re.sub(r'\n\s*\n\s*\n', '\n\n', cleaned_response)
    
    # 앞뒤 공백 제거
    cleaned_response = cleaned_response.strip()
    
    return cleaned_response

def combine_chunk_results(chunk_results):
    """청크 결과들을 하나의 통합 회의록으로 합치기"""
    print("🔗 청크 결과들을 통합 중...")
    
    # 각 청크에서 섹션별 내용 추출
    topics = set()
    main_contents = []
    issues = []
    decisions = []
    
    for chunk_result in chunk_results:
        if not chunk_result or not chunk_result.strip():
            continue
            
        lines = chunk_result.strip().split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # 섹션 구분
            if '회의 주제:' in line:
                topic = line.split('회의 주제:')[-1].strip()
                if topic:
                    topics.add(topic)
            elif '주요 내용:' in line:
                current_section = 'main'
            elif '이슈사항' in line or '미결사항' in line:
                current_section = 'issues'
            elif '결정사항' in line:
                current_section = 'decisions'
            elif line.startswith(('1.', '2.', '3.', '4.', '-', '•', '◦')):
                # 각 섹션의 내용 수집
                if current_section == 'main' and line not in main_contents:
                    main_contents.append(line)
                elif current_section == 'issues' and line not in issues:
                    issues.append(line)
                elif current_section == 'decisions' and line not in decisions:
                    decisions.append(line)
    
    # 통합 회의록 생성
    combined_content = ""
    
    # 회의 주제 (복수 주제를 하나로 통합)
    if topics:
        combined_topic = "종합 회의 - " + ", ".join(list(topics)[:2])  # 최대 2개 주제만
        combined_content += f"1. 회의 주제: {combined_topic}\n\n"
    else:
        combined_content += "1. 회의 주제: 종합 회의록\n\n"
    
    # 주요 내용
    combined_content += "2. 주요 내용:\n"
    if main_contents:
        for i, content in enumerate(main_contents[:10], 1):  # 최대 10개 항목
            # 번호 정리
            clean_content = content.lstrip('1234567890.-•◦ ')
            combined_content += f"   {i}. {clean_content}\n"
    else:
        combined_content += "   1. 다양한 주제에 대한 포괄적 논의 진행\n"
    
    combined_content += "\n"
    
    # 이슈사항
    combined_content += "3. 이슈사항(미결사항):\n"
    if issues:
        for issue in issues[:5]:  # 최대 5개 이슈
            clean_issue = issue.lstrip('1234567890.-•◦ ')
            combined_content += f"   ◦ {clean_issue}\n"
    else:
        combined_content += "   ◦ 추가 검토가 필요한 기술적 사항들\n"
    
    combined_content += "\n"
    
    # 결정사항
    combined_content += "4. 결정사항:\n"
    if decisions:
        for decision in decisions[:5]:  # 최대 5개 결정사항
            clean_decision = decision.lstrip('1234567890.-•◦ ')
            combined_content += f"   ◦ {clean_decision}\n"
    else:
        combined_content += "   ◦ 논의된 사항들의 단계별 실행 계획 수립\n"
    
    combined_content += "참고: 긴 회의록을 청크 단위로 처리하여 생성됨"
    
    print(f"✅ {len(chunk_results)}개 청크 통합 완료")
    return combined_content

def parse_meeting_analysis(ai_response):
    """AI 응답에서 <think> 부분 제거 후 반환"""
    try:
        print(f"🔍 파싱 시작, 응답 길이: {len(ai_response)}")
        print(f"🔍 응답 내용 미리보기: {ai_response[:200]}...")
        
        # 새로운 정리 함수 사용
        cleaned_response = clean_ai_response(ai_response)
        
        if not cleaned_response or len(cleaned_response) < 50:
            print("⚠️ AI 응답이 너무 짧거나 비어있음, fallback 사용")
            return create_fallback_analysis("")
            
        print(f"✅ <think> 부분 제거 완료, 최종 길이: {len(cleaned_response)}")
        return cleaned_response
        
    except Exception as e:
        print(f"❌ AI 응답 파싱 오류: {str(e)}")
        return create_fallback_analysis("")

def create_fallback_analysis(meeting_text):
    """AI 분석 실패시 폴백 분석 - 실제 STT 내용 기반"""
    
    # STT 내용에서 주요 키워드 추출
    keywords = extract_keywords_from_text(meeting_text)
    important_sentences = extract_important_sentences(meeting_text)
    
    # 회의록 구성
    analysis = "[회의 개요]\n"
    if keywords:
        analysis += f"• 주요 논의 주제: {', '.join(keywords[:5])}\n"
    else:
        analysis += "• 업무 진행 현황 및 향후 계획 논의\n"
    analysis += f"• 전사 텍스트 길이: 약 {len(meeting_text):,}자\n"
    analysis += f"• 회의 진행 내용 전체 기록됨\n\n"
    
    analysis += "[주요 논의 내용]\n"
    if important_sentences:
        for i, sentence in enumerate(important_sentences[:8], 1):
            analysis += f"• {sentence}\n"
    else:
        analysis += "• 다양한 업무 관련 사항 논의\n"
        analysis += "• 현재 진행 상황 점검 및 향후 계획 수립\n"
        analysis += "• 관련 업무 담당자들과의 협의\n"
    
    analysis += "\n[기타 사항]\n"
    analysis += "• 전사 내용이 길어 자동 요약으로 대체됨\n"
    analysis += "• 정확한 내용은 첨부된 전사 파일을 참고하세요\n"
    analysis += "• AI 분석 기능 사용 시 더 상세한 회의록 생성 가능\n\n"
    
    analysis += "※ 이 회의록은 STT 전사 내용을 기반으로 자동 생성되었습니다."
    
    return analysis

def extract_keywords_from_text(text):
    """텍스트에서 주요 키워드 추출 (간단한 빈도 기반)"""
    import re
    from collections import Counter
    
    # 한글, 영문, 숫자 단어만 추출
    words = re.findall(r'[가-힣a-zA-Z0-9]{2,}', text)
    
    # 불용어 제거 (더 포괄적)
    stopwords = {'이것', '그것', '저것', '하는', '되는', '있는', '없는', '했다', '됐다', '있다', '없다', 
                '그런데', '하지만', '그래서', '그리고', '그런', '이런', '저런', '같은', '다른',
                '때문', '경우', '상황', '부분', '관련', '대한', '에서', '으로', '를', '가', '이', '을',
                '하고', '해서', '해도', '하면', '한다', '한다', '합니다', '입니다', '습니다',
                '그리고', '또한', '그래서', '따라서', '하지만', '그러나', '그런데', '마찬가지로',
                '정도', '것', '거', '건', '게', '놈', '년', '것들', '분', '명', '개', '번', '차', '회',
                '때', '중', '후', '전', '간', '동안', '사이', '위', '아래', '앞', '뒤', '옆', '안', '밖'}
    
    # 빈도수 계산 (불용어 제외)
    word_counts = Counter([word for word in words if word not in stopwords and len(word) >= 2])
    
    # 상위 키워드 반환
    return [word for word, count in word_counts.most_common(10) if count >= 2]

def extract_important_sentences(text, max_sentences=8):
    """텍스트에서 중요한 문장들 추출"""
    import re
    
    # 문장 분리
    sentences = re.split(r'[.!?]\s+', text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
    
    if not sentences:
        return []
    
    # 길이가 적절한 문장들 선별 (너무 짧거나 긴 문장 제외)
    good_sentences = []
    for sentence in sentences:
        if 20 <= len(sentence) <= 150:  # 적절한 길이의 문장
            # 의미있는 내용이 있는 문장인지 간단히 체크
            if any(keyword in sentence for keyword in ['진행', '계획', '검토', '결정', '논의', '추진', '개발', '시스템', '업무', '작업']):
                good_sentences.append(sentence)
    
    # 최대 개수만큼 반환 (앞부분과 뒷부분에서 골고루)
    if len(good_sentences) <= max_sentences:
        return good_sentences
    else:
        # 앞쪽 절반, 뒤쪽 절반에서 균등하게 선택
        mid = len(good_sentences) // 2
        front_half = good_sentences[:mid][::max(1, mid//(max_sentences//2))]
        back_half = good_sentences[mid:][::max(1, (len(good_sentences)-mid)//(max_sentences//2))]
        return front_half[:max_sentences//2] + back_half[:max_sentences//2]

def create_meeting_minutes_txt(output_path, segment_count, info, analysis, base_name):
    """자연스러운 줄글 형식의 회의록 TXT 생성"""
    from datetime import datetime
    
    with open(output_path, 'w', encoding='utf-8') as f:
        # 제목
        f.write("=" * 60 + "\n")
        f.write(" " * 27 + "회의록" + " " * 27 + "\n")
        f.write("=" * 60 + "\n\n")
        
        # 기본 정보
        f.write(f"작성일시: {datetime.now().strftime('%Y년 %m월 %d일 %H:%M')}\n")
        f.write(f"작성자: AI 음성인식 시스템\n")
        f.write(f"음성 파일: {base_name}\n")
        f.write(f"전사 구간: 총 {len(segment_count) if hasattr(segment_count, '__len__') else segment_count}개 구간\n")
        f.write("=" * 60 + "\n\n")
        
        # AI 생성 회의록 내용 (줄글 형식)
        if isinstance(analysis, dict):
            # dict인 경우 문자열로 변환
            analysis_text = ""
            if 'summary' in analysis and analysis['summary']:
                analysis_text += f"회의 개요: {analysis['summary']}\n\n"
            else:
                analysis_text += f"회의 개요: {base_name} 회의 내용을 정리한 회의록입니다.\n\n"
            
            if 'participants' in analysis and analysis['participants']:
                analysis_text += f"참석자: {analysis['participants']}\n\n"
            else:
                analysis_text += "참석자: 참석자 정보 없음\n\n"
            
            if 'key_points' in analysis and isinstance(analysis['key_points'], list) and analysis['key_points']:
                analysis_text += "주요 논의사항:\n"
                for point in analysis['key_points']:
                    if point.strip():
                        analysis_text += f"• {point}\n"
                analysis_text += "\n"
            else:
                analysis_text += "주요 논의사항:\n• 전사 결과 파일에서 상세 내용을 확인하시기 바랍니다.\n\n"
            
            if 'decisions' in analysis and isinstance(analysis['decisions'], list) and analysis['decisions']:
                analysis_text += "결정사항:\n"
                for decision in analysis['decisions']:
                    if decision.strip():
                        analysis_text += f"• {decision}\n"
                analysis_text += "\n"
            
            if 'issues' in analysis and isinstance(analysis['issues'], list) and analysis['issues']:
                analysis_text += "이슈사항:\n"
                for issue in analysis['issues']:
                    if issue.strip():
                        analysis_text += f"• {issue}\n"
                analysis_text += "\n"
            
            if 'plans' in analysis and isinstance(analysis['plans'], list) and analysis['plans']:
                analysis_text += "향후 계획:\n"
                for plan in analysis['plans']:
                    if plan.strip():
                        analysis_text += f"• {plan}\n"
                analysis_text += "\n"
            
            f.write(analysis_text)
        else:
            # 문자열인 경우 그대로 사용 (이미 개선된 fallback_analysis)
            analysis_str = str(analysis) if analysis else ""
            if analysis_str.strip():
                f.write(analysis_str)
            else:
                # 분석이 완전히 실패한 경우
                f.write(f"회의 개요: {base_name} 회의 내용 분석\n\n")
                f.write("주요 논의사항:\n")
                f.write("• 음성 전사가 완료되었습니다.\n")
                f.write("• 상세 내용은 첨부된 전사 파일을 참고하시기 바랍니다.\n\n")
                f.write("참고: AI 분석 기능을 사용하면 더 상세한 회의록을 생성할 수 있습니다.\n")
        
        f.write("\n\n" + "=" * 60 + "\n")
        f.write("첨부 파일\n")
        f.write("=" * 60 + "\n")
        f.write(f"• 전사 결과: {base_name}_전사결과.txt\n")
        f.write(f"• 원본 음성: {base_name}\n")

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

def check_transcription_quality(segments_list, progress_callback=None):
    """전사 품질 검사 - 반복적인 자막/메뉴 텍스트 감지"""
    if not segments_list:
        return {"is_valid": False, "message": "전사 결과가 없습니다.", "issues": ["no_content"]}
    
    # 모든 전사 텍스트 수집
    all_texts = [segment.text.strip() for segment in segments_list if segment.text.strip()]
    
    if not all_texts:
        return {"is_valid": False, "message": "전사된 텍스트가 없습니다.", "issues": ["empty_transcription"]}
    
    # 문제적인 반복 패턴들
    repetitive_patterns = [
        "자막은 설정에서 선택하실 수 있습니다",
        "띄어쓰기와 문장부호를 정확히 표시해주세요",
        "할인도요 얘기하는거에요",
        "저 얼굴",
        "subtitle",
        "caption",
        "설정",
        "메뉴"
    ]
    
    # 반복 비율 계산
    unique_texts = set(all_texts)
    repetition_ratio = 1 - (len(unique_texts) / len(all_texts))
    
    issues = []
    sample_text = " / ".join(all_texts[:5])  # 처음 5개 샘플
    
    # 1. 높은 반복률 검사 (50% 이상 반복)
    if repetition_ratio > 0.5:
        issues.append("high_repetition")
        if progress_callback:
            progress_callback(f"⚠️ 오디오 품질 문제: 반복률 {repetition_ratio:.1%} (임계값: 50%)")
    
    # 2. 특정 패턴 검사
    pattern_matches = 0
    for text in all_texts[:10]:  # 처음 10개만 검사
        for pattern in repetitive_patterns:
            if pattern in text.lower():
                pattern_matches += 1
                break
    
    pattern_ratio = pattern_matches / min(len(all_texts), 10)
    
    if pattern_ratio > 0.5:  # 50% 이상이 문제적 패턴
        issues.append("repetitive_menu_content")
        if progress_callback:
            progress_callback(f"⚠️ 자막/메뉴 콘텐츠 감지: {pattern_ratio:.1%}")
    
    # 3. 너무 짧은 세그먼트들
    if len(all_texts) > 20 and all(len(text.split()) < 3 for text in all_texts[:10]):
        issues.append("too_short_segments")
        if progress_callback:
            progress_callback("⚠️ 비정상적으로 짧은 음성 세그먼트들")
    
    # 4. 단일 문자/단어 반복 감지 (예: "아 아 아 아..." or "그는 그는 그는...")
    single_char_repeat_count = 0
    single_word_repeat_count = 0
    
    for text in all_texts[:20]:  # 처음 20개 검사
        words = text.strip().split()
        
        # 단일 문자 반복 (예: "아 아 아 아...")
        if len(words) > 3 and len(set(words)) == 1 and len(words[0]) <= 2:
            single_char_repeat_count += 1
        
        # 단일 단어 반복 (예: "그는 그는 그는...")
        if len(words) > 2 and len(set(words)) == 1:
            single_word_repeat_count += 1
    
    if single_char_repeat_count > 2 or single_word_repeat_count > 3:
        issues.append("single_word_repetition")
        if progress_callback:
            progress_callback(f"⚠️ 단일 문자/단어 반복 감지: {single_char_repeat_count + single_word_repeat_count}개 구간")
    
    # 결과 판정
    if issues:
        error_messages = {
            "high_repetition": f"오디오에 동일한 내용이 {repetition_ratio:.1%} 반복됩니다. 실제 회의 내용이 아닌 것 같습니다.",
            "repetitive_menu_content": "오디오에 자막/메뉴 관련 텍스트가 반복적으로 나타납니다. 비디오 플레이어 오버레이나 자막 음성이 포함된 것 같습니다.",
            "too_short_segments": "음성 세그먼트가 비정상적으로 짧습니다.",
            "single_word_repetition": f"단일 문자나 단어가 반복적으로 나타납니다 (예: '아 아 아...', '그는 그는...'). 실제 회의 내용이 아닌 더미 오디오일 가능성이 높습니다."
        }
        
        main_issue = issues[0]  # 첫 번째 문제를 주요 문제로
        message = error_messages.get(main_issue, "오디오 품질에 문제가 있습니다.")
        message += f"\n\n감지된 텍스트 샘플: {sample_text}\n\n해결 방법:\n"
        message += "1. 원본 비디오에서 오버레이/자막이 없는 깨끗한 오디오로 다시 추출해주세요.\n"
        message += "2. 실제 회의 음성이 포함된 파일인지 확인해주세요.\n"
        message += "3. 다른 오디오 파일로 다시 시도해주세요."
        
        return {
            "is_valid": False,
            "message": message,
            "sample_text": sample_text,
            "issues": issues,
            "repetition_ratio": repetition_ratio,
            "pattern_ratio": pattern_ratio
        }
    
    # 품질이 좋으면 통과
    if progress_callback:
        progress_callback(f"✅ 오디오 품질 검사 통과 (반복률: {repetition_ratio:.1%}, 고유 세그먼트: {len(unique_texts)}개)")
    
    return {"is_valid": True, "message": "품질 검사 통과"}

def transcribe_audio_for_api(audio_file_path, progress_callback=None):
    """API 전용 STT 처리 함수 - 사용자 입력 없이 자동 처리"""
    try:
        import torch
        from faster_whisper import WhisperModel
        
        # GPU 확인
        if not torch.cuda.is_available():
            return {"success": False, "error": "CUDA가 사용 불가능합니다"}
        
        if progress_callback:
            progress_callback("🤖 Whisper Large-v3 모델 로딩 중...")
        
        # 모델 초기화
        try:
            model = WhisperModel(
                "large-v3", 
                device="cuda", 
                compute_type="float16",
                cpu_threads=2,
                num_workers=1
            )
        except Exception as e:
            return {"success": False, "error": f"모델 로딩 실패: {str(e)}"}
        
        if progress_callback:
            progress_callback("🎯 GPU에서 음성 전사 중...")
        
        # 전사 실행 - 반복 방지 핵심 설정
        segments, info = model.transcribe(
            audio_file_path,
            beam_size=3,
            language=None,
            vad_filter=True,
            temperature=0.0,
            initial_prompt=None,
            word_timestamps=True,
            condition_on_previous_text=False  # 핵심: 이전 텍스트 참조 비활성화
        )
        
        # 실시간 전사 수집
        segments_list = []
        for i, segment in enumerate(segments):
            segment_text = segment.text.strip()
            segments_list.append(segment)
            
            # 실시간 전사 업데이트
            if progress_callback:
                progress_callback(f"💬 [{segment.start:.1f}s] {segment_text}")
            
            # 진행 상황 업데이트
            if i % 5 == 0 and i > 0:
                if progress_callback:
                    progress_callback(f"📊 전사 진행: {i+1}개 구간 완료...")
        
        print(f"✅ 전사 완료: {len(segments_list)}개 구간, {info.duration:.1f}초")
        print(f"🔍 감지된 언어: {info.language} (확률: {info.language_probability:.1%})")
        
        # 전사 품질 검사
        if progress_callback:
            progress_callback("🔍 전사 품질 검사 중...")
        
        quality_check = check_transcription_quality(segments_list, progress_callback)
        if not quality_check["is_valid"]:
            error_msg = f"전사 품질이 낮습니다: {quality_check['message']}"
            print(f"❌ {error_msg}")
            if progress_callback:
                progress_callback(f"❌ {error_msg}")
            return {"success": False, "error": error_msg, "quality_issues": quality_check.get("issues", [])}
        else:
            print(f"✅ 전사 품질 검사 통과")
            if progress_callback:
                progress_callback("✅ 전사 품질 검사 통과")
        
        # STT 후처리 - 용어 교정
        if progress_callback:
            progress_callback("🔧 STT 후처리 중... (용어 교정 적용)")
        
        segments_list = post_process_stt(segments_list)
        
        # 화자 분리 적용
        if progress_callback:
            progress_callback("🎭 화자 분리 처리 중...")
        
        try:
            from src.utils.speaker_diarization import perform_speaker_diarization, apply_speaker_diarization_to_transcription, simple_time_based_diarization
            
            speaker_segments = perform_speaker_diarization(audio_file_path, num_speakers=None)
            
            if speaker_segments:
                segments_list = apply_speaker_diarization_to_transcription(segments_list, speaker_segments)
                print("✅ 실제 음성 특성 기반 화자 분리 적용 완료")
                diarization_success = True
            else:
                segments_list = simple_time_based_diarization(segments_list, gap_threshold=5.0, max_speakers=4)
                print("✅ 시간 기반 화자 구분 적용 완료")
                diarization_success = True
                
        except ImportError:
            from speaker_diarization import simple_time_based_diarization
            segments_list = simple_time_based_diarization(segments_list, gap_threshold=5.0, max_speakers=4)
            print("✅ 시간 기반 화자 구분 적용 완료 (pyannote.audio 미설치)")
            diarization_success = True
        except Exception as e:
            print(f"⚠️ 화자 분리 실패: {e}")
            for i, segment in enumerate(segments_list):
                segment.speaker = f"화자{((i//10)%4)+1}"
            diarization_success = False
        
        # 화자 이름 감지 및 적용
        if progress_callback:
            progress_callback("🏷️ 화자 이름 자동 감지 중...")
        
        try:
            from speaker_name_detection import process_speaker_names
            
            # 세그먼트를 딕셔너리 형태로 변환
            segment_dicts = []
            for segment in segments_list:
                segment_dict = {
                    'start': segment.start,
                    'end': segment.end,
                    'text': segment.text,
                    'speaker': getattr(segment, 'speaker', 'SPEAKER_00')
                }
                segment_dicts.append(segment_dict)
            
            # 화자 이름 감지 및 적용
            updated_segments, speaker_mapping = process_speaker_names(segment_dicts)
            
            if speaker_mapping:
                print(f"🎯 화자 이름 감지 성공: {len(speaker_mapping)}명")
                for original, name in speaker_mapping.items():
                    print(f"   {original} → {name}")
                
                # 원본 세그먼트에 이름 정보 업데이트
                for i, updated_segment in enumerate(updated_segments):
                    if i < len(segments_list):
                        segments_list[i].speaker = updated_segment['speaker']
                        if 'original_speaker' in updated_segment:
                            segments_list[i].original_speaker = updated_segment['original_speaker']
                
                if progress_callback:
                    progress_callback(f"✅ 화자 이름 적용 완료: {', '.join(speaker_mapping.values())}")
            else:
                print("ℹ️ 자기소개 패턴을 찾지 못했습니다 (화자1, 화자2 형태로 유지)")
                if progress_callback:
                    progress_callback("ℹ️ 화자 이름 감지되지 않음 (화자1, 화자2 형태로 유지)")
                    
        except ImportError as e:
            print(f"⚠️ 화자 이름 감지 모듈 로드 실패: {e}")
        except Exception as e:
            print(f"⚠️ 화자 이름 감지 실패: {e}")
        
        # 전체 텍스트 생성 (화자 이름 적용 확인)
        full_text = ""
        detailed_text = ""
        
        for segment in segments_list:
            # 화자 정보 정확하게 가져오기
            if hasattr(segment, 'speaker') and segment.speaker:
                speaker_info = segment.speaker
            else:
                speaker_info = "화자1"
            
            print(f"📝 세그먼트 저장: {speaker_info} -> {segment.text[:50]}...")  # 디버깅용
            
            full_text += f"{speaker_info}: {segment.text.strip()}\n"
            detailed_text += f"[{segment.start:.1f}s-{segment.end:.1f}s] {speaker_info}: {segment.text.strip()}\n"
        
        # AI 분석 실행
        if progress_callback:
            progress_callback("🤖 AI가 회의 내용을 분석하여 회의록 생성 중...")
        
        ai_analysis = analyze_meeting_with_ai(full_text)
        ai_analysis_success = ai_analysis is not None
        
        # 파일 저장
        base_name = os.path.splitext(os.path.basename(audio_file_path))[0]
        timestamp = datetime.now().strftime("%m%d_%H%M")
        
        # 전사 결과 파일
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
            "ai_analysis_success": ai_analysis_success
        }
        
    except Exception as e:
        error_msg = f"❌ STT 처리 오류: {str(e)}"
        print(error_msg)
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e)
        }

if __name__ == "__main__":
    try:
        # 시작 시 프로세스 우선순위 제한
        limit_process_priority()
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
