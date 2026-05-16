"""
jarvis/core/config.py
─────────────────────
Bütün konfiqurasiya mərkəzləşdirilmiş bu modulda saxlanılır.
API açarları .env faylından oxunur — kodda heç vaxt yazılmır.
"""

import logging
import os
from pathlib import Path

from dotenv import load_dotenv

# .env faylını yüklə (layihə kökündən)
_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_ROOT / ".env")


# ── ElevenLabs ────────────────────────────────────────────────────
ELEVENLABS_API_KEY: str = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE: str = os.getenv("ELEVENLABS_VOICE", "Adam")

# ── Ollama ────────────────────────────────────────────────────────
OLLAMA_HOST: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3")

# ── Sahib ─────────────────────────────────────────────────────────
OWNER_NAME: str = os.getenv("OWNER_NAME", "Ruslan Şükürlu")

# ── AI parametrləri ───────────────────────────────────────────────
AI_TEMPERATURE: float = 0.72
AI_MAX_TOKENS: int = 650
AI_HISTORY_SIZE: int = 12  # saxlanılan son mesaj sayı

# ── Səs ───────────────────────────────────────────────────────────
AUDIO_STABILITY: float = 0.45
AUDIO_SIMILARITY_BOOST: float = 0.85
AUDIO_STYLE: float = 0.25

# ── Mikrofon ──────────────────────────────────────────────────────
MIC_ENERGY_THRESHOLD: int = 250
MIC_PAUSE_THRESHOLD: float = 0.8
MIC_PHRASE_LIMIT: int = 20
MIC_TIMEOUT: int = 6
MIC_LANGUAGES: list[str] = ["az-AZ", "tr-TR"]

# ── UI ────────────────────────────────────────────────────────────
UI_FPS: int = 30  # frame/saniyə
UI_PARTICLES: int = 80

# ── Logging ───────────────────────────────────────────────────────
LOG_LEVEL: int = logging.DEBUG
LOG_FILE: Path = _ROOT / "jarvis.log"


# ── Validation ────────────────────────────────────────────────────
def validate() -> list[str]:
    """Kritik konfiqurasiyaları yoxlayır, çatışmayan dəyərləri qaytarır."""
    warnings = []
    if not ELEVENLABS_API_KEY:
        warnings.append(
            "ELEVENLABS_API_KEY tapılmadı — .env faylını yoxlayın. "
            "Səs çıxışı işləməyəcək."
        )
    if not OLLAMA_MODEL:
        warnings.append("OLLAMA_MODEL boşdur — default 'llama3' istifadə edilir.")
    return warnings
