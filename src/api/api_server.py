#!/usr/bin/env python3

"""
한국도로공사 모바일 오피스 STT API 서버
모바일에서 녹음 → 전송 → STT 처리 → 회의록 생성 → 이메일 발송
"""

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr
from typing import Optional, List
import os
import tempfile
import shutil
import uuid
from datetime import datetime
import logging
import asyncio
from pathlib import Path

# 환경변수 로드
try:
    from src.utils.load_env import load_env_variables
    load_env_variables()
except ImportError:
    print("⚠️ load_env 모듈을 찾을 수 없습니다.")

# 로컬 모듈 임포트
try:
    # app.py에서 필요한 함수들 직접 import
    from src.stt.app import transcribe_audio_for_api, analyze_meeting_with_ai, analyze_with_ollama
    from src.email.email_utils import send_meeting_minutes_email, extract_sender_from_filename, get_sender_email_from_name
    STT_AVAILABLE = True
    print("✅ app.py 메인 함수들을 성공적으로 import")
except ImportError as e:
    print(f"⚠️ STT 모듈 로드 실패: {e}")
    STT_AVAILABLE = False

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="한국도로공사 모바일 오피스 STT API",
    description="모바일에서 녹음된 음성을 STT 처리하여 회의록을 생성하고 이메일로 발송",
    version="1.0.0"
)

# CORS 설정 (모바일 오피스 접근 허용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 개발시 모든 도메인 허용, 운영시 한국도로공사 도메인만 허용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 업로드 디렉토리 설정
UPLOAD_DIR = Path("/tmp/mobile_office_uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# 요청/응답 모델
class STTRequest(BaseModel):
    sender_name: Optional[str] = None  # 발신자 이름
    sender_email: Optional[str] = None  # 발신자 이메일
    recipient_emails: Optional[List[str]] = None  # 수신자 이메일 목록
    meeting_title: Optional[str] = None  # 회의 제목
    department: Optional[str] = None  # 부서명
    auto_send_email: bool = True  # 자동 이메일 발송 여부

class STTResponse(BaseModel):
    success: bool
    task_id: str
    message: str
    processing_status: str = "queued"  # queued, processing, completed, failed

class STTResult(BaseModel):
    task_id: str
    success: bool
    status: str  # completed, failed, processing
    transcription: Optional[str] = None
    meeting_minutes: Optional[str] = None
    duration: Optional[float] = None
    language: Optional[str] = None
    email_sent: bool = False
    error_message: Optional[str] = None

# 작업 상태 저장 (실제 운영시에는 Redis나 DB 사용)
task_status = {}

@app.get("/")
async def root():
    """API 상태 확인"""
    return {
        "service": "한국도로공사 모바일 오피스 STT API",
        "status": "running",
        "stt_available": STT_AVAILABLE,
        "admin_dashboard": "/admin",
        "api_docs": "/docs",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/admin")
async def admin_dashboard():
    """관리자 대시보드 페이지"""
    dashboard_path = Path(__file__).parent.parent.parent / "web" / "admin_dashboard.html"
    if dashboard_path.exists():
        return FileResponse(dashboard_path, media_type="text/html")
    else:
        raise HTTPException(status_code=404, detail="관리자 대시보드를 찾을 수 없습니다")

@app.get("/health")
async def health_check():
    """헬스체크 엔드포인트"""
    return {
        "status": "healthy",
        "stt_engine": "available" if STT_AVAILABLE else "unavailable",
        "timestamp": datetime.now().isoformat()
    }

@app.post("/api/v1/stt/upload", response_model=STTResponse)
async def upload_audio_for_stt(
    background_tasks: BackgroundTasks,
    audio_file: UploadFile = File(..., description="음성 파일 (m4a, wav, mp3, flac)"),
    sender_name: Optional[str] = Form(None, description="발신자 이름"),
    sender_email: Optional[str] = Form(None, description="발신자 이메일"),
    recipient_emails: Optional[str] = Form(None, description="수신자 이메일 (쉼표로 구분)"),
    meeting_title: Optional[str] = Form(None, description="회의 제목"),
    department: Optional[str] = Form(None, description="부서명"),
    auto_send_email: bool = Form(True, description="자동 이메일 발송")
):
    """
    모바일 오피스에서 녹음된 음성 파일을 업로드하여 STT 처리 요청
    """
    try:
        # STT 엔진 사용 가능 확인
        if not STT_AVAILABLE:
            raise HTTPException(status_code=503, detail="STT 엔진을 사용할 수 없습니다")
        
        # 파일 검증
        if not audio_file.filename:
            raise HTTPException(status_code=400, detail="파일명이 없습니다")
        
        # 지원하는 오디오 형식 확인
        supported_formats = ['.m4a', '.wav', '.mp3', '.flac', '.mp4']
        file_ext = Path(audio_file.filename).suffix.lower()
        if file_ext not in supported_formats:
            raise HTTPException(
                status_code=400, 
                detail=f"지원하지 않는 파일 형식입니다. 지원 형식: {supported_formats}"
            )
        
        # 고유 작업 ID 생성
        task_id = str(uuid.uuid4())
        
        # 임시 파일 저장
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_filename = f"{task_id}_{timestamp}_{audio_file.filename}"
        temp_file_path = UPLOAD_DIR / safe_filename
        
        # 파일 저장
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(audio_file.file, buffer)
        
        logger.info(f"파일 업로드 완료: {safe_filename}")
        
        # 수신자 이메일 파싱
        recipient_list = []
        if recipient_emails:
            recipient_list = [email.strip() for email in recipient_emails.split(',') if email.strip()]
        
        # 작업 상태 초기화
        task_status[task_id] = {
            "status": "queued",
            "progress_message": "업로드 완료, 처리 대기 중...",
            "progress_steps": [],
            "created_at": datetime.now(),
            "file_path": str(temp_file_path),
            "sender_name": sender_name,
            "sender_email": sender_email,
            "recipient_emails": recipient_list,
            "meeting_title": meeting_title or audio_file.filename,
            "department": department,
            "auto_send_email": auto_send_email
        }
        
        # 백그라운드에서 STT 처리 시작
        background_tasks.add_task(
            process_stt_task,
            task_id=task_id,
            file_path=temp_file_path,
            sender_name=sender_name,
            sender_email=sender_email,
            recipient_emails=recipient_list,
            meeting_title=meeting_title or audio_file.filename,
            department=department,
            auto_send_email=auto_send_email
        )
        
        return STTResponse(
            success=True,
            task_id=task_id,
            message="음성 파일이 성공적으로 업로드되었습니다. STT 처리가 시작됩니다.",
            processing_status="queued"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"파일 업로드 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"파일 업로드 실패: {str(e)}")

@app.get("/api/v1/stt/status/{task_id}")
async def get_stt_status(task_id: str):
    """
    STT 처리 상태 조회
    """
    if task_id not in task_status:
        raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다")
    
    task = task_status[task_id]
    
    # 기본 응답 데이터
    response_data = {
        "task_id": task_id,
        "success": task["status"] == "completed",
        "status": task["status"],
        "transcription": task.get("transcription"),
        "meeting_minutes": task.get("meeting_minutes"),
        "duration": task.get("duration"),
        "language": task.get("language"),
        "email_sent": task.get("email_sent", False),
        "error_message": task.get("error_message"),
        "transcription_file": task.get("transcription_file"),
        "minutes_file": task.get("minutes_file")
    }
    
    # 진행 상황 정보 추가 (처리 중일 때)
    if task["status"] in ["processing", "queued"]:
        response_data.update({
            "progress_message": task.get("progress_message"),
            "progress_steps": task.get("progress_steps", []),
            "transcription_log": task.get("transcription_log", [])
        })
    
    # 전사 로그는 완료된 후에도 제공 (디버깅용)
    if task.get("transcription_log"):
        response_data["transcription_log"] = task.get("transcription_log", [])
    
    # 다운로드 관련 정보 추가 (완료된 작업만)
    if task["status"] == "completed":
        response_data.update({
            "download_urls": {
                "transcription": f"/api/v1/download/{task_id}/transcription",
                "minutes": f"/api/v1/download/{task_id}/minutes"
            },
            "files_ready": {
                "transcription": bool(task.get("transcription_file") and os.path.exists(task.get("transcription_file", ""))),
                "minutes": bool(task.get("minutes_file") and os.path.exists(task.get("minutes_file", "")))
            }
        })
    
    return response_data

@app.get("/api/v1/stt/tasks")
async def list_recent_tasks(limit: int = 10):
    """
    최근 작업 목록 조회 (관리용)
    """
    recent_tasks = []
    for task_id, task in list(task_status.items())[-limit:]:
        recent_tasks.append({
            "task_id": task_id,
            "status": task["status"],
            "created_at": task["created_at"].isoformat(),
            "meeting_title": task.get("meeting_title"),
            "sender_name": task.get("sender_name"),
            "department": task.get("department")
        })
    
    return {"tasks": recent_tasks}

@app.get("/api/v1/admin/dashboard")
async def get_admin_dashboard():
    """
    관리자 대시보드 통계 데이터
    """
    total_tasks = len(task_status)
    
    # 상태별 통계
    status_counts = {"queued": 0, "processing": 0, "completed": 0, "failed": 0}
    recent_24h = []
    
    from datetime import datetime, timedelta
    yesterday = datetime.now() - timedelta(days=1)
    
    for task_id, task in task_status.items():
        # 상태별 카운트
        status_counts[task.get("status", "unknown")] = status_counts.get(task.get("status", "unknown"), 0) + 1
        
        # 최근 24시간 작업
        if task["created_at"] >= yesterday:
            recent_24h.append({
                "task_id": task_id,
                "status": task.get("status"),
                "created_at": task["created_at"].isoformat(),
                "meeting_title": task.get("meeting_title"),
                "sender_name": task.get("sender_name"),
                "department": task.get("department"),
                "duration": task.get("duration"),
                "email_sent": task.get("email_sent", False),
                "file_path": task.get("file_path", "").split("/")[-1] if task.get("file_path") else None
            })
    
    # 부서별 통계
    department_stats = {}
    for task in task_status.values():
        dept = task.get("department", "미분류")
        if dept not in department_stats:
            department_stats[dept] = 0
        department_stats[dept] += 1
    
    return {
        "total_tasks": total_tasks,
        "status_counts": status_counts,
        "recent_24h_tasks": sorted(recent_24h, key=lambda x: x["created_at"], reverse=True),
        "department_stats": department_stats,
        "success_rate": round((status_counts["completed"] / max(total_tasks, 1)) * 100, 1),
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/v1/admin/tasks/detailed")
async def get_detailed_tasks(
    limit: int = 50,
    status: str = None,
    department: str = None,
    sender: str = None
):
    """
    상세 작업 목록 조회 (필터링 지원)
    """
    filtered_tasks = []
    
    for task_id, task in task_status.items():
        # 필터 적용
        if status and task.get("status") != status:
            continue
        if department and task.get("department") != department:
            continue
        if sender and sender.lower() not in task.get("sender_name", "").lower():
            continue
        
        task_detail = {
            "task_id": task_id,
            "status": task.get("status"),
            "created_at": task["created_at"].isoformat(),
            "updated_at": task.get("updated_at", task["created_at"]).isoformat(),
            "meeting_title": task.get("meeting_title"),
            "sender_name": task.get("sender_name"),
            "sender_email": task.get("sender_email"),
            "recipient_emails": task.get("recipient_emails", []),
            "department": task.get("department"),
            "duration": task.get("duration"),
            "language": task.get("language"),
            "transcription_length": len(task.get("transcription", "")),
            "meeting_minutes_length": len(task.get("meeting_minutes", "")),
            "email_sent": task.get("email_sent", False),
            "error_message": task.get("error_message"),
            "file_name": task.get("file_path", "").split("/")[-1] if task.get("file_path") else None
        }
        filtered_tasks.append(task_detail)
    
    # 최신순 정렬
    filtered_tasks.sort(key=lambda x: x["created_at"], reverse=True)
    
    return {
        "tasks": filtered_tasks[:limit],
        "total_filtered": len(filtered_tasks),
        "filters_applied": {
            "status": status,
            "department": department,
            "sender": sender,
            "limit": limit
        }
    }

@app.get("/api/v1/admin/task/{task_id}/details")
async def get_task_details(task_id: str):
    """
    특정 작업의 상세 정보 조회
    """
    if task_id not in task_status:
        raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다")
    
    task = task_status[task_id]
    
    return {
        "task_id": task_id,
        "status": task.get("status"),
        "created_at": task["created_at"].isoformat(),
        "updated_at": task.get("updated_at", task["created_at"]).isoformat(),
        "meeting_title": task.get("meeting_title"),
        "sender_name": task.get("sender_name"),
        "sender_email": task.get("sender_email"),
        "recipient_emails": task.get("recipient_emails", []),
        "department": task.get("department"),
        "auto_send_email": task.get("auto_send_email"),
        "file_path": task.get("file_path"),
        "stt_file": task.get("stt_file"),
        "minutes_file": task.get("minutes_file"),
        "duration": task.get("duration"),
        "language": task.get("language"),
        "transcription": task.get("transcription"),
        "meeting_minutes": task.get("meeting_minutes"),
        "email_sent": task.get("email_sent", False),
        "error_message": task.get("error_message"),
        "processing_logs": []  # 향후 로그 추가 가능
    }

async def process_stt_task(
    task_id: str,
    file_path: Path,
    sender_name: Optional[str],
    sender_email: Optional[str], 
    recipient_emails: List[str],
    meeting_title: str,
    department: Optional[str],
    auto_send_email: bool
):
    """
    STT 처리 백그라운드 작업
    """
    try:
        logger.info(f"STT 처리 시작: {task_id}")
        task_status[task_id]["status"] = "processing"
        task_status[task_id]["progress_message"] = "STT 모델 초기화 중..."
        task_status[task_id]["updated_at"] = datetime.now()
        
        # 진행 단계 추가 함수
        def add_progress_step(message):
            task_status[task_id]["progress_message"] = message
            task_status[task_id]["progress_steps"].append({
                "message": message,
                "timestamp": datetime.now().strftime("%H:%M:%S")
            })
            
            # 실시간 전사 메시지는 별도로 저장
            if "💬" in message:
                if "transcription_log" not in task_status[task_id]:
                    task_status[task_id]["transcription_log"] = []
                # 💬 제거하고 전사 텍스트만 저장
                clean_message = message.replace("💬", "").strip()
                task_status[task_id]["transcription_log"].append(clean_message)
            
            logger.info(f"[{task_id}] {message}")
        
        # STT 처리 실행 (진행 상황 콜백 포함)
        result = await run_stt_processing(
            audio_file_path=str(file_path),
            meeting_title=meeting_title,
            sender_name=sender_name,
            task_id=task_id,
            progress_callback=add_progress_step
        )
        
        if result["success"]:
            # STT 성공
            task_status[task_id].update({
                "status": "completed",
                "transcription": result["transcription"],
                "meeting_minutes": result["meeting_minutes"],
                "duration": result.get("duration"),
                "language": result.get("language"),
                "transcription_file": result.get("transcription_file"),
                "minutes_file": result.get("minutes_file"),
                "transcription_length": len(result.get("transcription", "")),
                "meeting_minutes_length": len(result.get("meeting_minutes", ""))
            })
            
            # 이메일 발송
            if auto_send_email and (recipient_emails or sender_email):
                email_result = await send_email_notification(
                    task_id=task_id,
                    sender_name=sender_name,
                    sender_email=sender_email,
                    recipient_emails=recipient_emails,
                    meeting_title=meeting_title,
                    department=department,
                    transcription_file=result.get("transcription_file"),
                    minutes_file=result.get("minutes_file"),
                    audio_file_path=str(file_path)
                )
                task_status[task_id]["email_sent"] = email_result
            
            logger.info(f"STT 처리 완료: {task_id}")
            
        else:
            # STT 실패
            task_status[task_id].update({
                "status": "failed",
                "error_message": result.get("error", "STT 처리 중 오류 발생")
            })
            logger.error(f"STT 처리 실패: {task_id} - {result.get('error')}")
            
    except Exception as e:
        logger.error(f"STT 작업 처리 중 예외 발생: {task_id} - {str(e)}")
        task_status[task_id].update({
            "status": "failed",
            "error_message": str(e)
        })
    
    finally:
        # 원본 파일 정리 (선택사항)
        try:
            if file_path.exists():
                file_path.unlink()
                logger.info(f"임시 파일 삭제: {file_path}")
        except Exception as e:
            logger.warning(f"임시 파일 삭제 실패: {e}")

async def run_stt_processing(
    audio_file_path: str,
    meeting_title: str = None,
    sender_name: str = None,
    task_id: str = None,
    progress_callback = None
):
    """
    STT 처리 실행 - app.py의 transcribe_audio_for_api 직접 호출
    """
    try:
        # 진행 상황 콜백 함수
        def progress_callback_internal(message):
            if task_id and progress_callback:
                progress_callback(message)
                # 💬 메시지인 경우 즉시 task_status 업데이트
                if "💬" in message and task_id:
                    if "transcription_log" not in task_status[task_id]:
                        task_status[task_id]["transcription_log"] = []
                    clean_message = message.replace("💬", "").strip()
                    task_status[task_id]["transcription_log"].append(clean_message)
            else:
                logger.info(f"[{task_id}] {message}")
        
        # app.py의 transcribe_audio_for_api 함수 직접 호출
        loop = asyncio.get_event_loop()
        
        def run_transcription():
            return transcribe_audio_for_api(audio_file_path, progress_callback_internal)
        
        # 비동기로 실행
        result = await loop.run_in_executor(None, run_transcription)
        
        if result["success"]:
            logger.info(f"[{task_id}] 고급 STT 처리 완료!")
            logger.info(f"[{task_id}] - 전사 파일: {result.get('transcription_file')}")
            logger.info(f"[{task_id}] - 회의록 파일: {result.get('minutes_file')}")
            logger.info(f"[{task_id}] - 화자 분리: {result.get('diarization_success', False)}")
            logger.info(f"[{task_id}] - AI 분석: {result.get('ai_analysis_success', False)}")
            
            return {
                "success": True,
                "transcription": result.get("transcription_text", ""),
                "meeting_minutes": result.get("minutes_text", ""),
                "transcription_file": result.get("transcription_file"),
                "minutes_file": result.get("minutes_file"),
                "duration": result.get("duration", 0),
                "language": result.get("language", "ko")
            }
        else:
            logger.error(f"[{task_id}] STT 처리 실패: {result.get('error')}")
            return result
        
    except Exception as e:
        logger.error(f"[{task_id}] STT 처리 중 예외: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

async def send_email_notification(
    task_id: str,
    sender_name: Optional[str],
    sender_email: Optional[str],
    recipient_emails: List[str],
    meeting_title: str,
    department: Optional[str],
    transcription_file: Optional[str],
    minutes_file: Optional[str],
    audio_file_path: str
) -> bool:
    """
    이메일 발송
    """
    try:
        # 수신자 목록 준비
        all_recipients = recipient_emails.copy() if recipient_emails else []
        
        # 발신자 자동 감지 (파일명에서)
        if not sender_email and sender_name:
            detected_email = get_sender_email_from_name(sender_name)
            if detected_email:
                sender_email = detected_email
        
        # 발신자를 수신자에 추가
        if sender_email and sender_email not in all_recipients:
            all_recipients.append(sender_email)
        
        if not all_recipients:
            logger.warning(f"수신자가 없어 이메일 발송 건너뜀: {task_id}")
            return False
        
        # 이메일 발송
        if transcription_file and minutes_file:
            success = send_meeting_minutes_email(
                meeting_minutes_path=minutes_file,
                stt_result_path=transcription_file,
                recipient_emails=all_recipients,
                meeting_title=f"[모바일오피스] {meeting_title}",
                audio_file_path=audio_file_path,
                auto_reply_to_sender=True
            )
            
            if success:
                logger.info(f"이메일 발송 성공: {task_id} → {len(all_recipients)}명")
                return True
            else:
                logger.error(f"이메일 발송 실패: {task_id}")
                return False
        else:
            logger.warning(f"첨부 파일이 없어 이메일 발송 불가: {task_id}")
            return False
            
    except Exception as e:
        logger.error(f"이메일 발송 중 오류: {task_id} - {str(e)}")
        return False

@app.get("/api/v1/download/{task_id}/{file_type}")
async def download_file(task_id: str, file_type: str):
    """
    STT 결과 파일 다운로드
    file_type: 'transcription' 또는 'minutes'
    """
    if task_id not in task_status:
        raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다")
    
    task = task_status[task_id]
    
    if task["status"] != "completed":
        raise HTTPException(status_code=400, detail="작업이 아직 완료되지 않았습니다")
    
    # 파일 경로 결정
    if file_type == "transcription":
        file_path = task.get("transcription_file")
        filename = f"{task_id}_전사결과.txt"
    elif file_type == "minutes":
        file_path = task.get("minutes_file")
        filename = f"{task_id}_회의록.txt"
    else:
        raise HTTPException(status_code=400, detail="유효하지 않은 파일 타입입니다")
    
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다")
    
    # 파일명을 더 명확하게 설정
    if file_type == "transcription":
        display_filename = f"전사결과_{task.get('meeting_title', task_id)[:20]}.txt"
    else:
        display_filename = f"회의록_{task.get('meeting_title', task_id)[:20]}.txt"
    
    # 파일명에서 특수문자 제거
    safe_filename = "".join(c for c in display_filename if c.isalnum() or c in "._-")
    
    response = FileResponse(
        path=file_path,
        filename=safe_filename,
        media_type="text/plain; charset=utf-8"
    )
    
    # CORS 및 다운로드 최적화 헤더 추가
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Expose-Headers"] = "Content-Disposition"
    response.headers["Content-Disposition"] = f'attachment; filename="{safe_filename}"'
    response.headers["Cache-Control"] = "no-cache"
    
    return response

@app.get("/api/v1/download-url/{task_id}/{file_type}")
async def get_download_url(task_id: str, file_type: str):
    """
    다운로드 URL 생성 (프론트엔드에서 window.open() 사용)
    """
    if task_id not in task_status:
        raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다")
    
    task = task_status[task_id]
    
    if task["status"] != "completed":
        raise HTTPException(status_code=400, detail="작업이 아직 완료되지 않았습니다")
    
    # 파일 경로 확인
    if file_type == "transcription":
        file_path = task.get("transcription_file")
    elif file_type == "minutes":
        file_path = task.get("minutes_file")
    else:
        raise HTTPException(status_code=400, detail="유효하지 않은 파일 타입입니다")
    
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다")
    
    # 다운로드 URL 반환
    download_url = f"/api/v1/download/{task_id}/{file_type}"
    
    return {
        "success": True,
        "download_url": download_url,
        "file_type": file_type,
        "task_id": task_id,
        "meeting_title": task.get("meeting_title", ""),
        "file_size": os.path.getsize(file_path) if os.path.exists(file_path) else 0
    }

@app.post("/api/v1/test/fix_task_files/{task_id}")
async def fix_task_files_for_testing(task_id: str):
    """테스트용: 완료된 작업의 파일 경로를 수정"""
    if task_id not in task_status:
        raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다")
    
    # 가장 최근 파일들 찾기
    import glob
    txt_files = glob.glob(os.path.join("/home/babelai/projects/ex-gpt-stt-uv", f"*{task_id}*.txt"))
    
    transcription_file = None
    minutes_file = None
    
    for file_path in txt_files:
        if "전사결과" in os.path.basename(file_path):
            transcription_file = file_path
        elif "회의록" in os.path.basename(file_path):
            minutes_file = file_path
    
    # 파일 경로 업데이트
    if transcription_file and minutes_file:
        task_status[task_id]["transcription_file"] = transcription_file
        task_status[task_id]["minutes_file"] = minutes_file
        
        return {
            "success": True,
            "message": "파일 경로가 수정되었습니다",
            "transcription_file": transcription_file,
            "minutes_file": minutes_file
        }
    else:
        return {
            "success": False,
            "message": "파일을 찾을 수 없습니다",
            "found_files": txt_files
        }

if __name__ == "__main__":
    import uvicorn
    
    print("🚀 한국도로공사 모바일 오피스 STT API 서버 시작")
    print("📱 모바일에서 녹음 → API 업로드 → STT 처리 → 이메일 발송")
    print("🌐 API 문서: http://localhost:8080/docs")
    
    # 환경변수에서 설정 읽기
    host = os.environ.get("API_HOST", "0.0.0.0")
    port = int(os.environ.get("API_PORT", "8080"))
    
    uvicorn.run(
        "api_server:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    )