#!/usr/bin/env python3

"""
Gmail SMTP 설정 스크립트 - babel.ai.dub@gmail.com 계정용
"""

import os
import getpass
from pathlib import Path

def setup_gmail_smtp():
    """Gmail SMTP 설정을 위한 환경변수 설정"""
    
    print("📧 Gmail SMTP 설정")
    print("=" * 50)
    print()
    
    print("🔐 Gmail 앱 비밀번호 설정이 필요합니다.")
    print()
    print("Gmail 앱 비밀번호 생성 방법:")
    print("1. Gmail 계정 설정 → 보안")
    print("2. 2단계 인증 활성화")
    print("3. '앱 비밀번호' 생성")
    print("4. 생성된 16자리 비밀번호 사용")
    print()
    
    # 발신자 이메일 확인
    sender_email = "babel.ai.dub@gmail.com"
    print(f"발신자 이메일: {sender_email}")
    
    # Gmail 앱 비밀번호 입력
    app_password = getpass.getpass("Gmail 앱 비밀번호 (16자리): ").strip()
    if not app_password:
        print("❌ 앱 비밀번호가 필요합니다.")
        return False
    
    # 환경변수 파일 생성
    env_file = Path.cwd() / ".env"
    
    # 기존 .env 파일 읽기
    env_content = ""
    if env_file.exists():
        with open(env_file, 'r', encoding='utf-8') as f:
            env_content = f.read()
    
    # 기존 SENDER_EMAIL, SENDER_PASSWORD 라인 제거
    lines = env_content.split('\n')
    filtered_lines = []
    for line in lines:
        if not (line.startswith('SENDER_EMAIL=') or line.startswith('SENDER_PASSWORD=')):
            filtered_lines.append(line)
    
    # 새로운 설정 추가
    filtered_lines.extend([
        f"SENDER_EMAIL={sender_email}",
        f"SENDER_PASSWORD={app_password}"
    ])
    
    # .env 파일 저장
    with open(env_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(filtered_lines))
    
    print(f"✅ 환경변수 설정 완료: {env_file}")
    print()
    
    # 테스트 이메일 발송 여부 확인
    test_choice = input("테스트 이메일을 발송하시겠습니까? (y/N): ").strip().lower()
    if test_choice in ['y', 'yes']:
        test_recipients = input("테스트 수신자 이메일 (쉼표로 구분): ").strip()
        if test_recipients:
            recipient_emails = [email.strip() for email in test_recipients.split(',')]
            send_test_email(sender_email, app_password, recipient_emails)
    
    return True

def send_test_email(sender_email, sender_password, recipient_emails):
    """테스트 이메일 발송"""
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from datetime import datetime
    
    try:
        print("📧 테스트 이메일 발송 중...")
        
        # 이메일 메시지 생성
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = ", ".join(recipient_emails)
        msg['Subject'] = f"[테스트] STT API 이메일 발송 테스트 - {datetime.now().strftime('%Y.%m.%d %H:%M')}"
        
        body = f"""
안녕하세요,

이것은 STT API 이메일 발송 시스템의 테스트 메일입니다.

📋 발신자: {sender_email}
📅 발송일시: {datetime.now().strftime('%Y년 %m월 %d일 %H시 %M분')}
🤖 시스템: AI 음성인식 + 자동 회의록 생성

이 메일을 받으셨다면 이메일 발송 설정이 정상적으로 완료된 것입니다.

감사합니다.
STT API 시스템
        """
        
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        # Gmail SMTP로 발송
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        
        text = msg.as_string()
        server.sendmail(sender_email, recipient_emails, text)
        server.quit()
        
        print(f"✅ 테스트 이메일 발송 완료!")
        print(f"   수신자: {', '.join(recipient_emails)}")
        return True
        
    except Exception as e:
        print(f"❌ 테스트 이메일 발송 실패: {str(e)}")
        print()
        print("일반적인 해결 방법:")
        print("1. Gmail 앱 비밀번호가 올바른지 확인")
        print("2. Gmail 계정에서 2단계 인증이 활성화되어 있는지 확인")
        print("3. '보안 수준이 낮은 앱의 액세스' 허용 (필요시)")
        return False

def load_env_file():
    """환경변수 파일을 시스템 환경변수로 로드"""
    env_file = Path.cwd() / ".env"
    if not env_file.exists():
        return
    
    with open(env_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and '=' in line and not line.startswith('#'):
                key, value = line.split('=', 1)
                os.environ[key] = value

if __name__ == "__main__":
    if setup_gmail_smtp():
        print("\n🎉 Gmail SMTP 설정이 완료되었습니다!")
        print()
        print("이제 API 서버에서 자동으로 이메일을 발송할 수 있습니다:")
        print("- 발신자: babel.ai.dub@gmail.com")
        print("- SMTP: Gmail (smtp.gmail.com:587)")
        print()
        print("API 서버를 재시작하면 새로운 설정이 적용됩니다.")