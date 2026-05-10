"""
jarvis/main.py
───────────────
J.A.R.V.I.S v3.0 — Əsas başlanğıc nöqtəsi.

Bu fayl bütün modulları birləşdirir:
  core/config.py  — konfiqurasiya
  core/logger.py  — logging
  core/ai.py      — AI sorğular
  core/audio.py   — TTS + mikrofon
  ui/interface.py — animasiyalı UI

İstifadə:
  python main.py

.env faylı lazımdır (bax: .env.example)
"""

from __future__ import annotations

import atexit
import queue
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Optional

# ── Layihə kökünü sys.path-a əlavə et ──
sys.path.insert(0, str(Path(__file__).resolve().parent))

from core.ai import ai_engine
from core.audio import ListenThread, speak
from core.config import OWNER_NAME, validate
from core.logger import log
from ui.interface import JarvisUI


# ═══════════════════════════════════════════════════════════════════
#   OLLAMA MENECERI
# ═══════════════════════════════════════════════════════════════════
class OllamaManager:
    def __init__(self) -> None:
        self._proc: Optional[subprocess.Popen] = None

    def start(self) -> bool:
        try:
            self._proc = subprocess.Popen(
                ["ollama", "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            time.sleep(1.5)  # serverın ayağa qalxmasını gözlə
            log.info("Ollama server başladıldı (PID: %d)", self._proc.pid)
            return True
        except FileNotFoundError:
            log.warning("'ollama' əmri tapılmadı — offline AI işləməyəcək")
            return False
        except Exception as exc:
            log.error("Ollama start xətası: %s", exc)
            return False

    def stop(self) -> None:
        if self._proc and self._proc.poll() is None:
            self._proc.terminate()
            log.info("Ollama server dayandırıldı")


# ═══════════════════════════════════════════════════════════════════
#   JARVIS CONTROLLER
# ═══════════════════════════════════════════════════════════════════
class JarvisController:
    """
    UI, Audio, AI modullarını birləşdirir.
    Bütün hadisə axını burada idarə olunur.
    """

    def __init__(self) -> None:
        self.status_queue: queue.Queue = queue.Queue()
        self.chat_queue: queue.Queue = queue.Queue()
        self.mic_active: bool = True
        self._speaking: bool = False
        self._thinking: bool = False
        self._listen_thread: Optional[ListenThread] = None

    # ── Mikrofon toggle ───────────────────────────────────────────
    def toggle_mic(self) -> None:
        self.mic_active = not self.mic_active
        self.status_queue.put("listening" if self.mic_active else "muted")
        log.info("Mikrofon: %s", "açıq" if self.mic_active else "bağlı")

    # ── Dinləmə bloklama şərti ────────────────────────────────────
    def _is_blocked(self) -> bool:
        return self._speaking or self._thinking or not self.mic_active

    # ── Mətn (mikrofon + yazı) emalı ─────────────────────────────
    def _process_input(self, text: str) -> None:
        """Hər iki giriş növü üçün ortaq emal."""
        self._thinking = True
        self.status_queue.put("thinking")
        self.chat_queue.put(("user", text))

        try:
            answer = ai_engine.ask(text)
        except Exception as exc:
            log.error("AI sorğu xətası: %s", exc, exc_info=True)
            answer = f"Bağışlayın, texniki xəta baş verdi: {exc}"
        finally:
            self._thinking = False

        self.chat_queue.put(("jarvis", answer))
        self._speak_answer(answer)

    def _speak_answer(self, text: str) -> None:
        self._speaking = True

        def on_start():
            self.status_queue.put("speaking")

        def on_finish():
            self._speaking = False
            self.status_queue.put("ready")

        # TTS bloklanıcıdır — ayrı thread
        threading.Thread(
            target=speak,
            args=(text,),
            kwargs={"on_start": on_start, "on_finish": on_finish},
            daemon=True,
            name="JarvisSpeakThread",
        ).start()

    # ── Text input (UI-dan) ───────────────────────────────────────
    def on_text_input(self, text: str) -> None:
        threading.Thread(
            target=self._process_input,
            args=(text,),
            daemon=True,
            name="JarvisProcessThread",
        ).start()

    # ── Mikrofon giriş ────────────────────────────────────────────
    def on_mic_text(self, text: str) -> None:
        self._process_input(text)  # ListenThread-dən gəlir, artıq öz thread-indədir

    # ── Dinləmə başlat ────────────────────────────────────────────
    def start_listening(self) -> None:
        self._listen_thread = ListenThread(
            on_text=self.on_mic_text,
            is_blocked=self._is_blocked,  # lambda yox, birbaşa metod
            on_status=self.status_queue.put,
        )
        # ListenThread.is_blocked mic_active_ref üçün self lazımdır — patch
        self._listen_thread._is_blocked = self._is_blocked  # type: ignore
        self._listen_thread.start()
        log.info("Dinləmə thread-i başladıldı")

    def stop(self) -> None:
        if self._listen_thread:
            self._listen_thread.stop()


# ═══════════════════════════════════════════════════════════════════
#   BAŞLANĞIC
# ═══════════════════════════════════════════════════════════════════
def main() -> None:
    print()
    print("═" * 62)
    print("  J.A.R.V.I.S  v3.0")
    print(f"  {OWNER_NAME} üçün hazırlanmışdır")
    print("═" * 62)
    print()

    # Konfiqurasiya yoxlaması
    warnings = validate()
    for w in warnings:
        log.warning("CONFIG: %s", w)

    # Ollama
    ollama = OllamaManager()
    ollama_ok = ollama.start()
    atexit.register(ollama.stop)
    if not ollama_ok:
        log.warning("Ollama işlək deyil — AI cavablar məhdud olacaq")

    # Controller
    ctrl = JarvisController()
    atexit.register(ctrl.stop)

    # UI
    ui = JarvisUI(
        on_text_input=ctrl.on_text_input,
        on_mic_toggle=ctrl.toggle_mic,
        status_queue=ctrl.status_queue,
        chat_queue=ctrl.chat_queue,
        mic_active_ref=lambda: ctrl.mic_active,
    )

    # Dinləməni başlat
    ctrl.start_listening()

    log.info("JARVIS hazır. Sahibi: %s", OWNER_NAME)
    ui.run()


if __name__ == "__main__":
    main()
