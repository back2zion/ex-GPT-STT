#!/usr/bin/env python3

"""
환경변수 로드 유틸리티
.env 파일에서 환경변수를 로드하여 시스템에 설정
"""

import os
from pathlib import Path

def load_env_variables(env_file_path=None):
    """
    .env 파일에서 환경변수를 로드
    
    Args:
        env_file_path: .env 파일 경로 (None이면 현재 디렉토리의 .env 사용)
    """
    if env_file_path is None:
        env_file_path = Path.cwd() / ".env"
    else:
        env_file_path = Path(env_file_path)
    
    if not env_file_path.exists():
        print(f"⚠️ 환경변수 파일을 찾을 수 없습니다: {env_file_path}")
        return False
    
    try:
        with open(env_file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                
                # 주석이나 빈 줄 건너뛰기
                if not line or line.startswith('#'):
                    continue
                
                # KEY=VALUE 형식 파싱
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # 따옴표 제거
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]
                    
                    os.environ[key] = value
                    
                else:
                    print(f"⚠️ 잘못된 형식 (라인 {line_num}): {line}")
        
        print(f"✅ 환경변수 로드 완료: {env_file_path}")
        return True
        
    except Exception as e:
        print(f"❌ 환경변수 로드 실패: {e}")
        return False

def print_loaded_env_vars(mask_sensitive=True):
    """
    로드된 환경변수 출력 (민감한 정보는 마스킹)
    
    Args:
        mask_sensitive: 민감한 정보 마스킹 여부
    """
    sensitive_keys = {'PASSWORD', 'TOKEN', 'SECRET', 'KEY', 'AUTH'}
    
    print("📋 로드된 환경변수:")
    print("-" * 40)
    
    env_vars = {k: v for k, v in os.environ.items() 
                if k.startswith(('HF_', 'OLLAMA_', 'SENDER_', 'VLLM_', 'TRANSCRIPTION_', 'AI_'))}
    
    for key, value in sorted(env_vars.items()):
        if mask_sensitive and any(sensitive in key.upper() for sensitive in sensitive_keys):
            masked_value = '*' * min(len(value), 8) if value else '(empty)'
            print(f"  {key}={masked_value}")
        else:
            print(f"  {key}={value}")

if __name__ == "__main__":
    # 환경변수 로드
    if load_env_variables():
        print_loaded_env_vars()
    else:
        print("환경변수 로드에 실패했습니다.")