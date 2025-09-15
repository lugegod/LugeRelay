
import os
import sys
import threading
import time
import json
from datetime import datetime

import pygame
from flask import Flask, render_template, request, jsonify, send_from_directory

# GPIO imports - only import if available (for non-Pi systems)
try:
    from gpiozero import DigitalOutputDevice
    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False
    print("Warning: GPIO not available. Running in simulation mode.")

from config import Config

app = Flask(__name__)
app.config.from_object(Config)

# Settings file path
SETTINGS_FILE = 'settings.json'

def load_settings_from_file():
    """Load settings from JSON file"""
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, 'r') as f:
                settings = json.load(f)
                # Update app config with loaded settings
                for key, value in settings.items():
                    if key in app.config:
                        app.config[key] = value
                print(f"Loaded settings from {SETTINGS_FILE}")
                return True
    except Exception as e:
        print(f"Error loading settings: {e}")
    return False

def save_settings_to_file():
    """Save current settings to JSON file"""
    try:
        settings = {
            'HOST': app.config['HOST'],
            'PORT': app.config['PORT'],
            'DEBUG': app.config['DEBUG'],
            'DEFAULT_DELAY1': app.config['DEFAULT_DELAY1'],
            'DEFAULT_DELAY2': app.config['DEFAULT_DELAY2'],
            'MIN_TOTAL_TIME': app.config['MIN_TOTAL_TIME'],
            'MAX_TOTAL_TIME': app.config['MAX_TOTAL_TIME'],
            'AUDIO_VOLUME': app.config['AUDIO_VOLUME'],
            'AUTO_REFRESH_INTERVAL': app.config['AUTO_REFRESH_INTERVAL'],
            'COUNTDOWN_UPDATE_INTERVAL': app.config['COUNTDOWN_UPDATE_INTERVAL'],
            'RELAY_PIN': app.config['RELAY_PIN'],
            'RELAY_ACTIVE_HIGH': app.config['RELAY_ACTIVE_HIGH'],
            'GATE_OPEN_DURATION': app.config['GATE_OPEN_DURATION'],
            'BEEP_RELAY_ALIGNMENT': app.config['BEEP_RELAY_ALIGNMENT']
        }
        
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(settings, f, indent=2)
        print(f"Settings saved to {SETTINGS_FILE}")
        return True
    except Exception as e:
        print(f"Error saving settings: {e}")
        return False

# Load settings on startup
load_settings_from_file()

# Global variables for sequence state
sequence_running = False
sequence_stopped = False
current_sequence = None
sequence_start_time = None

# Relay control
relay_device = None
relay_active = False

class TimingSequence:
    def __init__(self, delay1, delay2):
        self.delay1 = delay1  # Delay between beep 1 and beep 2
        self.delay2 = delay2  # Delay between beep 2 and beep 3
        self.total_time = delay1 + delay2 + app.config['GATE_OPEN_DURATION']
        
    def get_sequence_timeline(self, alignment_offset=0):
        """Returns timeline of events in seconds from start"""
        beep3_time = self.delay1 + self.delay2
        gate_open_time = beep3_time  # Gate opens immediately after beep 3
        relay_activation_time = beep3_time + alignment_offset  # Relay activation with alignment offset
        
        return {
            'beep1': 0,
            'beep2': self.delay1,
            'beep3': beep3_time,
            'gate_open': gate_open_time,  # Immediately after beep 3
            'relay_activation': relay_activation_time,  # Relay activation with alignment offset
            'reset': gate_open_time + app.config['GATE_OPEN_DURATION']
        }

class TestSequence:
    def __init__(self, offset):
        self.offset = offset  # Beep-relay alignment offset
        self.total_time = 3.0 + app.config['GATE_OPEN_DURATION']
        
    def get_sequence_timeline(self):
        """Returns timeline of events in seconds from start"""
        beep_time = 3.0  # Beep plays at 3 seconds
        gate_open_time = beep_time  # Gate opens immediately after beep
        relay_activation_time = beep_time + self.offset  # Relay activation with offset
        
        return {
            'beep1': 0,  # Not used in test mode
            'beep2': 0,  # Not used in test mode
            'beep3': beep_time,
            'gate_open': gate_open_time,  # Immediately after beep
            'relay_activation': relay_activation_time,  # Relay activation with offset
            'reset': gate_open_time + app.config['GATE_OPEN_DURATION']
        }

def init_audio():
    """Initialize pygame mixer for audio playback with retry logic"""
    max_retries = 3
    retry_delay = 0.5
    
    for attempt in range(max_retries):
        try:
            # First, try to quit any existing mixer to ensure clean state
            if pygame.mixer.get_init() is not None:
                pygame.mixer.quit()
                time.sleep(0.1)  # Brief pause after quit
            
            # Initialize with more conservative settings
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=1024)
            
            # Verify initialization was successful
            if pygame.mixer.get_init() is not None:
                print(f"Audio system initialized successfully (attempt {attempt + 1})")
                return True
            else:
                print(f"Audio initialization returned None (attempt {attempt + 1})")
                
        except Exception as e:
            print(f"Audio initialization failed (attempt {attempt + 1}): {e}")
            
        # Wait before retry (except on last attempt)
        if attempt < max_retries - 1:
            print(f"Retrying audio initialization in {retry_delay}s...")
            time.sleep(retry_delay)
            retry_delay *= 1.5  # Exponential backoff
    
    print("Audio initialization failed after all retries")
    return False

def play_audio_file(filename):
    """Play an audio file using pygame with fallback initialization"""
    audio_path = os.path.join(app.config['AUDIO_DIR'], filename)
    try:
        # Check if audio system is still initialized
        if pygame.mixer.get_init() is None:
            print("Audio system not initialized, attempting to reinitialize...")
            if not init_audio():
                print("Failed to reinitialize audio system")
                return False

        if os.path.exists(audio_path):
            sound = pygame.mixer.Sound(audio_path)
            # Apply configured volume to this sound (0.0 - 1.0)
            try:
                sound.set_volume(app.config['AUDIO_VOLUME'])
            except Exception:
                pass
            sound.play()
            print(f"Playing audio: {filename}")
            return True
        else:
            print(f"Audio file not found: {audio_path}")
            return False
    except Exception as e:
        print(f"Error playing audio {filename}: {e}")
        # Try to reinitialize audio system on error
        print("Attempting to reinitialize audio system...")
        if init_audio():
            try:
                sound = pygame.mixer.Sound(audio_path)
                try:
                    sound.set_volume(app.config['AUDIO_VOLUME'])
                except Exception:
                    pass
                sound.play()
                print(f"Successfully played audio after reinitialization: {filename}")
                return True
            except Exception as retry_e:
                print(f"Failed to play audio even after reinitialization: {retry_e}")
        return False

def init_relay():
    """Initialize the relay GPIO device"""
    global relay_device
    
    if not GPIO_AVAILABLE:
        print("GPIO not available - relay will be simulated")
        return True
    
    try:
        relay_device = DigitalOutputDevice(
            pin=app.config['RELAY_PIN'],
            active_high=app.config['RELAY_ACTIVE_HIGH']
        )
        print(f"Relay initialized on pin {app.config['RELAY_PIN']} (active_high={app.config['RELAY_ACTIVE_HIGH']})")
        return True
    except Exception as e:
        print(f"Failed to initialize relay: {e}")
        return False

def set_relay_state(active):
    """Set the relay state (True = active, False = inactive)"""
    global relay_active
    
    relay_active = active
    
    if GPIO_AVAILABLE and relay_device:
        try:
            if active:
                relay_device.on()
                print("Relay activated")
            else:
                relay_device.off()
                print("Relay deactivated")
        except Exception as e:
            print(f"Error controlling relay: {e}")
    else:
        # Simulation mode
        status = "ACTIVE" if active else "INACTIVE"
        print(f"Relay simulation: {status}")

def get_relay_status():
    """Get current relay status"""
    global relay_active
    return relay_active

def run_sequence(sequence):
    """Run the timing sequence in a separate thread"""
    global sequence_running, sequence_stopped, current_sequence, sequence_start_time
    
    sequence_running = True
    sequence_stopped = False
    current_sequence = sequence
    sequence_start_time = time.time()
    
    timeline = sequence.get_sequence_timeline(app.config['BEEP_RELAY_ALIGNMENT'])
    
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
        
        # Calculate timing for relay activation
        alignment_offset = app.config['BEEP_RELAY_ALIGNMENT']
        
        # Adjust delay2 if we have a negative offset
        if alignment_offset < 0:
            # For negative offset, we need to activate relay earlier
            # So we reduce delay2 by the offset amount
            adjusted_delay2 = sequence.delay2 + alignment_offset
            print(f"Adjusted delay2 to {adjusted_delay2}s for negative offset")
            
            # Ensure we don't have negative delay
            if adjusted_delay2 < 0:
                print(f"Warning: offset {alignment_offset}s is larger than delay2 {sequence.delay2}s")
                adjusted_delay2 = 0
        else:
            adjusted_delay2 = sequence.delay2
        
        # Wait for adjusted delay 2 (with stop check)
        if adjusted_delay2 > 0:
            for _ in range(int(adjusted_delay2 * 10)):  # Check every 0.1 seconds
                if sequence_stopped:
                    return
                time.sleep(0.1)
        
        if sequence_stopped:
            return
            
        # Handle relay activation based on offset
        if alignment_offset < 0:
            # Negative offset: relay activates now (before beep 3)
            print(f"Relay activating {abs(alignment_offset)}s before beep 3")
            set_relay_state(True)
            
            # Wait for the remaining time until beep 3
            for _ in range(int(abs(alignment_offset) * 10)):  # Check every 0.1 seconds
                if sequence_stopped:
                    return
                time.sleep(0.1)
        else:
            # Positive or zero offset: relay activates after beep 3
            # No additional waiting needed here - we'll handle it after beep 3
            pass
        
        if sequence_stopped:
            return
            
        # Play beep 3 (long beep)
        print("Playing beep 3")
        play_audio_file(app.config['BEEP3_FILE'])
        
        # Gate open phase starts immediately after beep 3
        print("Gate open phase")
        
        if alignment_offset >= 0:
            # Positive or zero offset: activate relay after beep 3
            if alignment_offset > 0:
                for _ in range(int(alignment_offset * 10)):  # Check every 0.1 seconds
                    if sequence_stopped:
                        return
                    time.sleep(0.1)
            set_relay_state(True)
        
        # Wait for configured gate open duration
        gate_open_duration = app.config['GATE_OPEN_DURATION']
        steps = max(1, int(gate_open_duration * 10))
        for _ in range(steps):  # Check every 0.1 seconds
            if sequence_stopped:
                return
            time.sleep(0.1)
        
        set_relay_state(False)  # Deactivate relay
        
        print("Sequence completed successfully")
        
    except Exception as e:
        print(f"Sequence error: {e}")
    finally:
        print("Resetting sequence state")
        set_relay_state(False)  # Ensure relay is off
        sequence_running = False
        sequence_stopped = False
        current_sequence = None
        sequence_start_time = None
        print("Sequence reset complete")

def run_test_sequence(sequence):
    """Run the test sequence in a separate thread (3s silence + final beep + relay)"""
    global sequence_running, sequence_stopped, current_sequence, sequence_start_time
    
    sequence_running = True
    sequence_stopped = False
    current_sequence = sequence
    sequence_start_time = time.time()
    
    timeline = sequence.get_sequence_timeline()
    
    try:
        print("Test sequence started - 3 seconds silence")
        
        # Calculate timing for relay activation
        beep_time = 3.0
        offset = sequence.offset
        
        # Handle relay activation based on offset
        if offset < 0:
            # Negative offset: relay activates before beep
            print(f"Relay will activate {abs(offset)}s before beep")
            # Wait for the time until relay activation (beep_time + offset)
            relay_activation_time = beep_time + offset
            if relay_activation_time > 0:
                for _ in range(int(relay_activation_time * 10)):  # Check every 0.1 seconds
                    if sequence_stopped:
                        return
                    time.sleep(0.1)
            
            if sequence_stopped:
                return
                
            # Activate relay
            set_relay_state(True)
            
            # Wait remaining time until beep
            for _ in range(int(abs(offset) * 10)):  # Check every 0.1 seconds
                if sequence_stopped:
                    return
                time.sleep(0.1)
        else:
            # Positive or zero offset: wait until beep time
            for _ in range(int(beep_time * 10)):  # Check every 0.1 seconds for 3 seconds
                if sequence_stopped:
                    return
                time.sleep(0.1)
        
        if sequence_stopped:
            return
        
        if sequence_stopped:
            return
            
        # Play final beep (beep 3)
        print("Playing final beep")
        play_audio_file(app.config['BEEP3_FILE'])
        
        # Gate open phase starts immediately after beep
        print("Gate open phase")
        
        if offset >= 0:
            # Positive or zero offset: activate relay after beep
            if offset > 0:
                for _ in range(int(offset * 10)):  # Check every 0.1 seconds
                    if sequence_stopped:
                        return
                    time.sleep(0.1)
            set_relay_state(True)
        
        # Wait for configured gate open duration
        gate_open_duration = app.config['GATE_OPEN_DURATION']
        steps = max(1, int(gate_open_duration * 10))
        for _ in range(steps):  # Check every 0.1 seconds
            if sequence_stopped:
                return
            time.sleep(0.1)
        
        set_relay_state(False)  # Deactivate relay
        
        print("Test sequence completed successfully")
        
    except Exception as e:
        print(f"Test sequence error: {e}")
    finally:
        print("Resetting test sequence state")
        set_relay_state(False)  # Ensure relay is off
        sequence_running = False
        sequence_stopped = False
        current_sequence = None
        sequence_start_time = None
        print("Test sequence reset complete")

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
        # Reset stop flag before starting new sequence
        sequence_stopped = False
        
        data = request.get_json()
        delay1 = float(data.get('delay1', app.config['DEFAULT_DELAY1']))
        delay2 = float(data.get('delay2', app.config['DEFAULT_DELAY2']))
        
        # Validate delays using configured constraints
        total_time = delay1 + delay2 + app.config['GATE_OPEN_DURATION']
        min_total = app.config['MIN_TOTAL_TIME']
        max_total = app.config['MAX_TOTAL_TIME']
        if total_time < min_total or total_time > max_total:
            return jsonify({'success': False, 'message': f'Total sequence time must be between {min_total:.1f}-{max_total:.1f} seconds'})
        
        sequence = TimingSequence(delay1, delay2)
        
        # Start sequence in background thread
        thread = threading.Thread(target=run_sequence, args=(sequence,))
        thread.daemon = True
        thread.start()
        
        return jsonify({'success': True, 'message': 'Sequence started'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/set_random_values', methods=['POST'])
def set_random_values():
    """Set random timing values without starting sequence"""
    try:
        # Generate random delays with constraint: delay2 > delay1
        import random
        
        # Generate delay1 between 1-8 seconds
        delay1 = round(random.uniform(1.0, 8.0), 1)
        
        # Generate delay2 within configured bounds and ensuring delay2 > delay1
        min_total = app.config['MIN_TOTAL_TIME']
        max_total = app.config['MAX_TOTAL_TIME']
        gate_open_duration = app.config['GATE_OPEN_DURATION']
        
        min_delay2 = max(delay1 + 0.5, min_total - delay1 - gate_open_duration)
        max_delay2 = min(12.0, max_total - delay1 - gate_open_duration)
        
        if min_delay2 >= max_delay2:
            # Fallback to safe values if random generation window is invalid
            delay1 = 3.0
            delay2 = 5.0
        else:
            delay2 = round(random.uniform(min_delay2, max_delay2), 1)
        
        # Validate total time
        total_time = delay1 + delay2 + 1
        if total_time < 6 or total_time > 18:
            # Fallback to safe values if random generation fails
            delay1 = 3.0
            delay2 = 5.0
        
        return jsonify({
            'success': True, 
            'message': 'Random values set',
            'delay1': delay1,
            'delay2': delay2
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/start_test_sequence', methods=['POST'])
def start_test_sequence():
    """Start a test timing sequence (3s silence + final beep + relay)"""
    global sequence_running, sequence_stopped
    
    if sequence_running:
        return jsonify({'success': False, 'message': 'Sequence already running'})
    
    try:
        # Reset stop flag before starting new test sequence
        sequence_stopped = False
        
        data = request.get_json()
        offset = float(data.get('offset', 0.0))
        
        # Create test sequence: 3 seconds silence + final beep + relay
        sequence = TestSequence(offset)
        
        # Start sequence in background thread
        thread = threading.Thread(target=run_test_sequence, args=(sequence,))
        thread.daemon = True
        thread.start()
        
        return jsonify({'success': True, 'message': 'Test sequence started'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/stop_sequence', methods=['POST'])
def stop_sequence():
    """Stop the current sequence"""
    global sequence_running, sequence_stopped, current_sequence, sequence_start_time
    
    if not sequence_running:
        return jsonify({'success': False, 'message': 'No sequence running'})
    
    try:
        # Set stop flag to interrupt the sequence
        sequence_stopped = True
        
        # Deactivate relay immediately when stopping
        set_relay_state(False)
        
        # Immediately reset all sequence state
        sequence_running = False
        current_sequence = None
        sequence_start_time = None
        
        print("Sequence stopped and reset immediately")
        return jsonify({'success': True, 'message': 'Sequence stopped and reset'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/sequence_status')
def sequence_status():
    """Get current sequence status for real-time updates"""
    global sequence_running, current_sequence, sequence_start_time, sequence_stopped
    
    # If sequence was stopped, immediately return idle state
    if sequence_stopped:
        return jsonify({
            'running': False,
            'current_time': 0,
            'total_time': 0,
            'phase': 'idle'
        })
    
    if not sequence_running or not current_sequence or not sequence_start_time:
        return jsonify({
            'running': False,
            'current_time': 0,
            'total_time': 0,
            'phase': 'idle'
        })
    
    current_time = time.time() - sequence_start_time
    
    # Handle test sequence differently
    if hasattr(current_sequence, 'offset'):
        # Test sequence
        timeline = current_sequence.get_sequence_timeline()
        if current_time < timeline['beep3']:
            phase = 'test_silence'
            countdown = timeline['beep3'] - current_time
        elif get_relay_status():
            # Gate is open as long as relay is active
            phase = 'gate_open'
            countdown = max(0, timeline['reset'] - current_time)
        else:
            phase = 'complete'
            countdown = 0
    else:
        # Regular sequence
        timeline = current_sequence.get_sequence_timeline(app.config['BEEP_RELAY_ALIGNMENT'])
        if current_time < timeline['beep2']:
            phase = 'delay1'
            countdown = timeline['beep2'] - current_time
        elif current_time < timeline['beep3']:
            phase = 'delay2'
            countdown = timeline['beep3'] - current_time
        elif get_relay_status():
            # Gate is open as long as relay is active
            phase = 'gate_open'
            countdown = max(0, timeline['reset'] - current_time)
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
        'timeline': timeline,
        'relay_active': get_relay_status()
    })

    # Note: Bluetooth scan endpoint removed as it's unused.

@app.route('/audio/<filename>')
def serve_audio(filename):
    """Serve audio files"""
    return send_from_directory(app.config['AUDIO_DIR'], filename)

@app.route('/settings')
def settings():
    """Settings page"""
    return render_template('settings.html', 
                         config=app.config)

@app.route('/test')
def test():
    """Test mode page"""
    return render_template('test.html')

@app.route('/save_test_offset', methods=['POST'])
def save_test_offset():
    """Save test offset to persistent settings"""
    try:
        data = request.get_json()
        offset = float(data.get('offset', 0.0))
        
        # Update the beep-relay alignment setting
        app.config['BEEP_RELAY_ALIGNMENT'] = offset
        
        # Save to file for persistence
        if save_settings_to_file():
            return jsonify({'success': True, 'message': 'Test offset saved successfully'})
        else:
            return jsonify({'success': False, 'message': 'Failed to save settings to file'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/get_test_offset')
def get_test_offset():
    """Get current test offset setting"""
    try:
        return jsonify({
            'success': True, 
            'offset': app.config['BEEP_RELAY_ALIGNMENT']
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/get_settings')
def get_settings():
    """Get current settings"""
    return jsonify({
        'host': app.config['HOST'],
        'port': app.config['PORT'],
        'debug': app.config['DEBUG'],
        'default_delay1': app.config['DEFAULT_DELAY1'],
        'default_delay2': app.config['DEFAULT_DELAY2'],
        'min_total_time': app.config['MIN_TOTAL_TIME'],
        'max_total_time': app.config['MAX_TOTAL_TIME'],
        'audio_volume': app.config['AUDIO_VOLUME'],
        'auto_refresh_interval': app.config['AUTO_REFRESH_INTERVAL'],
        'countdown_update_interval': app.config['COUNTDOWN_UPDATE_INTERVAL'],
        'relay_pin': app.config['RELAY_PIN'],
        'relay_active_high': app.config['RELAY_ACTIVE_HIGH'],
        'gate_open_duration': app.config['GATE_OPEN_DURATION'],
        'beep_relay_alignment': app.config['BEEP_RELAY_ALIGNMENT']
    })

@app.route('/relay_status')
def relay_status():
    """Get current relay status"""
    return jsonify({
        'active': get_relay_status(),
        'gpio_available': GPIO_AVAILABLE
    })

@app.route('/save_settings', methods=['POST'])
def save_settings():
    """Save settings"""
    try:
        data = request.get_json()
        
        # Update config values
        app.config['HOST'] = data.get('host', app.config['HOST'])
        app.config['PORT'] = int(data.get('port', app.config['PORT']))
        app.config['DEBUG'] = bool(data.get('debug', app.config['DEBUG']))
        app.config['DEFAULT_DELAY1'] = float(data.get('default_delay1', app.config['DEFAULT_DELAY1']))
        app.config['DEFAULT_DELAY2'] = float(data.get('default_delay2', app.config['DEFAULT_DELAY2']))
        app.config['MIN_TOTAL_TIME'] = float(data.get('min_total_time', app.config['MIN_TOTAL_TIME']))
        app.config['MAX_TOTAL_TIME'] = float(data.get('max_total_time', app.config['MAX_TOTAL_TIME']))
        app.config['AUDIO_VOLUME'] = float(data.get('audio_volume', app.config['AUDIO_VOLUME']))
        app.config['AUTO_REFRESH_INTERVAL'] = int(data.get('auto_refresh_interval', app.config['AUTO_REFRESH_INTERVAL']))
        app.config['COUNTDOWN_UPDATE_INTERVAL'] = int(data.get('countdown_update_interval', app.config['COUNTDOWN_UPDATE_INTERVAL']))
        app.config['RELAY_PIN'] = int(data.get('relay_pin', app.config['RELAY_PIN']))
        app.config['RELAY_ACTIVE_HIGH'] = bool(data.get('relay_active_high', app.config['RELAY_ACTIVE_HIGH']))
        app.config['GATE_OPEN_DURATION'] = float(data.get('gate_open_duration', app.config['GATE_OPEN_DURATION']))
        app.config['BEEP_RELAY_ALIGNMENT'] = float(data.get('beep_relay_alignment', app.config['BEEP_RELAY_ALIGNMENT']))
        
        # Update pygame volume if audio is initialized
        if pygame.mixer.get_init():
            pygame.mixer.music.set_volume(app.config['AUDIO_VOLUME'])
        
        # Save settings to file for persistence
        if save_settings_to_file():
            return jsonify({'success': True, 'message': 'Settings saved successfully and persisted to file'})
        else:
            return jsonify({'success': True, 'message': 'Settings saved but failed to persist to file'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error saving settings: {str(e)}'})

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'audio_initialized': pygame.mixer.get_init() is not None,
        'audio_details': pygame.mixer.get_init() if pygame.mixer.get_init() else None
    })

@app.route('/reinit_audio', methods=['POST'])
def reinit_audio():
    """Manually reinitialize audio system"""
    try:
        if init_audio():
            return jsonify({'success': True, 'message': 'Audio system reinitialized successfully'})
        else:
            return jsonify({'success': False, 'message': 'Failed to reinitialize audio system'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error reinitializing audio: {str(e)}'})

if __name__ == '__main__':
    # Initialize audio system
    if not init_audio():
        print("Warning: Audio system not initialized. Audio playback will not work.")
    
    # Initialize relay system
    if not init_relay():
        print("Warning: Relay system not initialized. Relay control will not work.")
    
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