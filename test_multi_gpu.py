#!/usr/bin/env python3
"""
Multi-GPU 기능 테스트 스크립트
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import get_optimal_gpu_device, initialize_multi_gpu_whisper_model, show_system_info

def test_multi_gpu():
    """Multi-GPU 기능 테스트"""
    print("🧪 Multi-GPU 최적화 테스트")
    print("=" * 50)
    
    # 시스템 정보 표시
    show_system_info()
    
    print("\n🎯 GPU 선택 테스트")
    print("-" * 30)
    
    # GPU 선택 테스트
    selected_gpu, success = get_optimal_gpu_device()
    
    if success:
        print(f"✅ 최적 GPU 선택 성공: GPU {selected_gpu}")
        
        # Multi-GPU Whisper 모델 초기화 테스트 (실제 모델은 로드하지 않음)
        print(f"\n🚀 GPU {selected_gpu}에 대한 WhisperModel 초기화 시뮬레이션")
        print("(실제 모델 로드는 건너뜀)")
        
        try:
            import torch
            if torch.cuda.is_available():
                # GPU 메모리 현재 상태 확인
                memory_used = torch.cuda.memory_allocated(selected_gpu) / (1024**3)
                memory_total = torch.cuda.get_device_properties(selected_gpu).total_memory / (1024**3)
                usage_percent = (memory_used / memory_total) * 100 if memory_total > 0 else 0
                
                print(f"📊 GPU {selected_gpu} 메모리 상태:")
                print(f"   사용중: {memory_used:.1f}GB")
                print(f"   전체: {memory_total:.1f}GB") 
                print(f"   사용률: {usage_percent:.1f}%")
                print(f"   여유공간: {memory_total - memory_used:.1f}GB")
                
                # 모든 GPU 상태 표시
                gpu_count = torch.cuda.device_count()
                print(f"\n🎯 모든 GPU 상태 ({gpu_count}개):")
                for i in range(gpu_count):
                    gpu_name = torch.cuda.get_device_name(i)
                    gpu_memory_used = torch.cuda.memory_allocated(i) / (1024**3)
                    gpu_memory_total = torch.cuda.get_device_properties(i).total_memory / (1024**3)
                    gpu_usage_percent = (gpu_memory_used / gpu_memory_total) * 100 if gpu_memory_total > 0 else 0
                    
                    status = "🔥 선택됨" if i == selected_gpu else "💤 대기중"
                    print(f"   GPU {i}: {gpu_name} - {gpu_memory_used:.1f}GB/{gpu_memory_total:.1f}GB ({gpu_usage_percent:.1f}%) {status}")
                
        except ImportError:
            print("⚠️ PyTorch를 찾을 수 없습니다.")
            
    else:
        print("❌ GPU 선택 실패 - CPU 모드를 사용해야 합니다.")
    
    print("\n✅ Multi-GPU 테스트 완료!")

if __name__ == "__main__":
    try:
        test_multi_gpu()
    except KeyboardInterrupt:
        print("\n❌ 테스트 중단됨")
    except Exception as e:
        print(f"\n❌ 테스트 오류: {e}")
        import traceback
        traceback.print_exc()