"""
Audio Keywords for Robot Framework
Keywords for audio file handling and processing
"""
import os
import logging
import tempfile
import time
from typing import Optional

from robot.api.deco import keyword, library

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    np = None
    NUMPY_AVAILABLE = False

try:
    import soundfile as sf
    SOUNDFILE_AVAILABLE = True
except ImportError:
    sf = None
    SOUNDFILE_AVAILABLE = False

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from config import AUDIO_SAMPLE_RATE, AUDIO_CHANNELS

logger = logging.getLogger(__name__)


@library(scope='GLOBAL')
class AudioKeywords:
    """Keywords for audio file handling"""

    ROBOT_LIBRARY_SCOPE = 'GLOBAL'

    def __init__(self):
        self.temp_dir = tempfile.mkdtemp(prefix="audio_test_")
        self.last_audio_path = None
        self.last_duration = 0

    @keyword("Generate Test Tone")
    def generate_test_tone(self, frequency: str = "440", duration: str = "1.0",
                          output_path: str = None) -> str:
        """Generate a test tone audio file"""
        if not NUMPY_AVAILABLE or not SOUNDFILE_AVAILABLE:
            raise AssertionError("numpy and soundfile required for audio generation")

        freq = float(frequency)
        dur = float(duration)

        if not output_path:
            output_path = os.path.join(
                self.temp_dir,
                f"tone_{int(freq)}hz_{int(time.time())}.wav"
            )

        # Generate sine wave
        t = np.linspace(0, dur, int(AUDIO_SAMPLE_RATE * dur), dtype=np.float32)
        audio = np.sin(2 * np.pi * freq * t) * 0.5

        # Save to file
        sf.write(output_path, audio, AUDIO_SAMPLE_RATE)

        self.last_audio_path = output_path
        self.last_duration = dur
        logger.info(f"Generated test tone: {output_path}")
        return output_path

    @keyword("Generate Silence")
    def generate_silence(self, duration: str = "1.0",
                        output_path: str = None) -> str:
        """Generate a silent audio file"""
        if not NUMPY_AVAILABLE or not SOUNDFILE_AVAILABLE:
            raise AssertionError("numpy and soundfile required")

        dur = float(duration)

        if not output_path:
            output_path = os.path.join(
                self.temp_dir,
                f"silence_{int(time.time())}.wav"
            )

        # Generate silence
        samples = int(AUDIO_SAMPLE_RATE * dur)
        audio = np.zeros(samples, dtype=np.float32)

        sf.write(output_path, audio, AUDIO_SAMPLE_RATE)

        self.last_audio_path = output_path
        self.last_duration = dur
        logger.info(f"Generated silence: {output_path}")
        return output_path

    @keyword("Get Audio Duration")
    def get_audio_duration(self, audio_path: str) -> float:
        """Get duration of audio file in seconds"""
        if not SOUNDFILE_AVAILABLE:
            raise AssertionError("soundfile required")

        info = sf.info(audio_path)
        return info.duration

    @keyword("Get Audio Sample Rate")
    def get_audio_sample_rate(self, audio_path: str) -> int:
        """Get sample rate of audio file"""
        if not SOUNDFILE_AVAILABLE:
            raise AssertionError("soundfile required")

        info = sf.info(audio_path)
        return info.samplerate

    @keyword("Audio Duration Should Be Greater Than")
    def audio_duration_should_be_greater_than(self, audio_path: str,
                                               min_duration: str):
        """Verify audio duration is greater than minimum"""
        duration = self.get_audio_duration(audio_path)
        min_dur = float(min_duration)

        if duration < min_dur:
            raise AssertionError(
                f"Audio duration {duration:.2f}s is less than {min_dur:.2f}s"
            )
        return True

    @keyword("Audio Duration Should Be Less Than")
    def audio_duration_should_be_less_than(self, audio_path: str,
                                            max_duration: str):
        """Verify audio duration is less than maximum"""
        duration = self.get_audio_duration(audio_path)
        max_dur = float(max_duration)

        if duration > max_dur:
            raise AssertionError(
                f"Audio duration {duration:.2f}s is greater than {max_dur:.2f}s"
            )
        return True

    @keyword("Audio File Should Exist")
    def audio_file_should_exist(self, audio_path: str):
        """Verify audio file exists"""
        if not os.path.exists(audio_path):
            raise AssertionError(f"Audio file not found: {audio_path}")
        return True

    @keyword("Audio Should Not Be Silent")
    def audio_should_not_be_silent(self, audio_path: str,
                                    threshold: str = "0.01"):
        """Verify audio is not silent (has some amplitude)"""
        if not NUMPY_AVAILABLE or not SOUNDFILE_AVAILABLE:
            raise AssertionError("numpy and soundfile required")

        data, _ = sf.read(audio_path)
        max_amplitude = np.max(np.abs(data))

        if max_amplitude < float(threshold):
            raise AssertionError(
                f"Audio appears silent (max amplitude: {max_amplitude:.4f})"
            )
        return True

    @keyword("Concatenate Audio Files")
    def concatenate_audio_files(self, output_path: str, *audio_paths) -> str:
        """Concatenate multiple audio files"""
        if not NUMPY_AVAILABLE or not SOUNDFILE_AVAILABLE:
            raise AssertionError("numpy and soundfile required")

        all_audio = []
        sample_rate = None

        for path in audio_paths:
            data, sr = sf.read(path)
            if sample_rate is None:
                sample_rate = sr
            elif sr != sample_rate:
                # Resample if needed
                from scipy import signal
                samples = int(len(data) * sample_rate / sr)
                data = signal.resample(data, samples)

            all_audio.append(data)

        combined = np.concatenate(all_audio)
        sf.write(output_path, combined, sample_rate)

        logger.info(f"Concatenated {len(audio_paths)} files to: {output_path}")
        return output_path

    @keyword("Trim Audio")
    def trim_audio(self, audio_path: str, start: str = "0",
                   end: str = None, output_path: str = None) -> str:
        """Trim audio file to specified start/end times"""
        if not NUMPY_AVAILABLE or not SOUNDFILE_AVAILABLE:
            raise AssertionError("numpy and soundfile required")

        data, sample_rate = sf.read(audio_path)
        start_sample = int(float(start) * sample_rate)
        end_sample = int(float(end) * sample_rate) if end else len(data)

        trimmed = data[start_sample:end_sample]

        if not output_path:
            base, ext = os.path.splitext(audio_path)
            output_path = f"{base}_trimmed{ext}"

        sf.write(output_path, trimmed, sample_rate)
        logger.info(f"Trimmed audio: {output_path}")
        return output_path

    @keyword("Get Audio RMS Level")
    def get_audio_rms_level(self, audio_path: str) -> float:
        """Get RMS (root mean square) level of audio"""
        if not NUMPY_AVAILABLE or not SOUNDFILE_AVAILABLE:
            raise AssertionError("numpy and soundfile required")

        data, _ = sf.read(audio_path)
        rms = np.sqrt(np.mean(data ** 2))
        return float(rms)

    @keyword("Cleanup Audio Files")
    def cleanup_audio_files(self):
        """Clean up temporary audio files"""
        import shutil
        try:
            shutil.rmtree(self.temp_dir, ignore_errors=True)
            self.temp_dir = tempfile.mkdtemp(prefix="audio_test_")
            logger.info("Audio files cleaned up")
        except Exception as e:
            logger.warning(f"Cleanup error: {e}")
        return True

    @keyword("Convert Audio To WAV")
    def convert_audio_to_wav(self, input_path: str,
                             output_path: str = None) -> str:
        """Convert audio file to WAV format"""
        if not SOUNDFILE_AVAILABLE:
            raise AssertionError("soundfile required")

        if not output_path:
            base = os.path.splitext(input_path)[0]
            output_path = f"{base}.wav"

        data, sample_rate = sf.read(input_path)
        sf.write(output_path, data, sample_rate, format='WAV')

        logger.info(f"Converted to WAV: {output_path}")
        return output_path

    @keyword("Resample Audio")
    def resample_audio(self, audio_path: str, target_rate: str,
                       output_path: str = None) -> str:
        """Resample audio to target sample rate"""
        if not NUMPY_AVAILABLE or not SOUNDFILE_AVAILABLE:
            raise AssertionError("numpy and soundfile required")

        from scipy import signal

        target_sr = int(target_rate)
        data, source_sr = sf.read(audio_path)

        if source_sr != target_sr:
            samples = int(len(data) * target_sr / source_sr)
            data = signal.resample(data, samples)

        if not output_path:
            base, ext = os.path.splitext(audio_path)
            output_path = f"{base}_{target_sr}hz{ext}"

        sf.write(output_path, data, target_sr)
        logger.info(f"Resampled to {target_sr}Hz: {output_path}")
        return output_path
