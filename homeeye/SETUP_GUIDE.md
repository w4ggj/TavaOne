# HomeEye AI Assistant — Setup Guide
## Built for W4GGJ / Joe

---

## 🛒 Shopping List (Recommended Hardware)

| Item | Notes | Est. Cost |
|------|-------|-----------|
| **Mini PC / Dedicated PC** | Any Windows PC with 8GB+ RAM. An old desktop works great. | $0–$300 |
| **Webcam** | Logitech C920 or C270 — reliable, good low-light | $30–$80 |
| **USB Microphone** | Blue Snowball iCE or Fifine K669 | $20–$50 |
| **Speakers** | Any USB or 3.5mm speakers | $15–$40 |

**Total budget estimate: $65–$470** (depending on what you already own)

---

## 📋 Prerequisites

- Windows 10 or 11 (works on Linux too with minor tweaks)
- Python 3.10 or newer → https://www.python.org/downloads/
  - ✅ Check "Add Python to PATH" during install
- An Anthropic API key → https://console.anthropic.com

---

## 🚀 Step-by-Step Installation

### Step 1 — Install Python
Download from https://www.python.org/downloads/ and install.
**Important:** Check the box that says "Add Python to PATH".

### Step 2 — Copy the HomeEye folder
Put the entire `vision-assistant` folder somewhere on your PC, for example:
```
C:\HomeEye\
```

### Step 3 — Open a Command Prompt in that folder
- Press `Win + R`, type `cmd`, press Enter
- Type: `cd C:\HomeEye` and press Enter

### Step 4 — Install dependencies
```
pip install -r requirements.txt
```
> If PyAudio fails to install, download the correct .whl from:
> https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio
> Then run: `pip install PyAudio‑0.2.14‑cp311‑cp311‑win_amd64.whl`

### Step 5 — Create your config file
- Copy `config.example.json` → rename it to `config.json`
- Open `config.json` in Notepad
- Fill in your `anthropic_api_key`
- Set `linked_drive_path` to any folder you want it to read files from
  - Example: `"C:/Users/Joe/Documents"`

### Step 6 — Test your webcam index
By default `camera_index` is `0` (first webcam). If you have multiple cameras,
try `1` or `2`. You can test with:
```
python -c "import cv2; cap=cv2.VideoCapture(0); print(cap.isOpened()); cap.release()"
```

### Step 7 — Run HomeEye!
Double-click `start_homeeye.bat` — or from command prompt:
```
python assistant.py
```

---

## 🎙️ How to Use It

HomeEye listens for a **wake word** before responding.

Default wake words: **"hey home"**, **"homeeye"**, **"computer"**

### Example commands:
| Say... | What happens |
|--------|-------------|
| "Hey home, what am I wearing?" | Takes webcam photo, describes your outfit |
| "Hey home, what's in my room?" | Describes your surroundings |
| "Hey home, check my files for anything about radio" | Reads your linked drive |
| "Hey home, what's the weather like outside?" | Answers from Claude's knowledge |
| "Hey home, good morning" | Greets you conversationally |
| "Goodbye" | Shuts down HomeEye |

---

## ⚙️ Config Options Explained

| Setting | What it does |
|---------|-------------|
| `anthropic_api_key` | Your Anthropic API key (required) |
| `wake_words` | Words that activate the assistant |
| `always_on` | If `true`, responds to everything without a wake word |
| `camera_index` | Which webcam to use (0 = first) |
| `microphone_index` | Which mic to use (null = default system mic) |
| `linked_drive_path` | Folder HomeEye can read files from |
| `use_whisper` | Use local Whisper AI instead of Google for speech (no internet needed) |
| `tts_speed` | How fast the voice speaks (default 175) |
| `max_history_turns` | How many conversation turns it remembers |

---

## 💰 API Cost Estimate

- Text-only question: ~$0.0001 per question (basically free)
- Question with webcam photo: ~$0.001–$0.003 per question
- 100 visual questions/day ≈ ~$0.10–$0.30/day → ~$3–$9/month

Since images are only sent when you ask visual questions, costs stay very low.

---

## 🔧 Troubleshooting

**"No module named X"**
→ Run `pip install -r requirements.txt` again

**PyAudio install fails**
→ Download pre-built wheel from https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio

**Microphone not working**
→ Make sure Windows has microphone access enabled (Settings → Privacy → Microphone)

**Webcam not opening**
→ Try `camera_index: 1` in config.json

**Speech not being recognized**
→ Speak clearly, check your mic in Windows Sound settings

**API errors**
→ Check your API key in config.json. Make sure you have credits at console.anthropic.com

---

## 🔄 Optional: Run at Windows Startup

1. Press `Win + R`, type `shell:startup`, press Enter
2. Create a shortcut to `start_homeeye.bat` in that folder
3. HomeEye will start automatically when Windows boots

---

## 📞 Need Help?
Bring this guide and any error messages to Claude at claude.ai and ask for help!
