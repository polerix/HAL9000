#!/bin/bash
# ===========================================================================
# HAL 9000 Viewscreen – Raspberry Pi 3 Setup Script
# ===========================================================================
# Run this script on a fresh Raspberry Pi OS installation:
#   chmod +x setup_pi.sh && sudo ./setup_pi.sh
# ===========================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
USER_HOME="/home/pi"
SERVICE_NAME="hal9000-viewscreen"

echo "============================================"
echo "  HAL 9000 Viewscreen – Setup"
echo "============================================"

# ---------------------------------------------------------------------------
# 1. System packages
# ---------------------------------------------------------------------------
echo "[1/6] Installing system packages..."
apt-get update -qq
apt-get install -y -qq \
    python3 \
    python3-pip \
    python3-pygame \
    mpv \
    fonts-freefont-ttf \
    > /dev/null 2>&1

echo "  ✓ python3, pygame, mpv installed"

# ---------------------------------------------------------------------------
# 2. Python dependencies
# ---------------------------------------------------------------------------
echo "[2/6] Installing Python dependencies..."
pip3 install -r "${SCRIPT_DIR}/requirements.txt" --quiet 2>/dev/null || \
    pip3 install -r "${SCRIPT_DIR}/requirements.txt" --quiet --break-system-packages 2>/dev/null || \
    echo "  ⚠ pip install skipped (system pygame should suffice)"

echo "  ✓ Python dependencies ready"

# ---------------------------------------------------------------------------
# 3. Install Eurostile KFB fonts
# ---------------------------------------------------------------------------
echo "[3/6] Installing Eurostile KFB fonts..."
FONT_SRC="${SCRIPT_DIR}/Fonts/Eurostile-Font-main/Eurostile KFB (Self-created)"
FONT_DEST="/usr/local/share/fonts/eurostile-kfb"

if [ -d "$FONT_SRC" ]; then
    mkdir -p "$FONT_DEST"
    cp "$FONT_SRC"/*.ttf "$FONT_DEST/" 2>/dev/null || true
    fc-cache -f -s > /dev/null 2>&1
    echo "  ✓ Eurostile KFB fonts installed to ${FONT_DEST}"
else
    echo "  ⚠ Font directory not found: ${FONT_SRC}"
fi

# ---------------------------------------------------------------------------
# 4. Configure HDMI for 600×1024 display
# ---------------------------------------------------------------------------
echo "[4/6] Configuring HDMI output..."
CONFIG_FILE="/boot/config.txt"
# Newer Pi OS uses /boot/firmware/config.txt
[ -f "/boot/firmware/config.txt" ] && CONFIG_FILE="/boot/firmware/config.txt"

# Backup
cp "$CONFIG_FILE" "${CONFIG_FILE}.bak.$(date +%s)"

# Add HAL9000 display configuration if not already present
if ! grep -q "# HAL 9000 Viewscreen" "$CONFIG_FILE"; then
    cat >> "$CONFIG_FILE" << 'HDMI_CONFIG'

# HAL 9000 Viewscreen – HDMI Configuration
# 600×1024 portrait display (7" HDMI monitor)
hdmi_group=2
hdmi_mode=87
hdmi_cvt=1024 600 60 6 0 0 0
display_hdmi_rotate=1
hdmi_force_hotplug=1
disable_overscan=1
HDMI_CONFIG
    echo "  ✓ HDMI config added (1024×600 → rotated to 600×1024 portrait)"
else
    echo "  ✓ HDMI config already present"
fi

# ---------------------------------------------------------------------------
# 5. Disable screen blanking / DPMS
# ---------------------------------------------------------------------------
echo "[5/6] Disabling screen blanking..."

# Console blanking
if ! grep -q "consoleblank=0" "$CONFIG_FILE"; then
    # Add to kernel cmdline
    CMDLINE="/boot/cmdline.txt"
    [ -f "/boot/firmware/cmdline.txt" ] && CMDLINE="/boot/firmware/cmdline.txt"
    if ! grep -q "consoleblank=0" "$CMDLINE"; then
        sed -i 's/$/ consoleblank=0/' "$CMDLINE"
    fi
fi

echo "  ✓ Screen blanking disabled"

# ---------------------------------------------------------------------------
# 6. Install systemd service
# ---------------------------------------------------------------------------
echo "[6/6] Installing systemd service..."

cp "${SCRIPT_DIR}/hal9000-viewscreen.service" "/etc/systemd/system/${SERVICE_NAME}.service"

# Update the ExecStart path in the service file
sed -i "s|INSTALL_DIR|${SCRIPT_DIR}|g" "/etc/systemd/system/${SERVICE_NAME}.service"

systemctl daemon-reload
systemctl enable "${SERVICE_NAME}.service"

echo "  ✓ Service installed and enabled"

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
echo ""
echo "============================================"
echo "  Setup complete!"
echo ""
echo "  Start now:     sudo systemctl start ${SERVICE_NAME}"
echo "  View logs:     journalctl -u ${SERVICE_NAME} -f"
echo "  Stop:          sudo systemctl stop ${SERVICE_NAME}"
echo ""
echo "  A reboot is recommended for HDMI changes."
echo "  Run: sudo reboot"
echo "============================================"
