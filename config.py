import os

class Config:
    """Configuration settings for the timing sequence application"""
    
    # Server settings
    HOST = '0.0.0.0'  # Allow external connections
    PORT = 5000
    DEBUG = False  # Set to True for development
    
    # Audio settings
    AUDIO_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'audio')
    AUDIO_DEVICE = None  # Optional output device name
    
    # Audio file names (place these files in the audio directory)
    BEEP1_FILE = 'beep1.wav'      # Short beep
    BEEP2_FILE = 'double_beep.wav'  # Short double-beep
    BEEP3_FILE = 'long_beep.wav'    # Long beep (gate open cue)
    
    # Default timing delays (in seconds)
    DEFAULT_DELAY1 = 5.0  # Delay between beep 1 and beep 2
    DEFAULT_DELAY2 = 8.0  # Delay between beep 2 and beep 3
    DEFAULT_GATE_DELAY = 0.0  # Delay after final beep before gate opens
    
    # Timing constraints
    MIN_TOTAL_TIME = 8.0   # Minimum total sequence time
    MAX_TOTAL_TIME = 20.0  # Maximum total sequence time
    
    # Audio playback settings
    AUDIO_VOLUME = 0.8  # Volume level (0.0 to 1.0)
    
    # Web interface settings
    AUTO_REFRESH_INTERVAL = 100  # milliseconds for status updates
    COUNTDOWN_UPDATE_INTERVAL = 50  # milliseconds for countdown updates 
    
    # Relay control settings
    RELAY_PIN = 17      # BCM numbering
    RELAY_ACTIVE_HIGH = True
    GATE_OPEN_DURATION = 3.0
