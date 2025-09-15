# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Structure

This project extends faster-whisper with Korean STT post-processing and meeting minutes generation. The main components are:

### Core Files
- **`app.py`**: GUI application for STT processing with post-processing features
- **`stt.py`**: Command-line STT processing script
- **`stt_simple.py`**: Simplified STT script
- **`main.py`**: Main entry point

### Package Structure
- **`faster_whisper/`**: Core faster-whisper library
  - `transcribe.py`: Main transcription functionality
  - `audio.py`: Audio processing utilities
  - `feature_extractor.py`: Feature extraction for ML models
  - `tokenizer.py`: Text tokenization
  - `vad.py`: Voice Activity Detection
  - `assets/`: Pre-trained models (Silero VAD ONNX files)

### Testing & Development
- **`tests/`**: Test suite with audio samples
  - `data/`: Test audio files (FLAC, MP3, WAV formats)
  - `test_transcribe.py`: Transcription tests
  - `test_tokenizer.py`: Tokenizer tests
  - `test_utils.py`: Utility function tests

### Configuration & Build
- **`pyproject.toml`**: Modern Python packaging configuration (uv support)
- **`uv.lock`**: UV package manager lock file

### Additional Resources
- **`benchmark/`**: Performance benchmarking scripts and test data
- **`docker/`**: Docker containerization files

## Development Commands

### Installation for Development (UV Package Manager)
```bash
# Using UV (recommended)
uv sync

# Traditional pip
pip install -e .
```

### Testing
```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_transcribe.py

# Run tests with verbose output
pytest -v tests/
```

### Code Quality
```bash
# Format code
black .
isort .

# Lint code
flake8 .
```

### Building Package
```bash
# Build distribution packages
uv build
```

### Model Conversion (Optional)
```bash
# Install conversion dependencies
uv add ct2-transformers-converter

# Convert Transformers model to CTranslate2 format
ct2-transformers-converter --model openai/whisper-base --output_dir whisper-base-ct2
```

## Architecture Overview

This is **faster-whisper**, a high-performance reimplementation of OpenAI's Whisper speech-to-text model using CTranslate2 for optimized inference. The library provides up to 4x speed improvements with lower memory usage compared to the original implementation.

## STT Post-processing and Meeting Minutes Generation

### Key Process Flow:
1. **STT (Speech-to-Text)**: Audio transcription using faster-whisper
2. **Post-processing**: Text correction and refinement using reference dictionary
3. **AI Analysis**: Content analysis using qwen2.5:32b model via Ollama
4. **Meeting Minutes**: Generate structured minutes following PDF template format

### Post-processing Dictionary:
- Reference location: `C:\Users\KwakDaniel\OneDrive\첨부 파일\interview_STT`
- Use ALL files in this directory as correction reference
- Apply corrections for technical terms, proper nouns, and domain-specific vocabulary

### Meeting Minutes Template:
- Follow the format from: `C:\Users\KwakDaniel\OneDrive\첨부 파일\회의록.pdf`
- **Table Format Structure**:
  - Header: 회의록 (제목), 확인자(수행업체 PM, 감독원) 
  - Basic Info: 일시, 장소, 회의주제, 참석자, 작성자
  - Content: 회의 내용 (주요 내용 기술 with numbered items and bullet points)
  - Issues: 이슈사항(미결사항) with bullet points
  - Attachments: 첨부파일 with bullet points
- **Required Fields**: All fields must be structured in table format matching PDF template
- Use AI analysis to extract meaningful content structure and populate template fields

### AI Integration:
- Model: qwen3:32b (via Ollama API at localhost:11434)
- Purpose: Analyze transcribed content and generate structured meeting minutes
- Fallback: Basic structure if AI analysis fails

### Core Components

#### Main Classes
- **`WhisperModel`** (faster_whisper/transcribe.py): Primary interface for speech transcription
- **`BatchedInferencePipeline`** (faster_whisper/transcribe.py): Batched transcription for improved throughput
- **`FeatureExtractor`** (faster_whisper/feature_extractor.py): Converts audio to mel-spectrogram features
- **`Tokenizer`** (faster_whisper/tokenizer.py): Handles text tokenization and language processing

#### Audio Processing
- **`decode_audio()`** (faster_whisper/audio.py): Audio decoding using PyAV (bundled FFmpeg)
- **`VadOptions`** & VAD functions (faster_whisper/vad.py): Voice Activity Detection using Silero VAD model

#### Key Data Structures
- **`Word`**: Individual word with timestamps and probability
- **`Segment`**: Transcription segment with metadata (timestamps, confidence scores, etc.)
- **`TranscriptionOptions`**: Configuration for transcription parameters

### Model Architecture Flow

1. **Audio Input** → `decode_audio()` → Raw audio array (16kHz, mono)
2. **Feature Extraction** → `FeatureExtractor` → Mel-spectrogram features  
3. **VAD Processing** (optional) → Speech timestamp detection → Audio chunks
4. **Tokenization** → `Tokenizer` → Token sequences with language/task tokens
5. **CTranslate2 Inference** → `WhisperModel` → Decoded transcription
6. **Post-processing** → Word-level timestamps, confidence scores → `Segment` objects

### Model Support
- Supports all OpenAI Whisper model sizes (tiny, base, small, medium, large-v3)
- Compatible with Distil-Whisper models (e.g., distil-large-v3)
- Automatic model download from Hugging Face Hub or local model loading
- Model conversion from Transformers format using `ct2-transformers-converter`

### Performance Features
- Multiple compute types: float16, int8, float32
- GPU acceleration with CUDA support (requires cuBLAS + cuDNN)
- Batched inference for higher throughput
- Voice Activity Detection for silence filtering
- Word-level timestamp generation

### Dependencies
- **CTranslate2**: Optimized transformer inference engine (>=4.0,<5)
- **PyAV**: Audio decoding (replaces FFmpeg dependency)
- **ONNX Runtime**: For VAD model inference (>=1.14,<2)
- **Hugging Face Hub**: Model downloading and caching
- **Tokenizers**: Fast tokenization

## Testing

The test suite covers:
- Transcription accuracy and functionality (tests/test_transcribe.py)
- Tokenization and language handling (tests/test_tokenizer.py) 
- Utility functions (tests/test_utils.py)

Test data is located in `tests/data/` with various audio formats (FLAC, MP3, WAV).

## Key Implementation Details

### Model Loading and Caching
- Models are cached locally via Hugging Face Hub (`~/.cache/huggingface/`)
- Local model loading supported via file paths
- Automatic model download and conversion from Transformers format

### Performance Optimizations
- **Batching**: Use `BatchedInferencePipeline` for processing multiple audio files
- **Quantization**: Support for int8, float16, and float32 compute types
- **VAD Integration**: Automatic silence detection and removal using Silero VAD
- **GPU Memory Management**: Efficient VRAM usage with configurable batch sizes

### Audio Processing Pipeline
Audio input → PyAV decode (16kHz mono) → VAD segmentation → Feature extraction (mel-spectrograms) → CTranslate2 inference → Post-processing (timestamps, confidence)