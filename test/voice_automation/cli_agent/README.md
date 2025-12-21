# Voice Agent CLI

Command-line voice agent with multi-language support for testing and development.

## Installation

```bash
pip install httpx websockets soundfile numpy
```

## Usage

### Interactive Mode (Default)
```bash
python voice_agent.py
python voice_agent.py --lang hi  # Hindi
python voice_agent.py --lang kn  # Kannada
python voice_agent.py --lang mr  # Marathi
```

### Speak Text
```bash
python voice_agent.py --action speak --text "Hello, how are you?" --lang en
python voice_agent.py --action speak --text "नमस्ते, कैसे हो?" --lang hi
```

### Transcribe Audio
```bash
python voice_agent.py --action listen --audio recording.wav --lang en
```

### Single Conversation Turn
```bash
python voice_agent.py --action converse --text "What is the weather?" --lang en
```

## Supported Languages

| Code | Language |
|------|----------|
| en   | English  |
| hi   | Hindi    |
| kn   | Kannada  |
| mr   | Marathi  |

## Environment Variables

- `PIPER_URL`: Piper TTS service URL (default: http://192.168.20.62:5500)
- `WHISPER_WS_URL`: WhisperLiveKit WebSocket URL (default: ws://192.168.1.120:8765/)
- `OLLAMA_URL`: Ollama LLM URL (default: http://192.168.1.120:11434)
- `OLLAMA_MODEL`: Ollama model name (default: llama3.1:8b)

## Examples

### English Conversation
```bash
$ python voice_agent.py --lang en

=== Voice Agent - English ===
Type your message or 'quit' to exit

[You]: Hello
[Agent]: Hello! How can I assist you today?
[You]: quit
Goodbye!
```

### Hindi Conversation
```bash
$ python voice_agent.py --lang hi

=== Voice Agent - Hindi ===
Type your message or 'quit' to exit

[You]: नमस्ते
[Agent]: नमस्ते! मैं आपकी कैसे मदद कर सकता हूं?
```
