#!/bin/bash

# LP to Denon Bridge & Kiosk Setup Script
# Must be run with sudo

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== LP to Denon Bridge Setup ===${NC}"

# 1. Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Errore: Questo script deve essere eseguito con sudo.${NC}"
    exit 1
fi

# Determine the actual user who invoked sudo
REAL_USER=${SUDO_USER:-$(logname)}
if [ -z "$REAL_USER" ] || [ "$REAL_USER" = "root" ]; then
    echo -e "${YELLOW}Attenzione: Impossibile identificare l'utente non-root. Verrà utilizzato 'pi' come default.${NC}"
    REAL_USER="pi"
fi

echo -e "${BLUE}Utente principale rilevato: ${GREEN}$REAL_USER${NC}"

# 2. Install dependencies
echo -e "${BLUE}1. Installazione pacchetti di sistema (APT)...${NC}"
apt update

# PipeWire and Audio dependencies
apt install -y pipewire pipewire-pulse wireplumber bluez bluez-tools cec-utils

# Graphics/Kiosk dependencies
apt install -y xserver-xorg xinit chromium-browser

# Python dependencies
apt install -y python3 python3-pip python3-flask python3-dbus python3-gi

# 3. Create directory structure
echo -e "${BLUE}2. Creazione cartelle di sistema...${NC}"
INSTALL_DIR="/usr/local/share/lp_to_denon"
mkdir -p "$INSTALL_DIR/sounds"
mkdir -p "$INSTALL_DIR/ui/templates"
mkdir -p "$INSTALL_DIR/ui/static"

# 4. Copy source files
echo -e "${BLUE}3. Copia dei file sorgenti...${NC}"
cp src/bridge_manager.py /usr/local/bin/lp_bridge_manager.py
cp src/cec_monitor.py /usr/local/bin/lp_cec_monitor.py
cp src/ui/app.py /usr/local/bin/lp_webui.py
cp src/ui/kiosk_start.sh /usr/local/bin/lp_kiosk_start.sh

cp src/ui/templates/index.html "$INSTALL_DIR/ui/templates/"
cp src/ui/static/style.css "$INSTALL_DIR/ui/static/"

chmod +x /usr/local/bin/lp_bridge_manager.py
chmod +x /usr/local/bin/lp_cec_monitor.py
chmod +x /usr/local/bin/lp_webui.py
chmod +x /usr/local/bin/lp_kiosk_start.sh

# 5. Generate chime WAV files
echo -e "${BLUE}4. Generazione file audio di chime...${NC}"
python3 src/generate_chimes.py "$INSTALL_DIR/sounds"

# 6. Configure Bluetooth Class of Device (CoD)
# Setting CoD to look like a Wearable Headset/Headphone (Class = 0x200414 or 0x200418 for HiFi Audio)
# so the turntable's Bluetooth scanner sees the RPi as a valid audio sink.
echo -e "${BLUE}5. Configurazione Bluetooth (Class of Device)...${NC}"
MAIN_CONF="/etc/bluetooth/main.conf"
if [ -f "$MAIN_CONF" ]; then
    # Backup
    cp "$MAIN_CONF" "$MAIN_CONF.bak"
    
    # Configure Class
    if grep -q "^#*Class =" "$MAIN_CONF"; then
        sed -i 's/^#*Class =.*/Class = 0x200414/' "$MAIN_CONF"
    else
        echo "Class = 0x200414" >> "$MAIN_CONF"
    fi
    
    # Configure Always Discoverable
    if grep -q "^#*DiscoverableTimeout =" "$MAIN_CONF"; then
        sed -i 's/^#*DiscoverableTimeout =.*/DiscoverableTimeout = 0/' "$MAIN_CONF"
    else
        echo "DiscoverableTimeout = 0" >> "$MAIN_CONF"
    fi
    
    echo -e "${GREEN}Bluetooth configurato correttamente come Headphone (Class: 0x200414)${NC}"
    systemctl restart bluetooth
else
    echo -e "${YELLOW}File /etc/bluetooth/main.conf non trovato. Assicurati che BlueZ sia installato.${NC}"
fi

# 7. Configure User Linger (Required for headless PipeWire/User services)
echo -e "${BLUE}6. Abilitazione Linger per l'utente $REAL_USER...${NC}"
loginctl enable-linger "$REAL_USER"

# 8. Configure Systemd services
echo -e "${BLUE}7. Configurazione dei servizi Systemd...${NC}"
SERVICES=("lp-bridge.service" "lp-cec.service" "lp-webui.service" "lp-kiosk.service")

for service in "${SERVICES[@]}"; do
    dest="/etc/systemd/system/$service"
    echo "Installing systemd service: $service -> $dest"
    
    # Replace @USER@ with the actual user in service files
    sed "s/@USER@/$REAL_USER/g" "config/systemd/$service" > "$dest"
    
    # Enable the services
    systemctl enable "$service"
done

# Reload systemd and start services
systemctl daemon-reload

echo -e "${BLUE}8. Avvio dei servizi...${NC}"
systemctl start lp-bridge.service
systemctl start lp-cec.service
systemctl start lp-webui.service
systemctl start lp-kiosk.service

echo -e "${GREEN}=== Setup completato con successo! ===${NC}"
echo -e "Il Raspberry Pi è ora configurato come ponte audio Bluetooth."
echo -e "All'avvio, l'interfaccia monitor si aprirà automaticamente via HDMI."
echo -e "L'interfaccia web è accessibile nella rete locale su: ${BLUE}http://<IP-DEL-RPI>:5000${NC}"
echo -e "Spegni/Accendi l'amplificatore Denon per testare lo standby automatico."
