# Raspberry Pi 3B Setup

## Flash Raspberry Pi OS
1. Download and install **Raspberry Pi Imager**.
2. Use it to flash **Raspberry Pi OS with Desktop** to a microSD card for the Pi 3B.
3. In the Imager settings enable SSH and configure Wi‑Fi as needed.

## First Boot
After the Pi boots, open a terminal or connect via SSH and update the system:

```bash
sudo apt update && sudo apt full-upgrade
```

## Install Dependencies
Install core packages and Python requirements:

```bash
sudo apt install python3-pip python3-venv
pip install -r requirements.txt
```

## Clone and Run the App
```bash
git clone https://github.com/<your-user>/LugeRelay.git
cd LugeRelay
python3 app.py
```

Open the Pi’s browser and navigate to `http://localhost:5000`.

## Wire the Relay
Connect a relay module to the Pi:

- VCC → 5 V
- GND → Ground
- Signal → **BCM 17** (physical pin 11)

## Troubleshooting
### Audio
- Ensure the correct audio output is selected (taskbar or `raspi-config`).
- Use `alsamixer` to check volumes and unmute channels.

### GPIO Permissions
If access to GPIO fails:

```bash
sudo adduser $USER gpio
```
Log out and back in to apply the group change.

### Autostart at Boot (Optional)
Create a systemd service or add a cron entry to launch the app on boot:

```bash
crontab -e
@reboot /usr/bin/python3 /home/pi/LugeRelay/app.py
```

