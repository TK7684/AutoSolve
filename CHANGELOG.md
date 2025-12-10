# Changelog

All notable changes to AutoSolve will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2024-12-10

### Added
- Initial implementation of AutoSolve captcha detection and solving system

#### Core Features
- Screen capture module with high-DPI and multi-monitor support
- OCR-based text detection for trigger phrases ("Live will end in", etc.)
- YOLOv8-based jigsaw captcha detection with fallback algorithms
- Telegram notification system with retry logic and cooldown
- Placeholder captcha solver with human-like mouse movements
- 24/7 monitoring loop with configurable intervals

#### Configuration
- Comprehensive settings management with environment variables and YAML support
- Settings GUI with tabs for easy configuration
- Real-time settings validation and updates
- Performance monitoring and debug options

#### Technical Implementation
- Structured logging with colored console output and file rotation
- Human-like mouse controller with multiple movement patterns
- GPU acceleration support for YOLO detection
- Automatic cleanup of old screenshots
- Graceful shutdown handling

#### Dependencies
- Python 3.8+ support
- PyTorch and Ultralytics for YOLO model
- EasyOCR for text detection
- python-telegram-bot for notifications
- OpenCV for image processing
- Tkinter for GUI

### Documentation
- Comprehensive README with installation and usage instructions
- API documentation in code docstrings
- Configuration examples in .env.example

### Known Limitations
- Auto-solve functionality is placeholder/simulation only
- Requires manual configuration of Telegram bot
- Windows-optimized (screen capture and mouse control)
- YOLO model training not included (uses pre-trained model)

### Security Notes
- Telegram credentials should be kept secure
- Screen capture permissions may be required
- Mouse control requires administrator privileges on some systems