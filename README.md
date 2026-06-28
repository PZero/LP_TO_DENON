# LP TO DENON - Bluetooth to HDMI Audio Bridge

Questo progetto trasforma un **Raspberry Pi 3 Mod. B** in un ponte audio Bluetooth headless e intelligente. Consente di collegare un giradischi Bluetooth (che supporta la trasmissione verso cuffie) al Raspberry Pi, che agirà da "cuffia virtuale", e di instradare l'audio digitale in modo lossless tramite la porta **HDMI** verso un amplificatore AV Denon (o qualsiasi ricevitore/TV HDMI).

Il sistema include:
*   **Pairing Automatico Headless**: Accetta automaticamente le connessioni dal giradischi senza richiedere inserimento di PIN o tastiera.
*   **Standby Software via HDMI-CEC**: Quando spegni l'amplificatore Denon, il Raspberry Pi disattiva l'uscita video HDMI e spegne il Bluetooth (per evitare che il giradischi si connetta a vuoto). Quando riaccendi l'amplificatore, il Pi riattiva l'HDMI e riabilita il Bluetooth.
*   **Indicatori Acustici (Chimes)**: Riproduce brevi suoni sintetici attraverso l'HDMI all'avvio del sistema, all'avvenuta connessione e alla disconnessione del giradischi.
*   **Dashboard di Monitoraggio HDMI**: Mostra a schermo intero sul TV una splendida interfaccia scura (Kiosk Mode) con lo stato corrente: una parabola radar blu pulsante in modalità ricerca, e un vinile che gira con un equalizzatore grafico animato quando il giradischi è connesso.

---

## 🛠️ Prerequisiti Hardware e Software

1.  **Raspberry Pi 3 Mod. B** (con Bluetooth e HDMI integrati).
2.  **Cavo HDMI** connesso ad un ingresso dell'amplificatore AV Denon.
3.  **Scheda MicroSD** (minimo 8GB).
4.  **Raspberry Pi OS Lite (Bookworm, 64-bit)** installato.
    *   *Nota*: La versione **Lite** è consigliata perché è priva di desktop environment pesante, garantendo un boot rapido e un minor consumo di risorse.

---

## 💾 Preparazione del Raspberry Pi (OS Flashing)

1.  Scarica e apri **Raspberry Pi Imager** sul tuo computer.
2.  Scegli il dispositivo (Raspberry Pi 3) ed il Sistema Operativo: **Raspberry Pi OS (Other) -> Raspberry Pi OS Lite (64-bit)** (Bookworm).
3.  Clicca su **Avanti** e poi su **Modifica Impostazioni**:
    *   Imposta un nome utente ed una password (es. utente: `pi`).
    *   Configura la tua rete Wi-Fi locale.
    *   Abilita il servizio **SSH** (nella scheda "Servizi") per poterti collegare da remoto.
4.  Scrivi l'immagine sulla MicroSD e inseriscila nel Raspberry Pi.

---

## 🚀 Installazione ed Avvio

Collega il Raspberry Pi all'alimentazione e all'amplificatore HDMI, attendi che si avvii, quindi collegati via SSH dal tuo computer principale:

```bash
ssh pi@<ip-del-raspberry-pi>
```

Una volta entrato, scarica il progetto (o clonalo tramite Git):

```bash
git clone https://github.com/PZero/LP_TO_DENON.git
cd LP_TO_DENON
```

Esegui lo script di installazione automatica:

```bash
sudo ./setup.sh
```

Lo script si occuperà di:
1. Aggiornare il sistema ed installare le dipendenze richieste (PipeWire, BlueZ, X11, Chromium, Flask).
2. Configurare il Bluetooth del Raspberry Pi come **Audio Headphone/Receiver** (cambiando il *Class of Device* a `0x200414`), rendendolo rilevabile dal giradischi.
3. Compilare e generare i file dei chime sonori (`boot.wav`, `connected.wav`, `disconnected.wav`).
4. Installare e attivare i 4 servizi Systemd per gestire in background il ponte Bluetooth, il monitor HDMI-CEC, il server web della UI e la Kiosk Mode su schermo.

---

## ⚙️ Come Funziona il Sistema

### 1. Primo Accoppiamento (Pairing)
1. Assicurati che l'amplificatore Denon sia acceso e sintonizzato sull'ingresso HDMI del Raspberry Pi. Sullo schermo vedrai apparire l'interfaccia con la scritta **"Ricerca Giradischi in corso..."** e il radar blu.
2. Metti il tuo giradischi in modalità **Pairing Bluetooth**.
3. Il Raspberry Pi rileverà la richiesta di pairing e la accetterà automaticamente grazie al D-Bus Agent personalizzato (`lp_bridge_manager.py`).
4. All'avvenuta connessione, sentirai un chime sonoro ascendente e l'interfaccia sul TV mostrerà un **vinile in rotazione** con il nome del tuo giradischi ed un equalizzatore grafico.
5. Il giradischi verrà aggiunto ai dispositivi "Trusted" del Pi: le volte successive si collegherà automaticamente appena acceso.

### 2. Standby Intelligente via CEC
Il servizio `lp-cec.service` monitora costantemente lo stato di accensione del TV/Amplificatore:
*   Se spegni l'amplificatore, il Pi spegne il Bluetooth e l'uscita video HDMI, riducendo i consumi e impedendo al giradischi di collegarsi accidentalmente.
*   Se accendi l'amplificatore, il Pi riaccende lo schermo e riapre il canale Bluetooth, pronto a connettersi al giradischi appena quest'ultimo viene avviato.

---

## 💻 Struttura del Progetto

```
LP_TO_DENON/
├── README.md               # Questa documentazione
├── setup.sh                # Script di installazione automatica per RPi
├── config/
│   └── systemd/            # Template dei servizi di sistema Systemd
│       ├── lp-bridge.service
│       ├── lp-cec.service
│       ├── lp-kiosk.service
│       └── lp-webui.service
└── src/
    ├── generate_chimes.py  # Generatore di file audio WAV per i chime
    ├── bridge_manager.py   # Bluetooth Agent e gestione eventi connessione
    ├── cec_monitor.py      # Monitor HDMI-CEC per la gestione dello standby
    └── ui/                 # Interfaccia grafica di monitoraggio
        ├── app.py          # Server Flask (Web API)
        ├── kiosk_start.sh  # Script di avvio per X11 + Chromium Kiosk
        ├── static/
        │   └── style.css   # Stile CSS moderno (dark mode, radar, vinile)
        └── templates/
            └── index.html  # Template HTML5 con polling JS dello stato
```

---

## 🛠️ Risoluzione dei Problemi (Troubleshooting)

### Controllare lo stato dei servizi
Puoi verificare se i servizi stanno girando correttamente usando `systemctl`:
```bash
systemctl status lp-bridge.service  # Stato del ponte Bluetooth
systemctl status lp-cec.service     # Stato del monitor CEC
systemctl status lp-webui.service   # Stato del server Flask
systemctl status lp-kiosk.service   # Stato dell'interfaccia HDMI
```

### Controllare i log di errore
```bash
journalctl -u lp-bridge.service -n 50 -f  # Log in tempo reale del Bluetooth
journalctl -u lp-cec.service -n 50 -f     # Log in tempo reale del monitor CEC
```

### Controllare le connessioni audio PipeWire
Per vedere i dispositivi audio attivi e come sono mappati da PipeWire:
```bash
wpctl status
```
Dovresti vedere il tuo giradischi sotto la sezione "Sources" e l'uscita HDMI sotto la sezione "Sinks".
