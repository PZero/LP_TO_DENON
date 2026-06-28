#!/bin/bash
# Disable screen blanking / screensaver / power management
xset s off
xset s noblank
xset -dpms

# Ensure chromium preferences exist and clean up crash state
mkdir -p ~/.config/chromium/Default
PREFS_FILE="$HOME/.config/chromium/Default/Preferences"
if [ -f "$PREFS_FILE" ]; then
    sed -i 's/"exited_cleanly":false/"exited_cleanly":true/g' "$PREFS_FILE"
    sed -i 's/"exit_type":"Crashed"/"exit_type":"Normal"/g' "$PREFS_FILE"
fi

# Start Chromium in Kiosk mode pointing to our local Flask monitoring app
chromium-browser \
    --noerrdialogs \
    --disable-infobars \
    --kiosk \
    --ozone-platform=x11 \
    --autoplay-policy=no-user-gesture-required \
    http://localhost:5000
