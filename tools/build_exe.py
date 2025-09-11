#!/usr/bin/env python3
"""
Build script to create a standalone Windows executable for the Luge Timing Sequence Controller
This script packages everything into a single .exe file that can run on any Windows machine
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def print_status(message, status="INFO"):
    """Print a formatted status message"""
    colors = {
        "INFO": "\033[94m",    # Blue
        "SUCCESS": "\033[92m", # Green
        "WARNING": "\033[93m", # Yellow
        "ERROR": "\033[91m",   # Red
    }
    color = colors.get(status, "\033[0m")
    reset = "\033[0m"
    print(f"{color}[{status}]{reset} {message}")

def install_pyinstaller():
    """Install PyInstaller if not already installed"""
    try:
        import PyInstaller
        print_status("PyInstaller already installed", "SUCCESS")
        return True
    except ImportError:
        print_status("Installing PyInstaller...", "INFO")
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)
            print_status("PyInstaller installed successfully", "SUCCESS")
            return True
        except subprocess.CalledProcessError as e:
            print_status(f"Failed to install PyInstaller: {e}", "ERROR")
            return False

def create_spec_file():
    """Create a PyInstaller spec file for the application"""
    spec_content = '''# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('templates', 'templates'),
        ('static', 'static'),
        ('config.py', '.'),
        ('audio', 'audio'),
    ],
    hiddenimports=[
        'flask',
        'pygame',
        'werkzeug',
        'jinja2',
        'markupsafe',
        'itsdangerous',
        'click',
        'blinker',
        'numpy',
        'wave',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='LugeTimer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
'''
    
    with open('LugeTimer.spec', 'w') as f:
        f.write(spec_content)
    
    print_status("Created PyInstaller spec file", "SUCCESS")

def build_executable():
    """Build the executable using PyInstaller"""
    print_status("Building executable...", "INFO")
    
    try:
        # Run PyInstaller
        result = subprocess.run([
            'pyinstaller',
            '--clean',
            '--onefile',
            '--name=LugeTimer',
            '--add-data=templates;templates',
            '--add-data=static;static',
            '--add-data=config.py;.',
            '--add-data=audio;audio',
            '--hidden-import=flask',
            '--hidden-import=pygame',
            '--hidden-import=werkzeug',
            '--hidden-import=jinja2',
            '--hidden-import=markupsafe',
            '--hidden-import=itsdangerous',
            '--hidden-import=click',
            '--hidden-import=blinker',
            '--hidden-import=numpy',
            '--hidden-import=wave',
            'app.py'
        ], check=True, capture_output=True, text=True)
        
        print_status("Executable built successfully", "SUCCESS")
        return True
        
    except subprocess.CalledProcessError as e:
        print_status(f"Build failed: {e}", "ERROR")
        print_status(f"Error output: {e.stderr}", "ERROR")
        return False

def create_launcher_script():
    """Create a simple launcher script for the executable"""
    launcher_content = '''@echo off
echo Starting Luge Timing Sequence Controller...
echo.
echo The application will open in your default web browser.
echo If it doesn't open automatically, go to: http://localhost:5000
echo.
echo Press Ctrl+C to stop the application.
echo.
LugeTimer.exe
pause
'''
    
    with open('Launch_LugeTimer.bat', 'w') as f:
        f.write(launcher_content)
    
    print_status("Created launcher script", "SUCCESS")

def create_readme():
    """Create a README file for the executable"""
    readme_content = '''# Luge Timing Sequence Controller - Windows Executable

## Quick Start

1. **Double-click** `Launch_LugeTimer.bat` to start the application
2. **Wait** for the application to start (you'll see a console window)
3. **Open your web browser** and go to: http://localhost:5000
4. **Use the web interface** to control your timing sequences

## Features

- ✅ Three-beep timing sequence with configurable delays
- ✅ Real-time countdown displays
- ✅ Stop button to interrupt sequences
- ✅ Gate open phase with auto-reset
- ✅ Works on any Windows computer (no installation required)
- ✅ Accessible from any device on the same network

## Audio Files

The application includes test beep sounds. To use your own audio files:

1. Replace the files in the `audio` folder:
   - `beep1.wav` - Short beep
   - `double_beep.wav` - Short double-beep
   - `long_beep.wav` - Long beep (gate open cue)

2. Restart the application

## Network Access

Once running, you can access the application from:
- **This computer**: http://localhost:5000
- **Other devices on network**: http://[this-computer-ip]:5000

## Troubleshooting

- **If the browser doesn't open automatically**: Manually go to http://localhost:5000
- **If you get a firewall warning**: Allow the application through your firewall
- **If audio doesn't work**: Check your system volume and audio settings
- **To stop the application**: Close the console window or press Ctrl+C

## System Requirements

- Windows 7 or later
- No additional software installation required
- Internet connection (for initial setup only)

---
**Happy Timing! 🏁⏱️**
'''
    
    with open('README_Windows.txt', 'w') as f:
        f.write(readme_content)
    
    print_status("Created README file", "SUCCESS")

def main():
    """Main build process"""
    print("🏁 Building Windows Executable for Luge Timing Sequence Controller")
    print("=" * 60)
    print()
    
    # Check if we're in the right directory
    if not os.path.exists('app.py'):
        print_status("Error: app.py not found. Please run this script from the project directory.", "ERROR")
        return False
    
    # Install PyInstaller
    if not install_pyinstaller():
        return False
    
    # Create spec file
    create_spec_file()
    
    # Build executable
    if not build_executable():
        return False
    
    # Create launcher script
    create_launcher_script()
    
    # Create README
    create_readme()
    
    # Check if build was successful
    exe_path = os.path.join('dist', 'LugeTimer.exe')
    if os.path.exists(exe_path):
        print()
        print("🎉 Build completed successfully!")
        print("=" * 60)
        print()
        print("📁 Generated files:")
        print(f"  ✅ {exe_path}")
        print("  ✅ Launch_LugeTimer.bat")
        print("  ✅ README_Windows.txt")
        print()
        print("📦 Distribution package:")
        print("  Copy these files to distribute:")
        print("  - dist/LugeTimer.exe")
        print("  - Launch_LugeTimer.bat")
        print("  - README_Windows.txt")
        print("  - audio/ (folder with beep files)")
        print()
        print("🚀 To test the executable:")
        print("  1. Double-click Launch_LugeTimer.bat")
        print("  2. Open http://localhost:5000 in your browser")
        print()
        return True
    else:
        print_status("Build failed - executable not found", "ERROR")
        return False

if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1) 