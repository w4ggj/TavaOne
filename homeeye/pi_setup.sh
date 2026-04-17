#!/bin/bash
# ============================================================
# HomeEye AI Assistant — Raspberry Pi Setup Script
# Run this once on a fresh Pi to install everything
# Usage: bash pi_setup.sh
# W4GGJ / TavaOne.com
# ============================================================

echo "=================================================="
echo "  HomeEye Pi Setup — W4GGJ"
echo "=================================================="

# Update system
echo "[1/8] Updating system..."
sudo apt update -y && sudo apt upgrade -y

# Install system dependencies
echo "[2/8] Installing system packages..."
sudo apt install -y \
    python3-pip \
    python3-venv \
    espeak \
    espeak-data \
    libportaudio2 \
    portaudio19-dev \
    libopencv-dev \
    python3-opencv \
    libatlas-base-dev \
    libjpeg-dev \
    git \
    ffmpeg

# Create virtual environment
echo "[3/8] Creating Python virtual environment..."
python3 -m venv ~/homeeye_env
source ~/homeeye_env/bin/activate

# Install Python packages
echo "[4/8] Installing Python packages..."
pip install --upgrade pip
pip install \
    anthropic \
    sounddevice \
    numpy \
    SpeechRecognition \
    opencv-python-headless \
    google-api-python-client \
    google-auth-oauthlib \
    pytz \
    requests

# Optional: face recognition (slower on Pi 3, fine on Pi 4/5)
echo "[5/8] Installing face recognition (this may take a while)..."
pip install cmake
pip install dlib || echo "dlib failed — face recognition will use OpenCV fallback"
pip install face-recognition || echo "face-recognition skipped — using OpenCV"

# Set up HomeEye directory
echo "[6/8] Setting up HomeEye directory..."
mkdir -p ~/HomeEye
mkdir -p ~/HomeEye/faces

# Copy files (assumes script is run from the HomeEye folder)
if [ -f "assistant_pi.py" ]; then
    cp *.py ~/HomeEye/
    cp *.json ~/HomeEye/ 2>/dev/null || true
    echo "Files copied to ~/HomeEye"
else
    echo "Run this script from your HomeEye folder!"
fi

# Create startup service
echo "[7/8] Creating systemd service for auto-start..."
cat > /tmp/homeeye.service << 'SERVICE'
[Unit]
Description=HomeEye AI Assistant
After=network.target sound.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/HomeEye
Environment=PATH=/home/pi/homeeye_env/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
ExecStart=/home/pi/homeeye_env/bin/python assistant_pi.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
SERVICE

sudo cp /tmp/homeeye.service /etc/systemd/system/homeeye.service
sudo systemctl daemon-reload
sudo systemctl enable homeeye.service
echo "Service installed — HomeEye will start on boot"

# Test espeak
echo "[8/8] Testing voice output..."
espeak "HomeEye installation complete. W4GGJ is online."

echo ""
echo "=================================================="
echo "  Setup complete!"
echo "=================================================="
echo ""
echo "Next steps:"
echo "1. Copy config_pi.example.json to config_pi.json"
echo "2. Add your Anthropic API key to config_pi.json"
echo "3. Find your mic index: python3 -c \"import sounddevice as sd; print(sd.query_devices())\""
echo "4. Enroll your face: python3 face_setup.py"
echo "5. Test: python3 assistant_pi.py"
echo "6. Enable auto-start: sudo systemctl start homeeye"
echo ""
echo "73 de W4GGJ"
