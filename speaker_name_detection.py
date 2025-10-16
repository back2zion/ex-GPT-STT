#!/usr/bin/env python3
"""
화자 이름 자동 인식 모듈
"나는 김철수입니다", "저는 이영희입니다" 등의 자기소개 패턴을 감지하여
화자1, 화자2를 실제 이름으로 변경
"""

import re
from typing import Dict, List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

class SpeakerNameDetector:
    def __init__(self):
        # 자기소개 패턴들 (실제 음성 패턴에 맞게 개선)
        self.intro_patterns = [
            r'나는\s+([가-힣]{2,4})\s*입니다',
            r'저는\s+([가-힣]{2,4})\s*입니다',  
            r'나는\s+([가-힣]{2,4})\s*이야',
            r'저는\s+([가-힣]{2,4})\s*이에요',
            r'나는\s+([가-힣]{2,4})\s*다',
            r'저는\s+([가-힣]{2,4})\s*예요',
            r'내가\s+([가-힣]{2,4})\s*이야',  # "내가 곽두일이야"
            r'제가\s+([가-힣]{2,4})\s*입니다',
            r'내\s*이름은\s+([가-힣]{2,4})',
            r'제\s*이름은\s+([가-힣]{2,4})',
        ]
        
        # 상대방 지칭 패턴들 (3자 지칭) - 이름만 추출하도록 개선
        self.reference_patterns = [
            r'([가-힣]{2,4})\s*(?:과장님?|팀장님?|부장님?|차장님?|대리님?|주임님?|사장님?|대표님?)\s*이?\s*말씀하신',
            r'([가-힣]{2,4})\s*(?:과장님?|팀장님?|부장님?|차장님?|대리님?|주임님?|사장님?|대표님?)\s*께서\s*(?:말씀|이야기)',
            r'([가-힣]{2,4})\s*(?:과장님?|팀장님?|부장님?|차장님?|대리님?|주임님?|사장님?|대표님?)\s*은?\s*어떻게\s*(?:생각|보세요)',
            r'([가-힣]{2,4})\s*(?:과장님?|팀장님?|부장님?|차장님?|대리님?|주임님?|사장님?|대표님?)\s*이?\s*(?:담당|책임)',
            r'([가-힣]{2,4})\s*(?:과장님?|팀장님?|부장님?|차장님?|대리님?|주임님?|사장님?|대표님?)\s*께서\s*(?:담당|책임)',
            r'([가-힣]{2,4})\s*(?:씨|님)\s*이?\s*말씀하신',
            r'([가-힣]{2,4})\s*(?:씨|님)\s*께서\s*(?:말씀|이야기)',
            r'([가-힣]{2,4})\s*(?:씨|님)\s*은?\s*어떻게\s*(?:생각|보세요)',
            r'([가-힣]{2,4})\s*선생님\s*이?\s*말씀하신',
            r'([가-힣]{2,4})\s*박사님\s*이?\s*(?:연구|발표)',
            r'([가-힣]{2,4})\s*교수님\s*이?\s*(?:강의|설명)',
            # 일반적인 지칭
            r'([가-힣]{2,4})\s*이?\s*그렇게\s*말했',
            r'([가-힣]{2,4})\s*이?\s*그런\s*(?:얘기|이야기)',
            r'([가-힣]{2,4})\s*이?\s*맞다고?\s*했',
            r'([가-힣]{2,4})\s*이?\s*(?:제안|의견)',
        ]
        
        # 컴파일된 패턴들
        self.compiled_patterns = [re.compile(pattern) for pattern in self.intro_patterns]
        self.compiled_reference_patterns = [re.compile(pattern) for pattern in self.reference_patterns]
        
        # 화자별 이름 매핑
        self.speaker_names = {}
        
        # 발견된 이름들 (상대방 지칭에서 감지된 이름들)
        self.mentioned_names = set()
        
        # 한국어 이름 후보들 (일반적인 이름들)
        self.common_names = {
            '김철수', '이영희', '박민수', '최지영', '정수현', '강혜진', '조민호', '윤서연',
            '장현우', '임다은', '한지민', '오세훈', '노민정', '송준혁', '배수지', '곽두일',
            '오진열', '백현복', '김성국', '박종현', '이상헌', '최영수', '정민철', '강태우'
        }
    
    def detect_names_in_segment(self, text: str, speaker_id: str) -> Optional[str]:
        """
        세그먼트에서 이름을 감지하고 화자 ID에 매핑 (자기소개 + 상대방 지칭)
        
        Args:
            text: 전사된 텍스트
            speaker_id: 화자 ID (예: "SPEAKER_00")
            
        Returns:
            감지된 이름 또는 None
        """
        # 1. 자기소개 패턴 감지
        for pattern in self.compiled_patterns:
            match = pattern.search(text)
            if match:
                name = match.group(1)
                
                # 2-4자 한글 이름 검증
                if len(name) >= 2 and len(name) <= 4 and name.replace(' ', '').isalpha():
                    logger.info(f"🎯 화자 이름 감지 (자기소개): {speaker_id} -> {name} (텍스트: {text[:50]})")
                    
                    # 기존에 다른 이름으로 매핑되어 있는지 확인
                    if speaker_id in self.speaker_names:
                        if self.speaker_names[speaker_id] != name:
                            logger.warning(f"⚠️ 화자 {speaker_id}의 이름이 변경됨: {self.speaker_names[speaker_id]} -> {name}")
                    
                    self.speaker_names[speaker_id] = name
                    return name
        
        # 2. 상대방 지칭 패턴 감지 (이름 수집)
        for pattern in self.compiled_reference_patterns:
            match = pattern.search(text)
            if match:
                mentioned_name = match.group(1)
                
                # 2-4자 한글 이름 검증 (직책 제외)
                if (len(mentioned_name) >= 2 and len(mentioned_name) <= 4 and 
                    mentioned_name.replace(' ', '').isalpha() and 
                    mentioned_name not in ['팀장', '과장', '부장', '차장', '대리', '주임', '사장', '대표']):
                    self.mentioned_names.add(mentioned_name)
                    logger.info(f"👥 상대방 지칭 감지: '{mentioned_name}' (발언자: {speaker_id}) (텍스트: {text[:50]})")
                    
        return None
    
    def process_transcription(self, segments: List[Dict]) -> List[Dict]:
        """
        전체 전사 결과에서 화자 이름을 감지하고 적용
        
        Args:
            segments: 화자 정보가 포함된 세그먼트 리스트
            
        Returns:
            이름이 적용된 세그먼트 리스트
        """
        logger.info(f"🔍 화자 이름 감지 시작: {len(segments)}개 세그먼트")
        
        # 1단계: 모든 세그먼트에서 이름 감지
        for segment in segments:
            text = segment.get('text', '')
            speaker = segment.get('speaker', 'SPEAKER_00')
            
            # 이름 감지 시도
            detected_name = self.detect_names_in_segment(text, speaker)
            
        # 2단계: 감지된 이름들 로그 출력
        if self.speaker_names:
            logger.info(f"✅ 감지된 화자 이름들 (자기소개): {self.speaker_names}")
        else:
            logger.info("ℹ️ 자기소개로 감지된 화자 이름이 없습니다")
            
        if self.mentioned_names:
            logger.info(f"👥 언급된 이름들 (상대방 지칭): {list(self.mentioned_names)}")
            
            # 3자 지칭으로 발견된 이름들을 미매핑 화자에 할당 시도
            unassigned_speakers = []
            for segment in segments:
                speaker = segment.get('speaker', 'SPEAKER_00')
                if speaker not in self.speaker_names:
                    unassigned_speakers.append(speaker)
            
            # 중복 제거
            unassigned_speakers = list(set(unassigned_speakers))
            
            if unassigned_speakers and self.mentioned_names:
                logger.info(f"🔗 미할당 화자와 언급된 이름 매칭 시도...")
                
                # 언급된 이름을 미할당 화자에 매핑 (중복 방지)
                mentioned_list = list(self.mentioned_names)
                assigned_names = set(self.speaker_names.values())  # 이미 할당된 이름들
                
                for speaker in unassigned_speakers:
                    # 아직 할당되지 않은 이름 찾기
                    for mentioned_name in mentioned_list:
                        if mentioned_name not in assigned_names:
                            self.speaker_names[speaker] = mentioned_name
                            assigned_names.add(mentioned_name)
                            logger.info(f"🎯 추정 매핑: {speaker} -> {mentioned_name} (상대방 지칭 기반)")
                            break
        else:
            logger.info("ℹ️ 상대방 지칭으로 감지된 이름이 없습니다")
        
        # 3단계: 모든 세그먼트의 화자 정보를 실제 이름으로 변경
        updated_segments = []
        for segment in segments:
            updated_segment = segment.copy()
            speaker = segment.get('speaker', 'SPEAKER_00')
            
            if speaker in self.speaker_names:
                updated_segment['speaker'] = self.speaker_names[speaker]
                updated_segment['original_speaker'] = speaker  # 원본 화자 ID 보존
                
            updated_segments.append(updated_segment)
        
        logger.info(f"🔄 화자 이름 적용 완료: {len(self.speaker_names)}명의 화자 이름 변경")
        return updated_segments
    
    def apply_names_to_text(self, text: str) -> str:
        """
        텍스트 내의 화자 표시를 실제 이름으로 변경
        
        Args:
            text: 원본 텍스트
            
        Returns:
            이름이 적용된 텍스트
        """
        if not self.speaker_names:
            return text
            
        updated_text = text
        
        # 화자 패턴을 이름으로 변경
        for speaker_id, name in self.speaker_names.items():
            # "SPEAKER_00:" -> "김철수:"
            updated_text = re.sub(
                rf'{speaker_id}:', 
                f'{name}:', 
                updated_text
            )
            
            # "화자1:" -> "김철수:" (번호 기반 패턴도 처리)
            speaker_num = speaker_id.replace('SPEAKER_', '').replace('0', '')
            if speaker_num.isdigit():
                speaker_num = str(int(speaker_num) + 1)  # 0-based to 1-based
                updated_text = re.sub(
                    rf'화자{speaker_num}:', 
                    f'{name}:', 
                    updated_text
                )
        
        return updated_text
    
    def get_speaker_mapping(self) -> Dict[str, str]:
        """
        현재 화자-이름 매핑 반환
        
        Returns:
            화자 ID -> 이름 매핑 딕셔너리
        """
        return self.speaker_names.copy()
    
    def clear_mappings(self):
        """화자 매핑 초기화"""
        self.speaker_names.clear()
        self.mentioned_names.clear()
        logger.info("🧹 화자 이름 매핑 초기화 완료")

def process_speaker_names(transcription_segments: List[Dict]) -> Tuple[List[Dict], Dict[str, str]]:
    """
    편의 함수: 화자 이름 감지 및 적용
    
    Args:
        transcription_segments: STT 결과 세그먼트들
        
    Returns:
        Tuple[업데이트된 세그먼트들, 화자 매핑 딕셔너리]
    """
    detector = SpeakerNameDetector()
    updated_segments = detector.process_transcription(transcription_segments)
    mapping = detector.get_speaker_mapping()
    
    return updated_segments, mapping

# 테스트 코드
if __name__ == "__main__":
    # 테스트 데이터 (자기소개 + 상대방 지칭 포함)
    test_segments = [
        {
            "start": 0.0,
            "end": 3.0,
            "text": "안녕하세요 나는 김철수입니다",
            "speaker": "SPEAKER_00"
        },
        {
            "start": 3.5,
            "end": 6.0,
            "text": "네 안녕하세요 반갑습니다",
            "speaker": "SPEAKER_01"
        },
        {
            "start": 6.5,
            "end": 9.0,
            "text": "김철수 팀장님이 말씀하신 대로 진행하겠습니다",
            "speaker": "SPEAKER_01"
        },
        {
            "start": 10.0,
            "end": 12.0,
            "text": "박민수씨는 어떻게 생각하세요?",
            "speaker": "SPEAKER_00"
        },
        {
            "start": 13.0,
            "end": 15.0,
            "text": "저는 박민수입니다. 그 의견에 동의합니다",
            "speaker": "SPEAKER_02"
        },
        {
            "start": 16.0,
            "end": 18.0,
            "text": "최지영 과장님께서 담당하시면 좋을 것 같습니다",
            "speaker": "SPEAKER_01"
        }
    ]
    
    # 테스트 실행
    logging.basicConfig(level=logging.INFO)
    updated_segments, mapping = process_speaker_names(test_segments)
    
    print("=== 화자 매핑 결과 ===")
    for k, v in mapping.items():
        print(f"{k} -> {v}")
    
    print("\n=== 업데이트된 세그먼트 ===")
    for segment in updated_segments:
        print(f"{segment['speaker']}: {segment['text']}")