#!/usr/bin/env python3
"""
Hugging Face 토큰 설정 유틸리티
"""

import os
import subprocess

def setup_huggingface_token(token=None):
    """
    Hugging Face 토큰 설정
    
    Args:
        token (str, optional): Hugging Face 토큰
    """
    
    if not token:
        token = input("🔑 Hugging Face 토큰을 입력하세요: ").strip()
        if not token:
            print("❌ 토큰이 입력되지 않았습니다.")
            return False
    
    print("🔐 Hugging Face 토큰 설정 중...")
    
    # 방법 1: 환경변수 설정 (현재 세션)
    os.environ["HF_TOKEN"] = token
    os.environ["HUGGINGFACE_TOKEN"] = token
    print("✅ 환경변수에 토큰 설정 완료")
    
    # 방법 2: huggingface-cli 사용 (영구 저장)
    try:
        # huggingface-cli 설치 확인
        result = subprocess.run(['huggingface-cli', '--version'], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            print("🔧 huggingface-cli로 토큰 설정 중...")
            
            # 토큰 로그인
            login_result = subprocess.run(
                ['huggingface-cli', 'login', '--token', token],
                capture_output=True, text=True
            )
            
            if login_result.returncode == 0:
                print("✅ huggingface-cli 토큰 설정 완료")
            else:
                print(f"⚠️ huggingface-cli 설정 실패: {login_result.stderr}")
        else:
            print("⚠️ huggingface-cli가 설치되지 않음")
            
    except FileNotFoundError:
        print("⚠️ huggingface-cli가 설치되지 않음")
    
    # 방법 3: .bashrc에 영구 추가 (선택사항)
    bashrc_path = os.path.expanduser("~/.bashrc")
    token_line = f'export HF_TOKEN="{token}"'
    
    try:
        with open(bashrc_path, 'r') as f:
            content = f.read()
        
        if 'HF_TOKEN' not in content:
            with open(bashrc_path, 'a') as f:
                f.write(f'\n# Hugging Face Token for pyannote.audio\n')
                f.write(f'{token_line}\n')
            print("✅ ~/.bashrc에 토큰 영구 저장 완료")
            print("   다음 터미널 세션부터 자동 적용됩니다.")
        else:
            print("✅ ~/.bashrc에 이미 HF_TOKEN이 설정되어 있습니다.")
    
    except Exception as e:
        print(f"⚠️ ~/.bashrc 업데이트 실패: {e}")
    
    print("\n🎯 토큰 설정 완료! 이제 화자 분리 기능을 사용할 수 있습니다.")
    return True


def test_huggingface_access():
    """Hugging Face 접근 테스트"""
    print("🧪 Hugging Face 접근 테스트 중...")
    
    try:
        from huggingface_hub import login, whoami
        
        # 현재 설정된 토큰으로 로그인 테스트
        token = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_TOKEN")
        
        if token:
            login(token=token, add_to_git_credential=False)
            user_info = whoami()
            print(f"✅ 로그인 성공: {user_info['name']}")
            return True
        else:
            print("❌ 토큰을 찾을 수 없습니다.")
            return False
            
    except ImportError:
        print("⚠️ huggingface_hub가 설치되지 않았습니다.")
        print("   설치: uv add huggingface_hub")
        return False
        
    except Exception as e:
        print(f"❌ 접근 실패: {e}")
        return False


def install_diarization_dependencies():
    """화자 분리 의존성 설치"""
    print("📦 화자 분리 의존성 설치 중...")
    
    try:
        import subprocess
        
        # uv로 diarization 의존성 설치
        result = subprocess.run(['uv', 'sync', '--extra', 'diarization'], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ 화자 분리 패키지 설치 완료")
            return True
        else:
            print(f"❌ 설치 실패: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ 의존성 설치 오류: {e}")
        return False


if __name__ == "__main__":
    import sys
    
    print("🎭 Hugging Face 토큰 설정 도구")
    print("=" * 50)
    
    # 토큰 설정
    if len(sys.argv) > 1:
        custom_token = sys.argv[1]
        setup_huggingface_token(custom_token)
    else:
        setup_huggingface_token()
    
    print()
    
    # 의존성 설치
    install_diarization_dependencies()
    
    print()
    
    # 접근 테스트
    test_huggingface_access()
    
    print("\n🎉 설정 완료! 이제 다음 명령으로 화자 분리를 사용할 수 있습니다:")
    print("   uv run python app.py")
    print("   또는")
    print("   uv run python speaker_diarization.py <audio_file>")