# Luge Relay Controller

This project provides a simple three-beep timing sequence and optional relay control for starting gates.

## Configuration

Relay behavior can be customized in `config.py`:

- `RELAY_PIN` – BCM pin number connected to the relay
- `RELAY_ACTIVE_HIGH` – set to `True` if the relay is triggered by a high signal
- `GATE_OPEN_DURATION` – number of seconds the gate stays open after the final beep

Adjust these values to match your hardware setup.

## Installation

Install the dependencies:

```bash
pip install -r requirements.txt
```

## Running

Start the web interface:

```bash
python app.py
```

Open a browser to `http://localhost:5000` to control the sequence.

## Web Interface Settings

The web interface provides a **Settings** panel where you can:

- Select the **audio output device** for playback of the timing cues.
- Adjust the **delay after the final beep before the gate opens** in 0.1 s increments.
- **Scan, pair, and connect** a Bluetooth speaker to use for audio output.

