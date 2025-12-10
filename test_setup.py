#!/usr/bin/env python3
"""
Test script to verify AutoSolve setup and dependencies.
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))


def test_imports():
    """Test if all required modules can be imported."""
    print("Testing imports...")

    try:
        # Configuration
        from config.settings import settings
        print("✓ Settings module imported")
    except Exception as e:
        print(f"✗ Settings module failed: {e}")
        return False

    try:
        # Utils
        from utils.logger import get_logger
        print("✓ Logger module imported")
    except Exception as e:
        print(f"✗ Logger module failed: {e}")
        return False

    try:
        # Core modules
        from core.screen_capture import ScreenCapture
        from core.ocr_detector import OCRDetector
        from core.jigsaw_detector import JigsawDetector
        from core.telegram_notifier import TelegramNotifier
        from core.captcha_solver import CaptchaSolver
        print("✓ All core modules imported")
    except Exception as e:
        print(f"✗ Core modules failed: {e}")
        return False

    try:
        # GUI
        from gui.settings_window import SettingsWindow
        print("✓ GUI module imported")
    except Exception as e:
        print(f"✗ GUI module failed: {e}")
        return False

    return True


def test_dependencies():
    """Test if required dependencies are available."""
    print("\nTesting dependencies...")

    # Required packages
    required_packages = [
        'torch', 'torchvision', 'ultralytics', 'opencv-python',
        'numpy', 'Pillow', 'easyocr', 'pyautogui',
        'python-telegram-bot', 'requests', 'python-dotenv',
        'pyyaml', 'colorlog', 'rich', 'pytest'
    ]

    missing_packages = []

    for package in required_packages:
        try:
            if package == 'opencv-python':
                import cv2
            elif package == 'Pillow':
                import PIL
            elif package == 'python-dotenv':
                import dotenv
            elif package == 'python-telegram-bot':
                import telegram
            elif package == 'colorlog':
                import colorlog
            elif package == 'pyyaml':
                import yaml
            else:
                __import__(package)
            print(f"✓ {package}")
        except ImportError:
            print(f"✗ {package} - MISSING")
            missing_packages.append(package)

    if missing_packages:
        print(f"\nMissing packages: {', '.join(missing_packages)}")
        print("Install with: pip install " + " ".join(missing_packages))
        return False

    return True


def test_model():
    """Test if YOLO model exists."""
    print("\nTesting YOLO model...")

    model_path = Path("Model/100824-YOLOv8.pt")
    if model_path.exists():
        print(f"✓ Model found at {model_path}")
        print(f"  Size: {model_path.stat().st_size / (1024*1024):.1f} MB")
        return True
    else:
        print(f"✗ Model not found at {model_path}")
        return False


def test_configuration():
    """Test configuration loading."""
    print("\nTesting configuration...")

    try:
        from config.settings import settings

        # Check if configuration loaded
        config = settings.config
        print(f"✓ Configuration loaded")
        print(f"  Computer name: {config.monitoring.computer_name}")
        print(f"  Check interval: {config.detection.check_interval}s")
        print(f"  Telegram token: {'SET' if config.telegram.bot_token else 'NOT SET'}")
        print(f"  Telegram chat ID: {'SET' if config.telegram.chat_id else 'NOT SET'}")

        # Validate configuration
        if settings.validate():
            print("✓ Configuration is valid")
            return True
        else:
            print("✗ Configuration validation failed")
            return False

    except Exception as e:
        print(f"✗ Configuration test failed: {e}")
        return False


def test_screen_capture():
    """Test screen capture functionality."""
    print("\nTesting screen capture...")

    try:
        from core.screen_capture import ScreenCapture

        capturer = ScreenCapture()
        img, path = capturer.capture_screen(save_to_file=False)

        if img:
            print(f"✓ Screen capture successful")
            print(f"  Size: {img.size}")
            print(f"  Mode: {img.mode}")
            return True
        else:
            print("✗ Screen capture returned no image")
            return False

    except Exception as e:
        print(f"✗ Screen capture failed: {e}")
        return False


def test_logger():
    """Test logging functionality."""
    print("\nTesting logger...")

    try:
        from utils.logger import get_logger

        logger = get_logger("TestLogger")
        logger.info("This is a test message")

        # Check if log file was created
        log_file = Path("logs/autosolve.log")
        if log_file.exists():
            print("✓ Log file created")
        else:
            print("! Log file not created (may be created later)")

        print("✓ Logger working")
        return True

    except Exception as e:
        print(f"✗ Logger test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("=" * 50)
    print("AutoSolve Setup Test")
    print("=" * 50)

    tests = [
        ("Dependencies", test_dependencies),
        ("Imports", test_imports),
        ("Model", test_model),
        ("Configuration", test_configuration),
        ("Logger", test_logger),
        ("Screen Capture", test_screen_capture),
    ]

    results = []
    for name, test_func in tests:
        print(f"\n{'='*20} {name} {'='*20}")
        result = test_func()
        results.append((name, result))

    # Summary
    print("\n" + "=" * 50)
    print("Test Summary")
    print("=" * 50)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"{name}: {status}")

    print(f"\nOverall: {passed}/{total} tests passed")

    if passed == total:
        print("\n✓ All tests passed! AutoSolve is ready to run.")
        print("\nTo start the application:")
        print("  python run.py")
        print("\nOr double-click run.py if you're on Windows.")
    else:
        print("\n✗ Some tests failed. Please fix the issues above.")
        print("\nMake sure to:")
        print("1. Install missing dependencies: pip install -r requirements.txt")
        print("2. Set up your .env file with Telegram configuration")
        print("3. Ensure the YOLO model is in the Model/ directory")


if __name__ == "__main__":
    main()