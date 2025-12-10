# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AutoSolve is a Python-based automated captcha detection and solving system that monitors computer screens for jigsaw captchas, particularly during live streaming scenarios. The project uses OCR (Optical Character Recognition) and YOLO (You Only Look Once) deep learning models to detect and solve captchas automatically.

## Core Architecture

The system operates as a continuous monitoring loop with the following key components:

### Monitoring Loop (The Core Logic)
The program enters an infinite loop that repeats every `check_interval` (default: 10 seconds).

### Step A: Screen Capture
- Takes a screenshot of the current screen
- Ensures proper handling of high-DPI displays
- Screenshots are stored in `captured_images` folder

### Step B: "Live will end in..." Detection (High Priority)
- Scans the screenshot for trigger text using OCR
- Looks for phrases like: "Live will end in", "ending in", etc.
- If found, triggers "Critical Mode" for immediate jigsaw captcha checking

### Step C: Jigsaw Captcha Detection
When trigger text is found:
- Runs Jigsaw Detector with high sensitivity (low threshold)
- **Primary Algorithm**: Uses YOLO model to find the puzzle piece
- **Fallback Algorithm**: If AI detection fails, searches for circular patterns and edge density (common properties of jigsaw pieces)

### Step D: Action (Notification vs. Auto-Solve)
If a Jigsaw Captcha is detected:
1. **Auto-Solve Attempt**: Currently a simulation/placeholder (waits 1 second and returns False)
   - Note: Needs implementation of actual mouse-dragging logic with human-like movements
2. **Notification**: Since solve fails, sends Telegram notification:
   - Message: "CAPTCHA DETECTED... Manual intervention required!"
   - Includes the screenshot as attachment

### Step E: Secondary Checks (Low Priority)
If "Live will end in..." was NOT found:
- **General Captcha**: Looks for generic captcha patterns
- **"Start" Button**: Checks if stream has finished and Start button appears
- If true, sends notification

## Key Configuration

### Model Files
- **YOLO Model**: `Model/100824-YOLOv8.pt` (46MB) - Primary detection model for jigsaw pieces

### Telegram Configuration
```python
TELEGRAM_BOT_TOKEN = "7911746488:AAH6dh-F1yIJfF9fo06rB8aymMe97I91x8c"
TELEGRAM_CHAT_ID = "-1002348216355"
```

## Error Handling & Maintenance

### Cleanup
- Automatically deletes old screenshots from `captured_images` folder to save space

### Resilience
- Internet connectivity: Retries Telegram messages 3 times
- Crash prevention: If program crashes repeatedly, pauses to prevent infinite error loops

## User Experience Requirements

The program must be:
1. **Easy to Use**: End-user should be able to double-click and run the program
2. **Verifiable**: Users can test program settings (notification test, quick checkup)
3. **Identifiable**: Users can enter their computer name (shown in Telegram notifications)
4. **Reliable**: Capable of running 24/7 to monitor and auto-solve captchas

## Technical Implementation Notes

### Detection Priority System
1. **High Priority**: "Live will end in..." text detection
2. **Critical Mode**: High-sensitivity jigsaw detection (low threshold)
3. **Secondary Checks**: General captcha patterns and "Start" button detection

### Auto-Solve Strategy
Current state: Placeholder simulation
- Needs implementation of human-like mouse dragging
- Should mimic natural mouse movements for anti-detection

### Image Processing
- Screenshots stored in `captured_images` folder
- Automatic cleanup of old images
- High-DPI display support

## Development Setup

### Project Structure
```
AutoSolve/
├── Model/
│   └── 100824-YOLOv8.pt (46MB YOLO model)
├── captured_images/ (created at runtime)
├── readme.txt (this file)
└── CLAUDE.md (this file)
```

### Anticipated Dependencies
Based on described functionality:
- `pyautogui` - Screen capture and mouse control
- `ultralytics` - YOLO model loading and inference
- `easyocr` or `pytesseract` - OCR for text detection
- `python-telegram-bot` - Telegram bot integration
- `opencv-python` - Image processing and pattern detection
- `numpy` - Array operations
- `torch` and `torchvision` - PyTorch for YOLO model
- `Pillow` - Image manipulation
- `tkinter` or `PyQt` - GUI for user settings (optional for double-click executable)

## Security Considerations

This project involves:
- Full screen capture capabilities
- Automated mouse control
- Telegram bot integration with hardcoded credentials
- OCR and AI model processing

Ensure proper user consent and compliance with terms of service for any platform where this automation is deployed.

## Deployment Notes

For end-user ease of use:
- Package as standalone executable (e.g., using PyInstaller)
- Include model file in the package
- Create simple GUI for initial setup (computer name, test notifications)
- Add system tray icon for 24/7 operation
- Include start-up option for automatic launch on boot