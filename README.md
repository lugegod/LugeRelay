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

## Raspberry Pi Setup

For Raspberry Pi deployment steps—including OS installation, dependency setup, and wiring instructions—see the [Raspberry Pi setup guide](docs/raspberry_pi_setup.md).
