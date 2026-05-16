"""
jarvis/core/audio.py
─────────────────────
 Bütün audio məntiqi:
  - speak()          → ElevenLabs TTS
  - ListenThread     → mikrofondan real-time dinləmə
"""

from __future__ import annotations

import os
import re
import tempfile
import threading
from typing import Callable, Optional

import pygame
import speech_recognition as sr
from elevenlabs import VoiceSettings
from elevenlabs.client import ElevenLabs

from core.config import (
    AUDIO_SIMILARITY_BOOST,
    AUDIO_STABILITY,
    AUDIO_STYLE,
    ELEVENLABS_API_KEY,
    ELEVENLABS_VOICE,
    MIC_ENERGY_THRESHOLD,
    MIC_LANGUAGES,
    MIC_PAUSE_THRESHOLD,
    MIC_PHRASE_LIMIT,
    MIC_TIMEOUT,
)
from core.logger import log

# ── pygame audio init ──────────────────────────────────────────────
try:
    pygame.mixer.pre_init(44100, -16, 2, 512)
    pygame.mixer.init()
    log.info("Audio sistemi hazır (pygame)")
except Exception as exc:
    log.error("pygame audio init xətası: %s", exc)

# ── ElevenLabs client ─────────────────────────────────────────────
_el_client: Optional[ElevenLabs] = None
_voice_id_cache: Optional[str] = None
_voice_lock = threading.Lock()

if ELEVENLABS_API_KEY:
    try:
        _el_client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
        log.info("ElevenLabs client hazır")
    except Exception as exc:
        log.error("ElevenLabs init xətası: %s", exc)
else:
    log.warning("ELEVENLABS_API_KEY tapılmadı — TTS deaktivdir")


def _get_voice_id() -> str:
    global _voice_id_cache
    with _voice_lock:
        if _voice_id_cache:
            return _voice_id_cache
        if not _el_client:
            return "pNInz6obpgDQGcFmaJgB"  # Adam default
        try:
            voices = _el_client.voices.get_all()
            for v in voices.voices:
                if v.name and v.name.lower() == ELEVENLABS_VOICE.lower():
                    _voice_id_cache = v.voice_id
                    log.debug("Voice ID tapıldı: %s (%s)", v.name, v.voice_id)
                    return _voice_id_cache
            # tapılmadısa birincini götür
            _voice_id_cache = voices.voices[0].voice_id
            return _voice_id_cache
        except Exception as exc:
            log.warning("Voice ID alınamadı: %s — default istifadə edilir", exc)
            _voice_id_cache = "pNInz6obpgDQGcFmaJgB"
            return _voice_id_cache


# ── TTS ───────────────────────────────────────────────────────────
_CLEAN_RE = re.compile(r"[*_`#►◉◈◎●✕]")


def speak(
    text: str,
    on_start: Optional[Callable] = None,
    on_finish: Optional[Callable] = None,
) -> None:
    """
    Mətni ElevenLabs ilə sintez edib çalır.
    on_start / on_finish callback-ları status yeniləmək üçündür.
    Bloklayıcıdır — thread içində çağırın.
    """
    if not _el_client:
        log.warning("TTS deaktiv — API key yoxdur")
        if on_finish:
            on_finish()
        return

    clean = _CLEAN_RE.sub("", text).strip()
    if not clean:
        if on_finish:
            on_finish()
        return

    if on_start:
        on_start()

    tmp_path: Optional[str] = None
    try:
        vid = _get_voice_id()
        audio_gen = _el_client.text_to_speech.convert(
            voice_id=vid,
            text=clean,
            model_id="eleven_multilingual_v2",
            voice_settings=VoiceSettings(
                stability=AUDIO_STABILITY,
                similarity_boost=AUDIO_SIMILARITY_BOOST,
                style=AUDIO_STYLE,
                use_speaker_boost=True,
            ),
        )

        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
            for chunk in audio_gen:
                if chunk:
                    f.write(chunk)
            tmp_path = f.name

        size = os.path.getsize(tmp_path)
        if size == 0:
            raise ValueError("Boş audio faylı sintez edildi")

        log.debug("TTS faylı yaradıldı: %s (%d bayt)", tmp_path, size)

        pygame.mixer.music.load(tmp_path)
        pygame.mixer.music.set_volume(1.0)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            pygame.time.wait(40)
        pygame.mixer.music.unload()
        log.debug("TTS çalındı: %d simvol", len(clean))

    except Exception as exc:
        log.error("TTS xətası: %s", exc, exc_info=True)
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
        if on_finish:
            on_finish()


# ── Mikrofon dinləmə ──────────────────────────────────────────────
class ListenThread(threading.Thread):
    """
    Arxa planda mikrofondan danışığı dinləyir.
    Tanınan mətn `on_text(text)` callback-ına göndərilir.
    `is_blocked()` True qaytaranda dinləməyi dayandırır.
    """

    def __init__(
        self,
        on_text: Callable[[str], None],
        is_blocked: Callable[[], bool],
        on_status: Callable[[str], None],
    ) -> None:
        super().__init__(daemon=True, name="JarvisListenThread")
        self._on_text = on_text
        self._is_blocked = is_blocked
        self._on_status = on_status
        self._stop_event = threading.Event()

    def stop(self) -> None:
        self._stop_event.set()

    def run(self) -> None:
        recognizer = sr.Recognizer()
        recognizer.energy_threshold = MIC_ENERGY_THRESHOLD
        recognizer.dynamic_energy_threshold = True
        recognizer.pause_threshold = MIC_PAUSE_THRESHOLD
        recognizer.non_speaking_duration = 0.4

        try:
            mic = sr.Microphone()
        except Exception as exc:
            log.error("Mikrofon açıla bilmədi: %s", exc)
            self._on_status("error")
            return

        with mic as source:
            log.info("Ambient səs kalibrasyonu başlayır...")
            recognizer.adjust_for_ambient_noise(source, duration=1.5)
            log.info(
                "Mikrofon hazır (energy threshold: %d)", recognizer.energy_threshold
            )
            self._on_status("ready")

            while not self._stop_event.is_set():
                if self._is_blocked():
                    self._on_status(
                        "muted"
                        if not self._is_blocked.__self__.mic_active  # type: ignore
                        else "busy"
                    )
                    import time
                    import time as t

                    t.sleep(0.15)
                    continue

                try:
                    self._on_status("listening")
                    audio = recognizer.listen(
                        source,
                        timeout=MIC_TIMEOUT,
                        phrase_time_limit=MIC_PHRASE_LIMIT,
                    )
                    self._on_status("thinking")

                    text = self._recognize(recognizer, audio)
                    if text:
                        log.info("Tanındı: '%s'", text)
                        self._on_text(text)
                    else:
                        self._on_status("ready")

                except sr.WaitTimeoutError:
                    self._on_status("ready")
                except Exception as exc:
                    log.warning("Dinləmə döngüsü xətası: %s", exc)
                    import time

                    time.sleep(0.5)
                    self._on_status("ready")

    @staticmethod
    def _recognize(recognizer: sr.Recognizer, audio: sr.AudioData) -> Optional[str]:
        for lang in MIC_LANGUAGES:
            try:
                # TODO: Fix unknown function
                text = recognizer.recognize_google(audio, language=lang)
                if text and text.strip():
                    return text.strip()
            except sr.UnknownValueError:
                continue
            except sr.RequestError as exc:
                log.warning("Google STT xətası (%s): %s", lang, exc)
                break
        return None
