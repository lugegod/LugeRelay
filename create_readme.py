#!/usr/bin/env python3
"""Create README file for Windows executable"""

readme_content = '''# Luge Timing Sequence Controller - Windows Executable

## Quick Start

1. Double-click "Launch_LugeTimer.bat" to start the application
2. Wait for the application to start (you'll see a console window)
3. Open your web browser and go to: http://localhost:5000
4. Use the web interface to control your timing sequences

## Features

- Three-beep timing sequence with configurable delays
- Real-time countdown displays
- Stop button to interrupt sequences
- Gate open phase with auto-reset
- Works on any Windows computer (no installation required)
- Accessible from any device on the same network

## Audio Files

The application includes test beep sounds. To use your own audio files:

1. Replace the files in the "audio" folder:
   - beep1.wav - Short beep
   - double_beep.wav - Short double-beep
   - long_beep.wav - Long beep (gate open cue)

2. Restart the application

## Network Access

Once running, you can access the application from:
- This computer: http://localhost:5000
- Other devices on network: http://[this-computer-ip]:5000

## Troubleshooting

- If the browser doesn't open automatically: Manually go to http://localhost:5000
- If you get a firewall warning: Allow the application through your firewall
- If audio doesn't work: Check your system volume and audio settings
- To stop the application: Close the console window or press Ctrl+C

## System Requirements

- Windows 7 or later
- No additional software installation required
- Internet connection (for initial setup only)

---
Happy Timing!
'''

# Write with UTF-8 encoding
with open('README_Windows.txt', 'w', encoding='utf-8') as f:
    f.write(readme_content)

print("README file created successfully!") 