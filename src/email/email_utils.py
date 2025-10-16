#!/usr/bin/env python3

"""
회의록 이메일 발송 유틸리티
"""

import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
import mimetypes

def extract_sender_from_filename(audio_file_path):
    """
    오디오 파일명에서 발신자 정보 추출
    예: "김철수_1013_도공회의.m4a" -> "김철수"
    """
    try:
        filename = os.path.splitext(os.path.basename(audio_file_path))[0]
        
        # 잘못된 패턴 미리 정의
        import re
        invalid_patterns = ['회의록', '회의', '미팅', 'meeting', 'call', 'record', 'audio']
        
        # 패턴 1: 이름_날짜_제목 (예: 김철수_1013_도공회의)
        if '_' in filename:
            parts = filename.split('_')
            potential_name = parts[0]
            
            # 잘못된 패턴 먼저 필터링
            if potential_name.lower() in invalid_patterns:
                pass  # 다음 패턴으로 넘어가기
            # 한글 이름 패턴 확인 (2-4자 한글)
            elif re.match(r'^[가-힣]{2,4}$', potential_name):
                return potential_name
            # 영문 이름 패턴 확인 (대소문자 혼합, 2-10자)
            elif re.match(r'^[A-Za-z]{2,10}$', potential_name):
                return potential_name
        
        # 패턴 2: 날짜로 시작하는 경우 (예: 1013_김철수_도공회의)
        if filename[0].isdigit() and '_' in filename:
            parts = filename.split('_')
            if len(parts) >= 2:
                potential_name = parts[1]
                
                # 잘못된 패턴 먼저 필터링
                if potential_name.lower() in invalid_patterns:
                    return None
                # 한글 이름 패턴 확인
                elif re.match(r'^[가-힣]{2,4}$', potential_name):
                    return potential_name
                # 영문 이름 패턴 확인
                elif re.match(r'^[A-Za-z]{2,10}$', potential_name):
                    return potential_name
        
        return None
        
    except Exception as e:
        print(f"⚠️ 파일명에서 발신자 추출 실패: {e}")
        return None

def get_sender_email_from_name(sender_name, email_mapping=None):
    """
    발신자 이름으로부터 이메일 주소 매핑
    """
    # 기본 이메일 매핑 (환경변수나 설정파일에서 로드 가능)
    default_mapping = {
        "김철수": "kim.cheolsu@company.com",
        "이영희": "lee.younghee@company.com", 
        "박민수": "park.minsu@company.com",
        "정수진": "jung.sujin@company.com",
    }
    
    # 환경변수에서 이메일 매핑 로드
    env_mapping = os.environ.get('EMAIL_NAME_MAPPING')
    if env_mapping:
        try:
            import json
            env_mapping_dict = json.loads(env_mapping)
            default_mapping.update(env_mapping_dict)
        except:
            pass
    
    # 사용자 제공 매핑 우선 사용
    if email_mapping:
        default_mapping.update(email_mapping)
    
    return default_mapping.get(sender_name)

def send_meeting_minutes_email(
    meeting_minutes_path,
    stt_result_path,
    recipient_emails,
    meeting_title="회의록",
    smtp_server="smtp.gmail.com",
    smtp_port=587,
    sender_email=None,
    sender_password=None,
    audio_file_path=None,
    auto_reply_to_sender=True
):
    """
    회의록을 이메일로 발송
    
    Args:
        meeting_minutes_path: 회의록 파일 경로 (TXT/DOCX)
        stt_result_path: STT 전사 결과 파일 경로
        recipient_emails: 수신자 이메일 리스트
        meeting_title: 회의 제목
        smtp_server: SMTP 서버 주소
        smtp_port: SMTP 포트
        sender_email: 발신자 이메일
        sender_password: 발신자 이메일 비밀번호
        audio_file_path: 원본 오디오 파일 경로 (발신자 추출용)
        auto_reply_to_sender: 원본 발신자에게도 회신할지 여부
    """
    
    # 오디오 파일에서 발신자 정보 추출
    original_sender_name = None
    original_sender_email = None
    
    if audio_file_path and auto_reply_to_sender:
        print("🔍 오디오 파일에서 발신자 정보 추출 중...")
        original_sender_name = extract_sender_from_filename(audio_file_path)
        
        if original_sender_name:
            print(f"📝 추출된 발신자 이름: {original_sender_name}")
            original_sender_email = get_sender_email_from_name(original_sender_name)
            
            if original_sender_email:
                print(f"📧 발신자 이메일: {original_sender_email}")
                # 기존 수신자 목록에 발신자 추가 (중복 제거)
                if original_sender_email not in recipient_emails:
                    recipient_emails.append(original_sender_email)
                    print(f"✅ 발신자를 수신자 목록에 추가: {original_sender_email}")
            else:
                print(f"⚠️ 발신자 '{original_sender_name}'의 이메일 매핑을 찾을 수 없습니다.")
                print("💡 setup_email_env.py에서 이름-이메일 매핑을 설정하세요.")
        else:
            print("⚠️ 파일명에서 발신자 이름을 추출할 수 없습니다.")
            print("💡 파일명 형식: '이름_날짜_제목.확장자' (예: 김철수_1013_도공회의.m4a)")
    
    # 환경변수에서 이메일 설정 읽기
    if not sender_email:
        sender_email = os.environ.get('SENDER_EMAIL', 'babel.ai.dub@gmail.com')
    if not sender_password:
        sender_password = os.environ.get('SENDER_PASSWORD')
    
    if not sender_email or not sender_password:
        raise ValueError("발신자 이메일 정보가 없습니다. 환경변수 SENDER_EMAIL, SENDER_PASSWORD를 설정하세요.")
    
    # 이메일 메시지 생성
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = ", ".join(recipient_emails)
    msg['Subject'] = f"[자동발송] {meeting_title} - {datetime.now().strftime('%Y.%m.%d')}"
    
    # 이메일 본문 (발신자 정보 포함)
    sender_info = ""
    if original_sender_name:
        if original_sender_email:
            sender_info = f"🎤 원본 제공자: {original_sender_name} ({original_sender_email})\n"
        else:
            sender_info = f"🎤 원본 제공자: {original_sender_name}\n"
    
    body = f"""
안녕하세요,

AI 음성인식 시스템에서 자동으로 생성된 회의록을 발송드립니다.

📋 회의명: {meeting_title}
📅 작성일시: {datetime.now().strftime('%Y년 %m월 %d일 %H:%M')}
🤖 생성 방식: AI 음성인식 + 자동 분석
{sender_info}
첨부파일:
• 회의록: {os.path.basename(meeting_minutes_path)}
• 전사 결과: {os.path.basename(stt_result_path)}

※ 이 메일은 자동으로 발송되었습니다.
※ 문의사항이 있으시면 담당자에게 연락해 주세요.

감사합니다.
    """
    
    msg.attach(MIMEText(body, 'plain', 'utf-8'))
    
    # 회의록 파일 첨부
    if os.path.exists(meeting_minutes_path):
        attach_file(msg, meeting_minutes_path)
    
    # STT 전사 결과 파일 첨부
    if os.path.exists(stt_result_path):
        attach_file(msg, stt_result_path)
    
    # 이메일 발송
    try:
        print(f"📧 이메일 발송 중... ({len(recipient_emails)}명)")
        
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()  # TLS 암호화 시작
        server.login(sender_email, sender_password)
        
        text = msg.as_string()
        server.sendmail(sender_email, recipient_emails, text)
        server.quit()
        
        print(f"✅ 이메일 발송 완료!")
        print(f"   수신자: {', '.join(recipient_emails)}")
        return True
        
    except Exception as e:
        print(f"❌ 이메일 발송 실패: {str(e)}")
        return False

def attach_file(msg, file_path):
    """파일을 이메일에 첨부"""
    try:
        # 파일 타입 추정
        content_type, encoding = mimetypes.guess_type(file_path)
        if content_type is None or encoding is not None:
            content_type = 'application/octet-stream'
        
        main_type, sub_type = content_type.split('/', 1)
        
        with open(file_path, 'rb') as file:
            attachment = MIMEBase(main_type, sub_type)
            attachment.set_payload(file.read())
            encoders.encode_base64(attachment)
            attachment.add_header(
                'Content-Disposition',
                f'attachment; filename="{os.path.basename(file_path)}"'
            )
            msg.attach(attachment)
        
        print(f"📎 파일 첨부: {os.path.basename(file_path)}")
        
    except Exception as e:
        print(f"⚠️ 파일 첨부 실패 ({os.path.basename(file_path)}): {str(e)}")

def setup_email_config():
    """이메일 설정 대화형 입력"""
    print("📧 이메일 발송 설정")
    print("=" * 40)
    
    # 발신자 이메일
    sender_email = input("발신자 이메일: ").strip()
    if not sender_email:
        print("❌ 발신자 이메일이 필요합니다.")
        return None, None, None
    
    # 발신자 비밀번호 (Gmail의 경우 앱 비밀번호 사용)
    import getpass
    sender_password = getpass.getpass("발신자 이메일 비밀번호 (Gmail 앱 비밀번호): ")
    if not sender_password:
        print("❌ 비밀번호가 필요합니다.")
        return None, None, None
    
    # 수신자 이메일
    print("\n수신자 이메일 주소를 입력하세요 (여러 개인 경우 쉼표로 구분):")
    recipients_input = input("수신자: ").strip()
    if not recipients_input:
        print("❌ 수신자 이메일이 필요합니다.")
        return None, None, None
    
    recipient_emails = [email.strip() for email in recipients_input.split(',')]
    
    print(f"\n✅ 설정 완료:")
    print(f"   발신자: {sender_email}")
    print(f"   수신자: {', '.join(recipient_emails)}")
    
    return sender_email, sender_password, recipient_emails

def test_email_sending():
    """이메일 발송 테스트"""
    print("🧪 이메일 발송 테스트")
    
    # 설정 입력
    sender_email, sender_password, recipient_emails = setup_email_config()
    if not sender_email:
        return
    
    # 테스트 파일 생성
    test_file_path = "/tmp/test_meeting_minutes.txt"
    with open(test_file_path, 'w', encoding='utf-8') as f:
        f.write("테스트 회의록\n")
        f.write("=" * 20 + "\n")
        f.write(f"생성일시: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write("내용: 이메일 발송 테스트입니다.\n")
    
    # 이메일 발송 테스트
    success = send_meeting_minutes_email(
        meeting_minutes_path=test_file_path,
        stt_result_path=test_file_path,  # 동일 파일 사용
        recipient_emails=recipient_emails,
        meeting_title="이메일 발송 테스트",
        sender_email=sender_email,
        sender_password=sender_password
    )
    
    # 테스트 파일 삭제
    os.remove(test_file_path)
    
    if success:
        print("✅ 이메일 발송 테스트 성공!")
    else:
        print("❌ 이메일 발송 테스트 실패!")

if __name__ == "__main__":
    test_email_sending()