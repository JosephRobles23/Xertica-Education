import os
import subprocess
from dataclasses import dataclass, field
from typing import Optional, List
from adapters.audio.base import BaseAudioAdapter

try:
    from google.cloud import texttospeech
    from google.cloud.texttospeech_v1 import SynthesizeSpeechRequest
    GOOGLE_TTS_AVAILABLE = True
    _TIMEPOINT_TYPE = getattr(SynthesizeSpeechRequest, 'TimepointType', None)
    _SSML_MARK = getattr(_TIMEPOINT_TYPE, 'SSML_MARK', None) if _TIMEPOINT_TYPE else None
except ImportError:
    texttospeech = None
    SynthesizeSpeechRequest = None
    GOOGLE_TTS_AVAILABLE = False
    _SSML_MARK = None


@dataclass
class TTSResult:
    audio_path: str
    duration_seconds: float
    captions: List[dict] = field(default_factory=list)


class GoogleCloudTTSAdapter(BaseAudioAdapter):
    def __init__(self, credentials_path: Optional[str] = None):
        self.credentials_path = credentials_path or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        self.is_mock = not GOOGLE_TTS_AVAILABLE or (not self.credentials_path and "GOOGLE_APPLICATION_CREDENTIALS" not in os.environ)

        if self.is_mock:
            print("Google Cloud TTS SDK or credentials not found. GoogleCloudTTSAdapter running in MOCK mode.")

    async def text_to_speech(self, text: str, output_path: str) -> float:
        result = await self.text_to_speech_with_timestamps(text, output_path)
        return result.duration_seconds

    def _write_mock_mp3(self, output_path: str, duration: float):
        """Generate a valid silent MP3 of the given duration using FFmpeg."""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono",
            "-t", str(duration),
            "-acodec", "libmp3lame", "-q:a", "4",
            output_path,
        ]
        try:
            subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        except Exception:
            # Last resort: write minimal valid MP3 frame (still better than zeros)
            with open(output_path, "wb") as f:
                f.write(b'\xff\xfb\x90\x00' * 1000)

    async def text_to_speech_with_timestamps(self, text: str, output_path: str) -> TTSResult:
        words_list = text.split()
        if self.is_mock:
            duration = max(1.5, len(words_list) / 2.5)
            self._write_mock_mp3(output_path, duration)
            captions = self._estimate_captions(words_list, duration)
            return TTSResult(audio_path=output_path, duration_seconds=duration, captions=captions)

        try:
            client = texttospeech.TextToSpeechClient()

            ssml_text = "<speak>"
            for i, word in enumerate(words_list):
                ssml_text += f'<mark name="w{i}"/>{word} '
            ssml_text += "</speak>"

            synthesis_input = texttospeech.SynthesisInput(ssml=ssml_text)

            voice = texttospeech.VoiceSelectionParams(
                language_code="es-US",
                name="es-US-Neural2-B"
            )

            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3
            )

            extra_kwargs = {}
            if _SSML_MARK is not None:
                extra_kwargs["enable_time_pointing"] = [_SSML_MARK]

            response = client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config,
                **extra_kwargs
            )

            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, "wb") as out:
                out.write(response.audio_content)

            cmd = ["ffprobe", "-i", output_path, "-show_entries", "format=duration", "-v", "quiet", "-of", "csv=p=0"]
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
            duration = float(result.stdout.strip())

            timepoints = []
            try:
                timepoints = response.timepoints
            except Exception:
                try:
                    timepoints = response._pb.timepoints
                except Exception:
                    pass

            if timepoints and len(timepoints) >= len(words_list):
                captions = self._parse_timepoints(timepoints, words_list)
            else:
                captions = self._estimate_captions(words_list, duration)

            return TTSResult(audio_path=output_path, duration_seconds=duration, captions=captions)

        except Exception as e:
            print(f"Error in Google Cloud TTS synthesis, falling back to mock: {e}")
            words = len(words_list)
            duration = max(1.5, words / 2.5)
            self._write_mock_mp3(output_path, duration)
            captions = self._estimate_captions(words_list, duration)
            return TTSResult(audio_path=output_path, duration_seconds=duration, captions=captions)

    def _parse_timepoints(self, timepoints, words_list: list) -> list:
        captions = []
        for i, tp in enumerate(timepoints):
            word = words_list[i] if i < len(words_list) else ""
            start_ms = int(tp.time_seconds * 1000)
            if i + 1 < len(timepoints):
                end_ms = int(timepoints[i + 1].time_seconds * 1000)
            else:
                avg_word_ms = len(word) * 80 + 200
                end_ms = start_ms + avg_word_ms
            captions.append({"word": word, "startMs": start_ms, "endMs": end_ms})
        return captions

    def _estimate_captions(self, words_list: list, duration: float) -> list:
        captions = []
        words_per_sec = len(words_list) / duration
        for i, word in enumerate(words_list):
            start_ms = int((i / words_per_sec) * 1000)
            end_ms = int(((i + 1) / words_per_sec) * 1000)
            captions.append({"word": word, "startMs": start_ms, "endMs": end_ms})
        return captions
