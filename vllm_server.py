#!/usr/bin/env python3
"""
vLLM 서버 - 듀얼 RTX 3090을 활용한 32B 모델 실행
텐서 병렬처리로 2개 GPU에 모델을 분산 처리
"""

import os
import asyncio
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from vllm import LLM, SamplingParams
from vllm.engine.arg_utils import AsyncEngineArgs
from vllm.engine.async_llm_engine import AsyncLLMEngine
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Ex-GPT STT vLLM Server")

class ChatRequest(BaseModel):
    messages: list
    max_tokens: int = 1024
    temperature: float = 0.1
    top_p: float = 0.7

class ChatResponse(BaseModel):
    response: str

# 전역 변수
engine = None

async def initialize_engine():
    """vLLM 엔진 초기화 - 듀얼 GPU 설정"""
    global engine
    
    try:
        logger.info("🚀 vLLM 엔진 초기화 시작...")
        logger.info("📊 GPU 정보: 2x RTX 3090 (48GB 총 VRAM)")
        
        # vLLM 엔진 설정 - 더 작은 모델로 테스트
        engine_args = AsyncEngineArgs(
            model="Qwen/Qwen2.5-14B-Instruct",  # 14B 모델로 변경
            # 듀얼 GPU 텐서 병렬처리
            tensor_parallel_size=2,
            # GPU 메모리 활용 최적화
            max_model_len=4096,  # 컨텍스트 길이 조정
            gpu_memory_utilization=0.85,  # 85% 메모리 활용
            # 데이터 타입 최적화
            dtype="float16",  # 메모리 절약
            # 기타 최적화 설정
            trust_remote_code=True,
            max_num_seqs=4,  # 배치 크기 줄임
            swap_space=2,  # 스왑 공간 (GB)
        )
        
        engine = AsyncLLMEngine.from_engine_args(engine_args)
        logger.info("✅ vLLM 엔진 초기화 완료!")
        
    except Exception as e:
        logger.error(f"❌ vLLM 엔진 초기화 실패: {e}")
        raise

@app.on_event("startup")
async def startup_event():
    """서버 시작 시 엔진 초기화"""
    await initialize_engine()

@app.post("/v1/chat/completions", response_model=ChatResponse)
async def chat_completion(request: ChatRequest):
    """OpenAI 호환 채팅 완성 API"""
    try:
        if not engine:
            raise HTTPException(status_code=500, detail="Engine not initialized")
        
        # 메시지를 프롬프트로 변환
        if request.messages:
            last_message = request.messages[-1]
            if isinstance(last_message, dict) and 'content' in last_message:
                prompt = last_message['content']
            else:
                prompt = str(last_message)
        else:
            raise HTTPException(status_code=400, detail="No messages provided")
        
        # 샘플링 파라미터 설정
        sampling_params = SamplingParams(
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            top_p=request.top_p,
            stop=["<|endoftext|>", "<|im_end|>"]
        )
        
        logger.info(f"🔄 추론 시작: {len(prompt)} 문자")
        
        # 추론 실행
        results = await engine.generate(prompt, sampling_params)
        
        if results and len(results) > 0:
            generated_text = results[0].outputs[0].text.strip()
            logger.info(f"✅ 추론 완료: {len(generated_text)} 문자 생성")
            
            return ChatResponse(response=generated_text)
        else:
            raise HTTPException(status_code=500, detail="No response generated")
            
    except Exception as e:
        logger.error(f"❌ 추론 실패: {e}")
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")

@app.get("/health")
async def health_check():
    """서버 상태 확인"""
    return {
        "status": "healthy",
        "engine_initialized": engine is not None,
        "gpu_count": 2,
        "model": "Qwen2.5-32B-Instruct"
    }

@app.get("/gpu-status")
async def gpu_status():
    """GPU 상태 정보"""
    try:
        import torch
        if torch.cuda.is_available():
            gpu_info = []
            for i in range(torch.cuda.device_count()):
                gpu_info.append({
                    "gpu": i,
                    "name": torch.cuda.get_device_name(i),
                    "memory_allocated": f"{torch.cuda.memory_allocated(i) / 1024**3:.2f} GB",
                    "memory_reserved": f"{torch.cuda.memory_reserved(i) / 1024**3:.2f} GB",
                    "memory_total": f"{torch.cuda.get_device_properties(i).total_memory / 1024**3:.2f} GB"
                })
            return {"gpu_info": gpu_info}
        else:
            return {"error": "CUDA not available"}
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    
    print("🚀 Ex-GPT STT vLLM 서버 시작")
    print("🔧 설정: Qwen2.5-32B + 듀얼 RTX 3090")
    print("🌐 서버 주소: http://localhost:8000")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )