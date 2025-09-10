from flask import Flask, render_template, request, jsonify, send_from_directory
import os
import threading
import time
import json
from datetime import datetime
import pygame
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

# Global variables for sequence state
sequence_running = False
sequence_stopped = False
current_sequence = None
sequence_start_time = None

class TimingSequence:
    def __init__(self, delay1, delay2, gate_delay, gate_open_duration):
        self.delay1 = delay1  # Delay between beep 1 and beep 2
        self.delay2 = delay2  # Delay between beep 2 and beep 3
        self.gate_delay = gate_delay  # Delay after final beep before gate opens
        self.gate_open_duration = gate_open_duration
        self.total_time = delay1 + delay2 + gate_delay + gate_open_duration

    def get_sequence_timeline(self):
        """Returns timeline of events in seconds from start"""
        return {
            'beep1': 0,
            'beep2': self.delay1,
            'beep3': self.delay1 + self.delay2,
            'gate_open': self.delay1 + self.delay2 + self.gate_delay,
            'reset': self.total_time
        }

def init_audio(device=None):
    """Initialize pygame mixer for audio playback"""
    try:
        pygame.mixer.quit()
    except Exception:
        pass
    try:
        if device:
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512, device=device)
        else:
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
        return True
    except Exception as e:
        print(f"Audio initialization failed: {e}")
        return False

def play_audio_file(filename):
    """Play an audio file using pygame"""
    try:
        audio_path = os.path.join(app.config['AUDIO_DIR'], filename)
        if os.path.exists(audio_path):
            sound = pygame.mixer.Sound(audio_path)
            sound.play()
            return True
        else:
            print(f"Audio file not found: {audio_path}")
            return False
    except Exception as e:
        print(f"Error playing audio {filename}: {e}")
        return False

def run_sequence(sequence):
    """Run the timing sequence in a separate thread"""
    global sequence_running, sequence_stopped, current_sequence, sequence_start_time
    
    sequence_running = True
    sequence_stopped = False
    current_sequence = sequence
    sequence_start_time = time.time()
    
    timeline = sequence.get_sequence_timeline()
    
    try:
        # Play beep 1 immediately
        print("Playing beep 1")
        play_audio_file(app.config['BEEP1_FILE'])
        
        # Wait for delay 1 (with stop check)
        for _ in range(int(sequence.delay1 * 10)):  # Check every 0.1 seconds
            if sequence_stopped:
                return
            time.sleep(0.1)
        
        if sequence_stopped:
            return
            
        # Play beep 2
        print("Playing beep 2")
        play_audio_file(app.config['BEEP2_FILE'])
        
        # Wait for delay 2 (with stop check)
        for _ in range(int(sequence.delay2 * 10)):  # Check every 0.1 seconds
            if sequence_stopped:
                return
            time.sleep(0.1)
        
        if sequence_stopped:
            return
            
        # Play beep 3 (long beep)
        print("Playing beep 3")
        play_audio_file(app.config['BEEP3_FILE'])

        # Wait for configured gate delay
        for _ in range(int(sequence.gate_delay * 10)):
            if sequence_stopped:
                return
            time.sleep(0.1)

        if sequence_stopped:
            return

        # Gate open phase
        print("Gate open phase")
        time.sleep(sequence.gate_open_duration)
        
        print("Sequence completed successfully")
        
    except Exception as e:
        print(f"Sequence error: {e}")
    finally:
        print("Resetting sequence state")
        sequence_running = False
        sequence_stopped = False
        current_sequence = None
        sequence_start_time = None
        print("Sequence reset complete")

@app.route('/')
def index():
    """Main GUI page"""
    return render_template('index.html',
                         default_delay1=app.config['DEFAULT_DELAY1'],
                         default_delay2=app.config['DEFAULT_DELAY2'],
                         default_gate_delay=app.config['DEFAULT_GATE_DELAY'],
                         gate_open_duration=app.config['GATE_OPEN_DURATION'])

@app.route('/start_sequence', methods=['POST'])
def start_sequence():
    """Start a new timing sequence"""
    global sequence_running, sequence_stopped
    
    if sequence_running:
        return jsonify({'success': False, 'message': 'Sequence already running'})
    
    try:
        data = request.get_json()
        delay1 = float(data.get('delay1', app.config['DEFAULT_DELAY1']))
        delay2 = float(data.get('delay2', app.config['DEFAULT_DELAY2']))
        gate_delay = float(data.get('gateDelay', app.config['DEFAULT_GATE_DELAY']))

        # Validate delays
        total_time = delay1 + delay2 + gate_delay + app.config['GATE_OPEN_DURATION']
        if total_time < app.config['MIN_TOTAL_TIME'] or total_time > app.config['MAX_TOTAL_TIME']:
            return jsonify({'success': False, 'message': 'Total sequence time must be between 8-20 seconds'})

        sequence = TimingSequence(delay1, delay2, gate_delay, app.config['GATE_OPEN_DURATION'])
        
        # Start sequence in background thread
        thread = threading.Thread(target=run_sequence, args=(sequence,))
        thread.daemon = True
        thread.start()
        
        return jsonify({'success': True, 'message': 'Sequence started'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/stop_sequence', methods=['POST'])
def stop_sequence():
    """Stop the current sequence"""
    global sequence_running, sequence_stopped
    
    if not sequence_running:
        return jsonify({'success': False, 'message': 'No sequence running'})
    
    try:
        sequence_stopped = True
        return jsonify({'success': True, 'message': 'Sequence stopped'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/sequence_status')
def sequence_status():
    """Get current sequence status for real-time updates"""
    global sequence_running, current_sequence, sequence_start_time
    
    if not sequence_running or not current_sequence or not sequence_start_time:
        return jsonify({
            'running': False,
            'current_time': 0,
            'total_time': 0,
            'phase': 'idle'
        })
    
    current_time = time.time() - sequence_start_time
    timeline = current_sequence.get_sequence_timeline()
    
    # Determine current phase
    if current_time < timeline['beep2']:
        phase = 'delay1'
        countdown = timeline['beep2'] - current_time
    elif current_time < timeline['beep3']:
        phase = 'delay2'
        countdown = timeline['beep3'] - current_time
    elif current_time < timeline['gate_open']:
        phase = 'gate_delay'
        countdown = timeline['gate_open'] - current_time
    elif current_time < timeline['reset']:
        phase = 'gate_open'
        countdown = timeline['reset'] - current_time
    else:
        phase = 'complete'
        countdown = 0
    
    # Debug logging
    print(f"Status: running={sequence_running}, current_time={current_time:.1f}, phase={phase}, countdown={countdown:.1f}")
    
    return jsonify({
        'running': True,
        'current_time': current_time,
        'total_time': current_sequence.total_time,
        'phase': phase,
        'countdown': countdown,
        'timeline': timeline
    })


@app.route('/audio_devices')
def audio_devices():
    """Return list of available audio output devices"""
    try:
        from pygame._sdl2 import audio as sdl2_audio
        devices = list(sdl2_audio.get_audio_device_names(False))
    except Exception as e:
        print(f"Error listing audio devices: {e}")
        devices = []
    return jsonify({'devices': devices, 'current': app.config.get('AUDIO_DEVICE')})


@app.route('/set_audio_device', methods=['POST'])
def set_audio_device():
    """Set the active audio output device"""
    data = request.get_json()
    device = data.get('device')
    if not device:
        return jsonify({'success': False, 'message': 'No device specified'})
    if init_audio(device):
        app.config['AUDIO_DEVICE'] = device
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'message': 'Failed to initialize audio device'})


@app.route('/bluetooth/devices')
def bluetooth_devices():
    """List known Bluetooth devices"""
    try:
        output = subprocess.check_output(['bluetoothctl', 'devices'], text=True)
        devices = []
        for line in output.strip().split('\n'):
            parts = line.split(' ', 2)
            if len(parts) >= 3:
                devices.append({'address': parts[1], 'name': parts[2]})
    except Exception as e:
        print(f"Bluetooth device listing failed: {e}")
        devices = []
    return jsonify({'devices': devices})


@app.route('/bluetooth/scan', methods=['POST'])
def bluetooth_scan():
    """Start scanning for Bluetooth devices"""
    try:
        subprocess.check_call(['bluetoothctl', 'scan', 'on'])
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/bluetooth/pair', methods=['POST'])
def bluetooth_pair():
    """Pair and connect to a Bluetooth device"""
    data = request.get_json()
    address = data.get('address')
    if not address:
        return jsonify({'success': False, 'message': 'No address provided'})
    try:
        subprocess.check_call(['bluetoothctl', 'pair', address])
        subprocess.check_call(['bluetoothctl', 'trust', address])
        subprocess.check_call(['bluetoothctl', 'connect', address])
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/audio/<filename>')
def serve_audio(filename):
    """Serve audio files"""
    return send_from_directory(app.config['AUDIO_DIR'], filename)

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'audio_initialized': pygame.mixer.get_init() is not None
    })

if __name__ == '__main__':
    # Initialize audio system
    if not init_audio(app.config.get('AUDIO_DEVICE')):
        print("Warning: Audio system not initialized. Audio playback will not work.")
    
    # Create audio directory if it doesn't exist
    os.makedirs(app.config['AUDIO_DIR'], exist_ok=True)
    
    print(f"Starting Flask app on {app.config['HOST']}:{app.config['PORT']}")
    print(f"Audio directory: {app.config['AUDIO_DIR']}")
    print("Place your beep audio files in the audio directory:")
    print(f"  - {app.config['BEEP1_FILE']}")
    print(f"  - {app.config['BEEP2_FILE']}")
    print(f"  - {app.config['BEEP3_FILE']}")
    
    app.run(
        host=app.config['HOST'],
        port=app.config['PORT'],
        debug=app.config['DEBUG']
    ) 
