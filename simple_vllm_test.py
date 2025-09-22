#!/usr/bin/env python3
"""
간단한 vLLM 테스트 - 설치 확인
"""

try:
    print("🔍 vLLM 모듈 테스트 시작...")
    
    # 기본 임포트 테스트
    print("1. 기본 임포트...")
    import torch
    print(f"   PyTorch: {torch.__version__}")
    print(f"   CUDA 가능: {torch.cuda.is_available()}")
    print(f"   GPU 수: {torch.cuda.device_count()}")
    
    # vLLM 임포트 테스트
    print("2. vLLM 임포트...")
    try:
        from vllm import LLM, SamplingParams
        print("   ✅ vLLM 임포트 성공")
    except Exception as e:
        print(f"   ❌ vLLM 임포트 실패: {e}")
        exit(1)
    
    # 간단한 모델 테스트 (작은 모델)
    print("3. 작은 모델 로딩 테스트...")
    try:
        llm = LLM(
            model="microsoft/DialoGPT-small",
            tensor_parallel_size=1,  # 단일 GPU로 테스트
            gpu_memory_utilization=0.3,
            max_model_len=512
        )
        print("   ✅ 모델 로딩 성공")
        
        # 간단한 생성 테스트
        sampling_params = SamplingParams(temperature=0.8, top_p=0.95, max_tokens=50)
        outputs = llm.generate(["Hello, how are you?"], sampling_params)
        
        for output in outputs:
            generated_text = output.outputs[0].text
            print(f"   📝 생성 텍스트: {generated_text}")
            
        print("   ✅ 텍스트 생성 성공")
        
    except Exception as e:
        print(f"   ❌ 모델 테스트 실패: {e}")
        import traceback
        print(f"   🔍 상세 오류: {traceback.format_exc()}")
    
    print("\n🎉 vLLM 기본 테스트 완료!")
    
except Exception as e:
    print(f"❌ 전체 테스트 실패: {e}")
    import traceback
    print(f"🔍 상세 오류: {traceback.format_exc()}")