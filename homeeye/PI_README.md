# HomeEye AI Assistant — Raspberry Pi Edition
## W4GGJ / TavaOne.com

---

## Hardware Required

| Item | Recommended | Min Spec |
|------|-------------|----------|
| Raspberry Pi | Pi 5 4GB | Pi 4 4GB |
| MicroSD | 32GB Class 10 | 16GB |
| USB Microphone | Fifine K669 | Any USB mic |
| Speaker | USB or 3.5mm | Any |
| Webcam | Logitech C270 | Any USB cam |
| Power Supply | Official Pi PSU | 5V 3A |

---

## Quick Install

```bash
# On your Pi, open terminal and run:
git clone https://github.com/w4ggj/homeeye  # or copy files manually
cd HomeEye
bash pi_setup.sh
```

---

## Manual Install

```bash
# System packages
sudo apt update
sudo apt install -y espeak libportaudio2 portaudio19-dev python3-pip python3-venv

# Python environment
python3 -m venv ~/homeeye_env
source ~/homeeye_env/bin/activate
pip install anthropic sounddevice numpy SpeechRecognition opencv-python-headless google-api-python-client google-auth-oauthlib pytz

# Run
python3 assistant_pi.py
```

---

## Configuration

Copy `config_pi.example.json` to `config_pi.json` and fill in:

```json
{
  "anthropic_api_key": "YOUR_KEY_HERE",
  "microphone_index": null,
  "camera_index": 0,
  "weather_location": "Tampa Bay, FL"
}
```

Find your microphone index:
```bash
python3 -c "import sounddevice as sd; print(sd.query_devices())"
```

---

## Differences from Windows Version

| Feature | Windows | Raspberry Pi |
|---------|---------|--------------|
| TTS Engine | pyttsx3 | espeak |
| WOPR Visualizer | Full WOPR display | Text-only (optional) |
| Face Recognition | OpenCV | OpenCV |
| Sound Effects | sounddevice tones | sounddevice tones |
| Auto-start | Task Scheduler | systemd service |
| SmartThings | ✅ | ✅ |
| Google Calendar | ✅ | ✅ |
| Traffic | ✅ | ✅ |
| Weather | ✅ | ✅ |
| Ham Radio | ✅ | ✅ |

---

## Auto-Start on Boot

```bash
sudo systemctl enable homeeye
sudo systemctl start homeeye

# Check status
sudo systemctl status homeeye

# View logs
journalctl -u homeeye -f
```

---

## Face Enrollment

```bash
python3 face_setup.py
```

---

## Voice Commands

All the same commands as the Windows version work on Pi:
- "Hey Claude, [question]"
- "Good morning"
- "Turn on/off [device]"
- "What's the weather?"
- "What's the traffic?"
- "What's on my calendar?"
- "Band conditions"
- "Check the DX cluster"
- "Goodbye"

---

## Performance Tips

- **Pi 5** runs everything smoothly
- **Pi 4** works well — face recognition may take 2-3 seconds
- **Pi 3** — disable face recognition, use voice only
- Close unused apps to free RAM
- Use a fast SD card (Class 10 / A1 rated)
- Heatsink recommended for sustained use

---

73 de W4GGJ — TavaOne.com
