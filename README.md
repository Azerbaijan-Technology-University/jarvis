# J.A.R.V.I.S v3.0
### Just A Rather Very Intelligent System
*Ruslan Şükürlu üçün hazırlanmışdır*

---

## 📁 Layihə Strukturu

```
jarvis/
├── main.py              ← Başlanğıc nöqtəsi
├── requirements.txt     ← Python asılılıqları
├── .env.example         ← Mühit dəyişənləri şablonu
├── .env                 ← Sizin real açarlarınız (git-ə yükləməyin!)
├── jarvis.log           ← Avtomatik yaradılır
│
├── core/
│   ├── config.py        ← Bütün konfiqurasiya
│   ├── logger.py        ← Strukturlaşdırılmış logging
│   ├── ai.py            ← AI sorğu mühərriki (Ollama + DuckDuckGo)
│   └── audio.py         ← TTS (ElevenLabs) + mikrofon dinləmə
│
└── ui/
    └── interface.py     ← Tam animasiyalı Tkinter interfeysi
```

---

## ⚡ Qurulum


### 1. Python asılılıqlarını qurun
```bash
python -m venv .venv

# Windows (Powershell)
./.venv/Scripts/activate

# Linux / macOS
source venv/bin/activate
```

### 2. Python asılılıqlarını qurun
```bash
pip install -r requirements.txt
```

### 3. PyAudio qurun (mikrofon üçün)
```bash
# Windows
pip install pyaudio

# Linux
sudo apt install portaudio19-dev
pip install pyaudio

# macOS
brew install portaudio
pip install pyaudio
```

### 4. Ollama qurun (offline AI üçün)
```bash
# https://ollama.ai/download — saytdan endirin
ollama pull llama3
```

### 5. .env faylı yaradın
```bash
cp .env.example .env
# .env faylını redaktə edin və ElevenLabs açarınızı daxil edin
```

### 6. Başladın
```bash
python main.py
```

---

## 🔐 Təhlükəsizlik

- API açarları `.env` faylında saxlanılır — kodda HEÇ VAXT yazılmır
- `.env` faylını GitHub-a yükləməyin (`.gitignore`-a əlavə edin)
- `.env.example` faylını paylaşmaq təhlükəsizdir

---

## 🎮 İstifadə

| Əməl | Necə |
|------|------|
| Danışmaq | Mikrofona danışın (avtomatik dinləyir) |
| Yazmaq | Sağ paneldə mətn daxil edin |
| Mic söndür/aç | Sol paneldə mic düyməsinə klikləyin |
| Tam ekran çıx | ESC |
| Tam ekran | F11 |

---

## 📊 Arxitektura

```
main.py (JarvisController)
    ├── core/ai.py       → Sorğu routing + context history
    ├── core/audio.py    → TTS speak() + ListenThread
    └── ui/interface.py  → Canvas draw loop + event handling
```

Hər modul müstəqildir — ayrı-ayrılıqda test etmək olar.

---

*JARVIS v3.0 — Middle-level production architecture*
