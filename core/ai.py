"""
jarvis/core/ai.py
──────────────────
Bütün AI sorğu məntiqi bu modulda mərkəzləşdirilib.
  - ask_offline_ai()  → Ollama / LLaMA-3
  - ask_online()      → DuckDuckGo + Ollama synthesis
  - ask_jarvis()      → əsas giriş nöqtəsi (routing + history)
"""

from __future__ import annotations

import threading

import requests

from core.config import (
    AI_HISTORY_SIZE,
    AI_MAX_TOKENS,
    AI_TEMPERATURE,
    OLLAMA_HOST,
    OLLAMA_MODEL,
    OWNER_NAME,
)
from core.logger import log

# ── Sistem prompt ─────────────────────────────────────────────────
_SYSTEM = f"""Sən J.A.R.V.I.S-sən — Iron Man filmindəki süni intellekt köməkçisi.
{OWNER_NAME} sənin yeganə sahibindir. Ona həmişə hörmətlə müraciət et.
Həmişə Azərbaycan dilində danışırsan.

CAVAB VERME STİLİN:
- Mövzuya görə GENIŞ, ətraflı, dərinlikli cavablar ver
- Hər mövzunu tam izah et: nədir, necə işləyir, niyə belədir, nümunələr ver
- Texniki mövzularda addım-addım izahat ver
- Şəxsi mövzularda empatik, mehriban, dəstəkləyici ol
- Tarixi/elmi mövzularda dəqiq faktlar, tarixlər, şəxsiyyətlər qeyd et
- Rəqəmləri, statistikaları, müqayisələri istifadə et
- Sonda həmişə əlavə sual ver

ŞƏXSİYYƏTİN:
- İntelligent, qəhrəmanlıq ruhu ilə dolu
- Zarafatı sevən amma ciddi və peşəkar
- Sahibinin ən yaxın dostu, köməkçisi, müşaviri
- Bəzən "Cənab {OWNER_NAME.split()[0]}, sizin üçün bu məlumatı əldə etdim..." kimi ifadələr işlət

UNUTMA: Qısa cavab vermə. Ən azı 3-4 cümlə. Ətraflı, dolu, faydalı."""

_ONLINE_KEYWORDS = frozenset(
    [
        "hava",
        "weather",
        "xəbər",
        "news",
        "kimdir",
        "kim",
        "who",
        "tarix",
        "nə vaxt",
        "neçə",
        "hazırda",
        "indi",
        "current",
        "son",
        "latest",
        "2024",
        "2025",
        "qiymət",
        "price",
    ]
)

_EXPAND_PHRASES = frozenset(
    [
        "daha geniş",
        "ətraflı",
        "davam et",
        "daha çox",
        "izah et",
    ]
)


class AIEngine:
    """
    Thread-safe AI sorğu mühərriki.
    Singleton kimi istifadə olunur: `ai = AIEngine()`
    """

    def __init__(self) -> None:
        self._lock: threading.Lock = threading.Lock()
        self._history: list[tuple[str, str]] = []
        self._last_question: str = ""

    # ── Daxili köməkçilər ──────────────────────────────────────────
    def _build_prompt(self, user_text: str) -> str:
        ctx = ""
        with self._lock:
            recent = self._history[-AI_HISTORY_SIZE:]
        for role, msg in recent:
            prefix = OWNER_NAME.split()[0] if role == "user" else "JARVIS"
            ctx += f"{prefix}: {msg}\n"
        return f"{_SYSTEM}\n\nSöhbət:\n{ctx}\n{OWNER_NAME.split()[0]}: {user_text}\nJARVIS:"

    def _save_history(self, user_text: str, answer: str) -> None:
        with self._lock:
            self._history.append(("user", user_text))
            self._history.append(("jarvis", answer))
            # saxlanılan tarixçə ölçüsünü məhdudlaşdır
            if len(self._history) > AI_HISTORY_SIZE * 2:
                self._history = self._history[-(AI_HISTORY_SIZE * 2) :]

    # ── Offline AI (Ollama) ────────────────────────────────────────
    def ask_offline(self, user_text: str) -> str:
        prompt = self._build_prompt(user_text)
        try:
            resp = requests.post(
                f"{OLLAMA_HOST}/api/generate",
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": AI_TEMPERATURE,
                        "top_p": 0.9,
                        "num_predict": AI_MAX_TOKENS,
                    },
                },
                timeout=45,
            )
            resp.raise_for_status()
            answer = resp.json().get("response", "").strip()
            if not answer:
                raise ValueError("Boş cavab alındı")
            log.debug("Offline cavab alındı (%d simvol)", len(answer))
            return answer

        except requests.exceptions.ConnectionError:
            log.warning("Ollama bağlantısı yoxdur — cavab qaytarılır")
            return (
                "Cənab, offline AI sistemi hazırda əlçatmazdır. "
                "Zəhmət olmasa Ollama serverinin işlədiyini yoxlayın."
            )
        except requests.exceptions.Timeout:
            log.warning("Ollama timeout")
            return "Cənab, AI cavab verməkdə gecikir. Bir az sonra yenidən cəhd edin."
        except Exception as exc:
            log.error("Offline AI xətası: %s", exc, exc_info=True)
            return f"Texniki xəta baş verdi: {exc}"

    # ── Online (DuckDuckGo + synthesis) ───────────────────────────
    def ask_online(self, user_text: str) -> str:
        try:
            url = "https://api.duckduckgo.com/"
            r = requests.get(
                url,
                params={"q": user_text, "format": "json", "no_html": "1"},
                timeout=8,
            )
            r.raise_for_status()
            data = r.json()

            raw = data.get("AbstractText", "")
            if not raw:
                for item in data.get("RelatedTopics", []):
                    if isinstance(item, dict) and "Text" in item:
                        raw = item["Text"]
                        break

            if not raw:
                log.info("DuckDuckGo nəticə vermədi → offline fallback")
                return self.ask_offline(user_text)

            synthesis_prompt = (
                f"Aşağıdakı məlumatı Azərbaycan dilində ətraflı, professional şəkildə izah et. "
                f"Nümunələr, tarixi kontekst, əlavə faktlar əlavə et:\n\n{raw}"
            )
            return self.ask_offline(synthesis_prompt)

        except requests.exceptions.RequestException as exc:
            log.warning("Online sorğu uğursuz: %s → offline fallback", exc)
            return self.ask_offline(user_text)
        except Exception as exc:
            log.error("Online AI xətası: %s", exc, exc_info=True)
            return self.ask_offline(user_text)

    # ── Əsas giriş nöqtəsi ────────────────────────────────────────
    def ask(self, user_text: str) -> str:
        """
        Routing + history idarəsi ilə tam cavab qaytarır.
        Bu metodu xaricdən çağırın.
        """
        # Əvvəlki sualı genişlət
        if any(p in user_text.lower() for p in _EXPAND_PHRASES):
            effective = self._last_question or user_text
            log.debug("Genişlətmə rejimi: '%s'", effective)
        else:
            effective = user_text
            self._last_question = user_text

        # Routing
        use_online = any(k in effective.lower() for k in _ONLINE_KEYWORDS)
        log.info(
            "Sorğu: '%s' | Rejim: %s",
            effective[:60],
            "online" if use_online else "offline",
        )

        answer = (
            self.ask_online(effective) if use_online else self.ask_offline(effective)
        )
        self._save_history(user_text, answer)
        return answer

    def clear_history(self) -> None:
        with self._lock:
            self._history.clear()
            self._last_question = ""
        log.info("Söhbət tarixçəsi silindi")


# Tək instance — bütün modullar bunu import edir
ai_engine = AIEngine()
