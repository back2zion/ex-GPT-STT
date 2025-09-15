#!/usr/bin/env python3

from faster_whisper import WhisperModel
import sys
import os
from datetime import datetime

def transcribe_audio(audio_file):
    """STT 실행"""
    if not os.path.exists(audio_file):
        print(f"File not found: {audio_file}")
        return
    
    print(f"File: {os.path.basename(audio_file)}")
    print("Transcribing with Large-v3 model...")
    
    model = WhisperModel("large-v3", device="cpu", compute_type="int8")
    
    segments, info = model.transcribe(
        audio_file,
        beam_size=5,
        language="ko",
        vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=500),
        temperature=0.0,
        compression_ratio_threshold=2.4,
        no_speech_threshold=0.6,
        condition_on_previous_text=False
    )
    
    # Save results
    base_name = os.path.splitext(os.path.basename(audio_file))[0]
    output_dir = os.path.dirname(audio_file)
    output_file = os.path.join(output_dir, f"{base_name}_STT.txt")
    
    print(f"Saving to: {output_file}")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"{base_name} - STT Results\n")
        f.write(f"{datetime.now().strftime('%Y.%m.%d %H:%M')} - {info.duration:.0f}s\n")
        f.write(f"Language: {info.language} ({info.language_probability:.1%})\n\n")
        
        segment_count = 0
        for segment in segments:
            f.write(f"[{segment.start:.1f}s -> {segment.end:.1f}s]\n")
            f.write(f"{segment.text.strip()}\n\n")
            segment_count += 1
            
            print(f"[{segment.start:.1f}s] {segment.text.strip()}")
        
        f.write(f"Total: {segment_count} segments\n")
    
    print(f"\nDone! Saved: {os.path.basename(output_file)}")
    print(f"Segments: {segment_count}, Duration: {info.duration:.1f}s")

def main():
    if len(sys.argv) == 2:
        # Direct file path
        audio_file = sys.argv[1].strip().strip('"').strip("'")
        
        # Convert Windows path to WSL
        if audio_file.lower().startswith(("c:\\", "c:/")):
            if "\\" in audio_file:
                audio_file = audio_file.replace("C:\\", "/mnt/c/").replace("\\", "/")
            else:
                audio_file = audio_file.replace("C:/", "/mnt/c/").replace("c:/", "/mnt/c/")
        
        transcribe_audio(audio_file)
    else:
        # Interactive mode
        print("STT - Speech to Text")
        print("=" * 30)
        print("Drag audio file to terminal or enter path:")
        
        while True:
            try:
                audio_file = input("\nFile path: ").strip()
                
                # Remove quotes
                if audio_file.startswith('"') and audio_file.endswith('"'):
                    audio_file = audio_file[1:-1]
                elif audio_file.startswith("'") and audio_file.endswith("'"):
                    audio_file = audio_file[1:-1]
                
                if not audio_file:
                    print("Please enter file path")
                    continue
                
                # Convert Windows to WSL path
                if audio_file.lower().startswith(("c:\\", "c:/")):
                    if "\\" in audio_file:
                        audio_file = audio_file.replace("C:\\", "/mnt/c/").replace("\\", "/")
                    else:
                        audio_file = audio_file.replace("C:/", "/mnt/c/").replace("c:/", "/mnt/c/")
                    print(f"Converted: {audio_file}")
                
                # Check format
                supported = ('.mp3', '.wav', '.m4a', '.flac', '.aac', '.ogg')
                if not audio_file.lower().endswith(supported):
                    print(f"Unsupported format. Use: {', '.join(supported)}")
                    continue
                
                transcribe_audio(audio_file)
                
                again = input("\nProcess another file? (y/N): ").strip().lower()
                if again not in ['y', 'yes']:
                    break
                    
            except KeyboardInterrupt:
                print("\n\nBye!")
                break
            except EOFError:
                break

if __name__ == "__main__":
    main()