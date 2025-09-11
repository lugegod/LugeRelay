
import os
import subprocess
import threading
import time
from datetime import datetime

import pygame
from flask import Flask, render_template, request, jsonify, send_from_directory


from flask import Flask, render_template, request, jsonify, send_from_directory
import os
import threading
import time
import json
from datetime import datetime
import subprocess
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
    def __init__(self, delay1, delay2):
        self.delay1 = delay1  # Delay between beep 1 and beep 2
        self.delay2 = delay2  # Delay between beep 2 and beep 3
        self.total_time = delay1 + delay2 + 3  # +3 for final beep duration + gate open time
        
    def get_sequence_timeline(self):
        """Returns timeline of events in seconds from start"""
        return {
            'beep1': 0,
            'beep2': self.delay1,
            'beep3': self.delay1 + self.delay2,
            'gate_open': self.delay1 + self.delay2,  # Immediately after beep 3
            'reset': self.delay1 + self.delay2 + 3  # 3 seconds after gate open
        }

def init_audio():
    """Initialize pygame mixer for audio playback"""
    try:
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
        
        # Gate open phase starts immediately (3 seconds)
        print("Gate open phase")
        time.sleep(3)
        
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
                         default_delay2=app.config['DEFAULT_DELAY2'])

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
        
        # Validate delays
        total_time = delay1 + delay2 + 3  # +3 for beep duration + gate open time
        if total_time < 8 or total_time > 20:
            return jsonify({'success': False, 'message': 'Total sequence time must be between 8-20 seconds'})
        
        sequence = TimingSequence(delay1, delay2)
        
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

@app.route('/bluetooth_scan', methods=['POST'])
def bluetooth_scan():
    """Trigger a bounded Bluetooth scan using bluetoothctl."""

    def _scan():
        proc = None
        try:
            proc = subprocess.Popen(
                ['bluetoothctl'],
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                text=True
            )
            proc.stdin.write('scan on\n')
            proc.stdin.flush()
            time.sleep(5)
            proc.stdin.write('scan off\n')
            proc.stdin.flush()
        except Exception as e:
            print(f"Bluetooth scan error: {e}")
        finally:
            if proc:
                try:
                    proc.terminate()
                    proc.wait(timeout=5)
                except Exception:
                    proc.kill()

    thread = threading.Thread(target=_scan, daemon=True)
    thread.start()
    return jsonify({'success': True, 'message': 'Bluetooth scan started'})

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
    if not init_audio():
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