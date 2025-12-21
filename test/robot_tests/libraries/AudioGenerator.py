"""
Audio Generation Library for Headless Testing
Generates synthetic speech audio for testing without mic/speaker
"""

import asyncio
import numpy as np
import soundfile as sf
import subprocess
import tempfile
import os
from pathlib import Path

class AudioGenerator:
    """Generate test audio for headless voice testing"""

    SAMPLE_RATE = 16000  # 16kHz for LiveKit/Whisper

    # Test phrases for each language
    TEST_PHRASES = {
        "en": [
            "Hello, how are you today?",
            "What is the weather like?",
            "Thank you for your help",
            "Goodbye, have a nice day",
        ],
        "hi": [
            "नमस्ते, आप कैसे हैं?",
            "मौसम कैसा है?",
            "आपकी मदद के लिए धन्यवाद",
            "अलविदा, आपका दिन शुभ हो",
        ],
        "kn": [
            "ನಮಸ್ಕಾರ, ನೀವು ಹೇಗಿದ್ದೀರಿ?",
            "ಹವಾಮಾನ ಹೇಗಿದೆ?",
            "ನಿಮ್ಮ ಸಹಾಯಕ್ಕೆ ಧನ್ಯವಾದಗಳು",
            "ವಿದಾಯ, ನಿಮಗೆ ಶುಭ ದಿನವಾಗಲಿ",
        ],
        "ta": [
            "வணக்கம், நீங்கள் எப்படி இருக்கிறீர்கள்?",
            "வானிலை எப்படி இருக்கிறது?",
            "உங்கள் உதவிக்கு நன்றி",
            "பிரியாவிடை, நல்ல நாள்",
        ],
        "te": [
            "నమస్కారం, మీరు ఎలా ఉన్నారు?",
            "వాతావరణం ఎలా ఉంది?",
            "మీ సహాయానికి ధన్యవాదాలు",
            "వీడ్కోలు, మంచి రోజు",
        ],
        "ml": [
            "നമസ്കാരം, നിങ്ങൾ എങ്ങനെയുണ്ട്?",
            "കാലാവസ്ഥ എങ്ങനെയുണ്ട്?",
            "നിങ്ങളുടെ സഹായത്തിന് നന്ദി",
            "വിട, നല്ല ദിവസം",
        ],
        "mr": [
            "नमस्कार, तुम्ही कसे आहात?",
            "हवामान कसे आहे?",
            "तुमच्या मदतीबद्दल धन्यवाद",
            "निरोप, तुमचा दिवस चांगला जावो",
        ],
    }

    def __init__(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix="robot_audio_"))

    def generate_silence(self, duration_seconds=1.0):
        """Generate silence audio"""
        samples = int(self.SAMPLE_RATE * duration_seconds)
        audio = np.zeros(samples, dtype=np.int16)

        output_file = self.temp_dir / f"silence_{duration_seconds}s.wav"
        sf.write(str(output_file), audio, self.SAMPLE_RATE)
        return str(output_file)

    def generate_tone(self, frequency=440, duration_seconds=1.0):
        """Generate tone (for testing audio pipeline)"""
        t = np.linspace(0, duration_seconds, int(self.SAMPLE_RATE * duration_seconds))
        audio = np.sin(2 * np.pi * frequency * t) * 0.3
        audio = (audio * 32767).astype(np.int16)

        output_file = self.temp_dir / f"tone_{frequency}hz_{duration_seconds}s.wav"
        sf.write(str(output_file), audio, self.SAMPLE_RATE)
        return str(output_file)

    def generate_speech_espeak(self, text, language="en", output_path=None):
        """Generate speech using eSpeak (open-source TTS)

        Args:
            text: Text to synthesize
            language: Language code (en, hi, kn, ta, te, ml, mr)
            output_path: Optional output path

        Returns:
            Path to generated audio file
        """
        if output_path is None:
            output_path = self.temp_dir / f"speech_{language}_{hash(text)}.wav"

        # eSpeak language mapping
        espeak_lang_map = {
            "en": "en",
            "hi": "hi",
            "kn": "kn",
            "ta": "ta",
            "te": "te",
            "ml": "ml",
            "mr": "mr",
        }

        espeak_lang = espeak_lang_map.get(language, "en")

        # Install espeak if needed
        self._ensure_espeak_installed()

        # Generate speech with eSpeak
        cmd = [
            "espeak",
            "-v", espeak_lang,
            "-w", str(output_path),
            "-s", "150",  # Speed: 150 words per minute
            text
        ]

        try:
            subprocess.run(cmd, check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            # Fallback: generate silence if eSpeak fails
            return self.generate_silence(2.0)

        # Convert to 16kHz mono (LiveKit requirement)
        self._convert_to_16khz_mono(output_path)

        return str(output_path)

    def generate_test_phrase(self, language="en", phrase_index=0):
        """Generate a test phrase in specified language"""
        phrases = self.TEST_PHRASES.get(language, self.TEST_PHRASES["en"])
        text = phrases[phrase_index % len(phrases)]
        return self.generate_speech_espeak(text, language)

    def generate_incomplete_phrase(self, language="en"):
        """Generate incomplete phrase (for VAD testing - silence timeout)"""
        incomplete_texts = {
            "en": "Hello, I want to...",  # Incomplete
            "hi": "नमस्ते, मैं चाहता हूं...",
            "kn": "ನಮಸ್ಕಾರ, ನಾನು ಬಯಸುತ್ತೇನೆ...",
            "ta": "வணக்கம், நான் விரும்புகிறேன்...",
            "te": "నమస్కారం, నేను కోరుకుంటున్నాను...",
            "ml": "നമസ്കാരം, എനിക്ക് വേണം...",
            "mr": "नमस्कार, मला पाहिजे...",
        }

        text = incomplete_texts.get(language, incomplete_texts["en"])
        return self.generate_speech_espeak(text, language)

    def _ensure_espeak_installed(self):
        """Install eSpeak if not present"""
        try:
            subprocess.run(["espeak", "--version"], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            # Install eSpeak
            subprocess.run(["apt-get", "update"], check=False)
            subprocess.run([
                "apt-get", "install", "-y", "espeak", "espeak-ng"
            ], check=False)

    def _convert_to_16khz_mono(self, audio_path):
        """Convert audio to 16kHz mono using ffmpeg"""
        temp_output = str(audio_path) + ".tmp.wav"

        try:
            cmd = [
                "ffmpeg", "-i", str(audio_path),
                "-ar", str(self.SAMPLE_RATE),
                "-ac", "1",
                "-y",
                temp_output
            ]
            subprocess.run(cmd, check=True, capture_output=True)

            # Replace original
            os.replace(temp_output, audio_path)
        except (subprocess.CalledProcessError, FileNotFoundError):
            # ffmpeg not available, keep original
            pass

    def cleanup(self):
        """Clean up temporary files"""
        import shutil
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
