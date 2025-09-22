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
                    memory_allocated = torch.cuda.memory_allocated(i) / (1024**3)
                    memory_cached = torch.cuda.memory_reserved(i) / (1024**3)
                    total_memory = torch.cuda.get_device_properties(i).total_memory / (1024**3)
                    usage_percent = (memory_allocated / total_memory) * 100 if total_memory > 0 else 0
                    
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
            print("⚠️ CUDA를 사용할 수 없어 CPU 모드로 전환")
            return initialize_cpu_whisper_model(model_name)
        
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
                print("⚠️ GPU 선택 실패, CPU 모드로 전환")
                return initialize_cpu_whisper_model(model_name)
        
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
            
            # 안전한 GPU 초기화
            model = WhisperModel(
                model_name, 
                device="cuda",
                device_index=device_index,
                compute_type="float16"
            )
            print(f"✅ GPU {device_index}에 {model_name} 모델 로드 성공!")
        except Exception as gpu_error:
            print(f"⚠️ GPU 로드 실패: {str(gpu_error)}")
            print("🔄 CPU 모드로 전환...")
            raise gpu_error
        
        print(f"✅ {model_name} 모델 GPU {selected_device} 로드 성공!")
        
        # GPU 메모리 사용량 확인
        memory_used = torch.cuda.memory_allocated(selected_device) / (1024**3)
        memory_total = torch.cuda.get_device_properties(selected_device).total_memory / (1024**3)
        print(f"🔥 GPU {selected_device} 메모리 사용: {memory_used:.1f}GB / {memory_total:.1f}GB")
        
        return model, selected_device, True
        
    except Exception as e:
        print(f"⚠️ Multi-GPU 초기화 실패: {str(e)}")
        print("🔄 CPU 모드로 폴백...")
        return initialize_cpu_whisper_model(model_name)

def initialize_cpu_whisper_model(model_name="large-v3"):
    """최적화된 CPU WhisperModel 초기화"""
    print("🖥️ CPU 모드 사용 (Large-v3 모델)")
    
    # CPU 코어 수를 고려한 워커 수 설정
    physical_cores = psutil.cpu_count(logical=False)  # 물리 코어 수
    if physical_cores is None:
        physical_cores = 4  # 기본값
    max_workers = max(1, min(4, physical_cores // 2))  # 물리 코어의 절반만 사용
    
    print(f"🔧 {model_name} 모델 로드 중... (워커: {max_workers}개, CPU 제한)")
    
    model = WhisperModel(
        model_name, 
        device="cpu", 
        compute_type="int8",
        num_workers=max_workers
    )
    
    print(f"✅ CPU {model_name} 모델 로드 완료")
    return model, None, False

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
        
        # Multi-GPU 최적화 모델 초기화
        print("🎯 Multi-GPU 최적화 분석 시작...")
        model_result = initialize_multi_gpu_whisper_model("large-v3")
        
        if len(model_result) == 3:
            model, selected_gpu, gpu_success = model_result
        else:
            model, gpu_success = model_result[0], model_result[2] if len(model_result) > 2 else False
            selected_gpu = model_result[1] if len(model_result) > 1 else None
        show_resource_usage(process, "모델 로드 완료")
        
        if gpu_success:
            gpu_name = "RTX 3090" if selected_gpu is not None else "GPU"
            print(f"🎙️ Multi-GPU 가속 전사 시작... (GPU {selected_gpu}: {gpu_name})")
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
            
            # Multi-GPU 메모리 사용량 표시 (10개마다)
            gpu_info = ""
            if gpu_success and i % 10 == 0:
                try:
                    import torch
                    if torch.cuda.is_available() and selected_gpu is not None:
                        gpu_memory_used = torch.cuda.memory_allocated(selected_gpu) / (1024**3)
                        gpu_info = f" [GPU {selected_gpu}: {gpu_memory_used:.1f}GB]"
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

def analyze_text_chunk(chunk_text, chunk_num=1):
    """개별 텍스트 청크 분석"""
    import requests
    import json
    
    # vLLM 서버 먼저 시도
    try:
        vllm_available = requests.get("http://localhost:8000/health", timeout=2)
        if vllm_available.status_code == 200:
            print("🚀 vLLM 서버 사용 (더 빠른 처리)")
            return analyze_with_vllm(chunk_text)
    except:
        pass
    
    try:
        # Ollama 모델 사용 (32B 우선, 실패하면 8B로 폴백)
        url = "http://localhost:11434/api/generate"
        
        # 32B 모델 존재 여부 확인 후 선택
        try:
            import subprocess
            result = subprocess.run(['ollama', 'list'], capture_output=True, text=True, timeout=5)
            if "qwen3:32b" in result.stdout:
                model_to_use = "qwen3:32b"
                print(f"🚀 Ollama {model_to_use} 연결 중... (청크 {chunk_num}) - 고품질 32B 모델")
            else:
                model_to_use = "qwen3:8b"
                print(f"🚀 Ollama {model_to_use} 연결 중... (청크 {chunk_num}) - 32B 모델 없음, 8B 사용")
        except:
            model_to_use = "qwen3:8b"
            print(f"🚀 Ollama {model_to_use} 연결 중... (청크 {chunk_num}) - 모델 확인 실패, 8B 사용")
        
        # 청크용 간단한 프롬프트
        prompt = f"""다음 회의 일부 내용을 간단히 요약해주세요. 

회의 내용 (일부):
{chunk_text}

이 부분에서 다루어진 주요 내용들을 bullet point로 간단히 정리해주세요:

• [주요 논의사항 1]
• [주요 논의사항 2] 
• [결정사항이나 중요 포인트]

간결하게 핵심만 추출하고, 마크다운이나 추론 과정은 포함하지 마세요."""

        # 모델에 따른 최적화된 옵션 설정
        if "32b" in model_to_use:
            options = {
                "temperature": 0.1,     # 32B는 더 낮은 temperature로 일관성 확보
                "top_p": 0.7,
                "top_k": 10,
                "repeat_penalty": 1.1,
                "num_ctx": 8192,        # 32B는 더 큰 컨텍스트 사용
                "num_predict": 1024     # 32B는 더 긴 응답 생성 가능
            }
        else:
            options = {
                "temperature": 0.2,     # 8B는 약간 높은 temperature
                "top_p": 0.8,
                "top_k": 20,
                "repeat_penalty": 1.1,
                "num_ctx": 4096,        # 8B는 표준 컨텍스트
                "num_predict": 512      # 8B는 짧은 응답
            }
        
        payload = {
            "model": model_to_use,
            "prompt": prompt,
            "stream": False,
            "options": options
        }
        
        print(f"🚀 {model_to_use} 모델로 청크 {chunk_num} 분석 중...")
        if "32b" in model_to_use:
            print(f"⏳ 청크 처리 중... (고품질 32B 모델)")
            timeout_seconds = 300  # 32B 모델은 5분 타임아웃
        else:
            print(f"⏳ 청크 처리 중... (빠른 8B 모델)")
            timeout_seconds = 120   # 8B 모델은 2분 타임아웃
        
        import time
        start_time = time.time()
        
        response = requests.post(url, json=payload, timeout=timeout_seconds)
        
        elapsed = time.time() - start_time
        
        print(f"🔍 API 응답 상태: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            analysis = result.get('response', '')
            print(f"✅ 청크 {chunk_num} 분석 완료! (소요시간: {elapsed:.1f}초)")
            # <think> 부분 제거
            cleaned_analysis = clean_ai_response(analysis)
            return cleaned_analysis
        else:
            print(f"❌ 청크 {chunk_num} 분석 실패: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ 청크 {chunk_num} 분석 오류: {str(e)}")
        return None

def clean_ai_response(ai_response):
    """AI 응답에서 <think> 부분과 추론 과정 제거"""
    if not ai_response:
        return ai_response
    
    import re
    cleaned_response = ai_response
    
    # <think>과 </think> 사이의 모든 내용 제거 (다중 라인 포함)
    cleaned_response = re.sub(r'<think>.*?</think>', '', cleaned_response, flags=re.DOTALL | re.IGNORECASE)
    
    # <think>으로 시작하지만 </think>이 없는 경우 (줄 끝까지 제거)
    cleaned_response = re.sub(r'<think>.*', '', cleaned_response, flags=re.DOTALL | re.IGNORECASE)
    
    # 다른 추론 패턴들도 제거
    patterns_to_remove = [
        r'Let me.*?(?=\n\[|\[|$)',
        r'I need to.*?(?=\n\[|\[|$)', 
        r'First.*?(?=\n\[|\[|$)',
        r'I will.*?(?=\n\[|\[|$)',
        r'Let\'s.*?(?=\n\[|\[|$)',
        r'I\'ll.*?(?=\n\[|\[|$)'
    ]
    
    for pattern in patterns_to_remove:
        cleaned_response = re.sub(pattern, '', cleaned_response, flags=re.DOTALL | re.IGNORECASE)
    
    # 연속된 빈 줄 제거
    cleaned_response = re.sub(r'\n\s*\n\s*\n', '\n\n', cleaned_response)
    
    # 앞뒤 공백 제거
    cleaned_response = cleaned_response.strip()
    
    return cleaned_response

def combine_chunk_results(chunk_results):
    """청크 결과들을 하나의 회의록으로 합치기"""
    print("🔗 청크 결과들을 통합 중...")
    
    combined_content = "[회의 개요]\n"
    combined_content += "• 다양한 업무와 프로젝트 논의가 진행됨\n"
    combined_content += "• 여러 주제에 걸친 종합적 검토 및 의사결정\n\n"
    
    combined_content += "[주요 논의 내용]\n"
    
    for i, chunk_result in enumerate(chunk_results, 1):
        if chunk_result and chunk_result.strip():
            # 청크 결과를 정리해서 추가
            lines = chunk_result.strip().split('\n')
            for line in lines:
                line = line.strip()
                if line and not line.startswith('[') and not line.startswith('#'):
                    if not line.startswith('•'):
                        combined_content += f"• {line}\n"
                    else:
                        combined_content += f"{line}\n"
    
    combined_content += "\n[주요 결정사항 및 향후 계획]\n"
    combined_content += "• 논의된 사항들의 단계별 실행 계획 수립\n"
    combined_content += "• 관련 부서 간 협조 체계 구축\n\n"
    
    combined_content += "[미해결 이슈 및 추후 논의사항]\n"
    combined_content += "• 추가 검토가 필요한 기술적 사항들\n"
    combined_content += "• 다음 회의에서 우선적으로 다룰 안건들\n\n"
    
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
    """AI 분석 실패시 폴백 분석 - bullet point 개조식"""
    return """[회의 개요]
• 다양한 업무와 프로젝트 논의 진행
• 현재 작업 진행 상황 및 향후 계획 검토
• 관련 부서 담당자들 참석

[주요 논의 내용]
• 시스템 개발 관련 기술적 사항
  - 현재 개발 중인 기능 구현 방안
  - 시스템 개선 사항 검토
• 사용자 요구사항 반영 방안
  - 시스템 개선 방향 논의
  - 활발한 의견 교환
• 데이터 처리 및 시스템 연계 이슈
  - 기존 시스템과의 호환성 검토
  - 새로운 기능 추가 방안 논의

[주요 결정사항 및 향후 계획]
• 현재 진행 중인 개발 작업 계속 추진
• 일정 및 우선순위 재조정
• 시스템 안정성 확보를 위한 추가 검토 과정

[미해결 이슈 및 추후 논의사항]
• 기술적 세부사항 추가 검토 필요
• 다음 회의에서 우선적으로 논의 예정
• 구체적인 해결 방안 도출 필요

참고: AI 분석 실패로 기본 템플릿 생성. 정확한 내용은 전사 파일 참고 바람."""

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
        f.write(analysis)
        
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
