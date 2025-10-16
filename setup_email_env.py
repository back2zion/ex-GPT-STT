#!/usr/bin/env python3

"""
이메일 설정 도우미 스크립트
환경변수를 설정하여 자동 이메일 발송을 활성화합니다.
"""

import os
import getpass

def setup_name_email_mapping():
    """이름-이메일 매핑 설정"""
    print("\n👥 이름-이메일 매핑 설정 (선택사항)")
    print("파일명에서 발신자 이름을 추출하여 자동으로 회신하는 기능입니다.")
    print("예: '김철수_1013_도공회의.m4a' → 김철수에게 자동 회신")
    print()
    
    name_mapping = {}
    
    while True:
        name = input("발신자 이름 (종료하려면 엔터): ").strip()
        if not name:
            break
            
        email = input(f"{name}님의 이메일: ").strip()
        if email:
            name_mapping[name] = email
            print(f"✅ {name} → {email} 매핑 추가")
        else:
            print("❌ 이메일을 입력하지 않았습니다. 건너뜁니다.")
        print()
    
    if name_mapping:
        import json
        mapping_json = json.dumps(name_mapping, ensure_ascii=False)
        return mapping_json
    return None

def setup_email_environment():
    """이메일 환경변수 설정"""
    print("📧 이메일 자동 발송 설정")
    print("=" * 50)
    print("이 설정은 ~/.bashrc에 환경변수를 추가합니다.")
    print("Gmail을 사용하는 경우 '앱 비밀번호'를 사용하세요.")
    print("(Google 계정 > 보안 > 2단계 인증 > 앱 비밀번호)")
    print()
    
    # 현재 환경변수 확인
    current_sender = os.environ.get('SENDER_EMAIL', '')
    current_recipients = os.environ.get('EMAIL_TO', '')
    current_mapping = os.environ.get('EMAIL_NAME_MAPPING', '')
    
    if current_sender:
        print(f"현재 설정된 발신자: {current_sender}")
    if current_recipients:
        print(f"현재 설정된 수신자: {current_recipients}")
    if current_mapping:
        print(f"현재 이름 매핑: {current_mapping}")
    print()
    
    # 발신자 이메일
    sender_email = input(f"발신자 이메일 ({current_sender}): ").strip()
    if not sender_email:
        sender_email = current_sender
    if not sender_email:
        print("❌ 발신자 이메일이 필요합니다.")
        return False
    
    # 발신자 비밀번호
    sender_password = getpass.getpass("발신자 이메일 비밀번호 (Gmail 앱 비밀번호): ")
    if not sender_password:
        print("❌ 비밀번호가 필요합니다.")
        return False
    
    # 수신자 이메일
    recipients = input(f"수신자 이메일 (쉼표로 구분, {current_recipients}): ").strip()
    if not recipients:
        recipients = current_recipients
    if not recipients:
        print("❌ 수신자 이메일이 필요합니다.")
        return False
    
    # 이름-이메일 매핑 설정
    name_mapping = setup_name_email_mapping()
    
    # 환경변수를 ~/.bashrc에 추가
    bashrc_path = os.path.expanduser("~/.bashrc")
    env_lines = [
        f'export SENDER_EMAIL="{sender_email}"',
        f'export SENDER_PASSWORD="{sender_password}"',
        f'export EMAIL_TO="{recipients}"',
        f'export EMAIL_AUTO_SEND="1"'
    ]
    
    # 이름 매핑이 있으면 추가
    if name_mapping:
        env_lines.append(f'export EMAIL_NAME_MAPPING=\'{name_mapping}\'')
        print(f"✅ 이름-이메일 매핑 설정됨: {len(eval(name_mapping))}개 항목")
    
    try:
        # 기존 설정 제거 (있는 경우)
        if os.path.exists(bashrc_path):
            with open(bashrc_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # 기존 이메일 관련 환경변수 제거
            filtered_lines = []
            for line in lines:
                if not any(var in line for var in ['SENDER_EMAIL', 'SENDER_PASSWORD', 'EMAIL_TO', 'EMAIL_AUTO_SEND', 'EMAIL_NAME_MAPPING']):
                    filtered_lines.append(line)
            
            with open(bashrc_path, 'w', encoding='utf-8') as f:
                f.writelines(filtered_lines)
        
        # 새로운 설정 추가
        with open(bashrc_path, 'a', encoding='utf-8') as f:
            f.write("\n# STT 이메일 발송 설정 (자동 생성)\n")
            for line in env_lines:
                f.write(line + '\n')
        
        print("\n✅ 환경변수 설정 완료!")
        print(f"📝 설정 파일: {bashrc_path}")
        print("\n📋 설정된 변수:")
        print(f"   SENDER_EMAIL: {sender_email}")
        print(f"   EMAIL_TO: {recipients}")
        print(f"   EMAIL_AUTO_SEND: 1")
        print("\n💡 설정을 적용하려면:")
        print("   source ~/.bashrc")
        print("   또는 새 터미널을 여세요.")
        
        return True
        
    except Exception as e:
        print(f"❌ 설정 저장 실패: {e}")
        return False

def test_email_settings():
    """이메일 설정 테스트"""
    print("\n🧪 이메일 설정 테스트")
    
    try:
        from email_utils import send_meeting_minutes_email
        import tempfile
        from datetime import datetime
        
        # 환경변수 읽기
        sender_email = os.environ.get('SENDER_EMAIL')
        sender_password = os.environ.get('SENDER_PASSWORD')
        email_to = os.environ.get('EMAIL_TO')
        
        if not all([sender_email, sender_password, email_to]):
            print("❌ 환경변수가 설정되지 않았습니다.")
            return False
        
        # 테스트 파일 생성
        test_file = tempfile.mktemp(suffix='.txt')
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(f"이메일 발송 테스트\n")
            f.write(f"생성 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"테스트 내용입니다.\n")
        
        # 이메일 발송 테스트
        recipients = [email.strip() for email in email_to.split(',')]
        success = send_meeting_minutes_email(
            meeting_minutes_path=test_file,
            stt_result_path=test_file,
            recipient_emails=recipients,
            meeting_title="이메일 발송 테스트",
            sender_email=sender_email,
            sender_password=sender_password
        )
        
        # 테스트 파일 삭제
        os.unlink(test_file)
        
        if success:
            print("✅ 이메일 설정 테스트 성공!")
            return True
        else:
            print("❌ 이메일 설정 테스트 실패!")
            return False
            
    except Exception as e:
        print(f"❌ 테스트 중 오류: {e}")
        return False

def show_current_settings():
    """현재 이메일 설정 표시"""
    print("📋 현재 이메일 설정")
    print("=" * 30)
    
    sender = os.environ.get('SENDER_EMAIL', '미설정')
    recipients = os.environ.get('EMAIL_TO', '미설정')
    auto_send = os.environ.get('EMAIL_AUTO_SEND', '0')
    
    print(f"발신자: {sender}")
    print(f"수신자: {recipients}")
    print(f"자동 발송: {'활성화' if auto_send == '1' else '비활성화'}")

if __name__ == "__main__":
    print("🔧 STT 이메일 발송 설정 도우미")
    print("=" * 50)
    
    while True:
        print("\n메뉴:")
        print("1. 이메일 설정하기")
        print("2. 현재 설정 확인")
        print("3. 이메일 테스트")
        print("4. 종료")
        
        choice = input("\n선택하세요 (1-4): ").strip()
        
        if choice == '1':
            setup_email_environment()
        elif choice == '2':
            show_current_settings()
        elif choice == '3':
            test_email_settings()
        elif choice == '4':
            print("👋 설정을 완료했습니다!")
            break
        else:
            print("❌ 올바른 번호를 선택하세요.")