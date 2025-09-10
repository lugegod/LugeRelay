#!/usr/bin/env python3
"""
Test script for Luge Timing Sequence Controller
This script verifies the application setup and dependencies
"""

import os
import sys
import importlib

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

def test_python_version():
    """Test Python version"""
    version = sys.version_info
    if version.major >= 3 and version.minor >= 7:
        print_status(f"Python {version.major}.{version.minor}.{version.micro} - OK", "SUCCESS")
        return True
    else:
        print_status(f"Python {version.major}.{version.minor}.{version.micro} - Requires Python 3.7+", "ERROR")
        return False

def test_dependencies():
    """Test required Python packages"""
    required_packages = [
        'flask',
        'pygame',
        'werkzeug',
        'jinja2'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            importlib.import_module(package)
            print_status(f"{package} - OK", "SUCCESS")
        except ImportError:
            print_status(f"{package} - Missing", "ERROR")
            missing_packages.append(package)
    
    return len(missing_packages) == 0

def test_file_structure():
    """Test if all required files exist"""
    required_files = [
        'app.py',
        'config.py',
        'requirements.txt',
        'templates/index.html',
        'static/countdown.js'
    ]
    
    missing_files = []
    
    for file_path in required_files:
        if os.path.exists(file_path):
            print_status(f"{file_path} - OK", "SUCCESS")
        else:
            print_status(f"{file_path} - Missing", "ERROR")
            missing_files.append(file_path)
    
    return len(missing_files) == 0

def test_audio_directory():
    """Test audio directory and files"""
    audio_dir = 'audio'
    
    if not os.path.exists(audio_dir):
        print_status(f"Creating {audio_dir} directory", "INFO")
        os.makedirs(audio_dir, exist_ok=True)
    
    required_audio_files = [
        'beep1.wav',
        'double_beep.wav', 
        'long_beep.wav'
    ]
    
    missing_audio = []
    
    for audio_file in required_audio_files:
        audio_path = os.path.join(audio_dir, audio_file)
        if os.path.exists(audio_path):
            print_status(f"audio/{audio_file} - OK", "SUCCESS")
        else:
            print_status(f"audio/{audio_file} - Missing", "WARNING")
            missing_audio.append(audio_file)
    
    if missing_audio:
        print_status("Please add the following audio files to the audio/ directory:", "WARNING")
        for file in missing_audio:
            print(f"  - {file}")
    
    return len(missing_audio) == 0

def test_audio_system():
    """Test pygame audio system"""
    try:
        import pygame
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
        print_status("Audio system - OK", "SUCCESS")
        pygame.mixer.quit()
        return True
    except Exception as e:
        print_status(f"Audio system - Error: {e}", "ERROR")
        return False

def test_flask_app():
    """Test Flask app import"""
    try:
        # Temporarily modify sys.path to import app
        sys.path.insert(0, os.getcwd())
        from app import app as flask_app
        print_status("Flask app - OK", "SUCCESS")
        return True
    except Exception as e:
        print_status(f"Flask app - Error: {e}", "ERROR")
        return False

def main():
    """Run all tests"""
    print("🏁 Luge Timing Sequence Controller - Setup Test")
    print("=" * 50)
    print()
    
    tests = [
        ("Python Version", test_python_version),
        ("Dependencies", test_dependencies),
        ("File Structure", test_file_structure),
        ("Audio Directory", test_audio_directory),
        ("Audio System", test_audio_system),
        ("Flask App", test_flask_app),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        print("-" * len(test_name))
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print_status(f"Test failed with exception: {e}", "ERROR")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("SUMMARY:")
    print("=" * 50)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        color = "\033[92m" if result else "\033[91m"
        reset = "\033[0m"
        print(f"{color}{status}{reset} {test_name}")
    
    print(f"\n{passed}/{total} tests passed")
    
    if passed == total:
        print_status("All tests passed! The application is ready to run.", "SUCCESS")
        print("\nTo start the application:")
        print("1. Add your audio files to the audio/ directory")
        print("2. Run: python app.py")
        print("3. Open: http://localhost:5000")
    else:
        print_status("Some tests failed. Please fix the issues above.", "WARNING")

if __name__ == "__main__":
    main() 