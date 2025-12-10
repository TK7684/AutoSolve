# AutoSolve

An automated captcha detection and solving program that monitors computer screens 24/7, using OCR and YOLOv8 for detection, with Telegram notifications.

## Features

- 24/7 screen monitoring for captcha detection
- OCR-based text detection for trigger phrases
- YOLOv8 AI model for jigsaw captcha detection
- Telegram notifications with screenshots
- Easy-to-use GUI for configuration
- System tray integration for background operation

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/AutoSolve.git
   cd AutoSolve
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure environment:
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

## Usage

1. Run the program:
   ```bash
   python src/main.py
   ```

2. Configure your settings in the GUI:
   - Set your computer name
   - Test Telegram notifications
   - Adjust monitoring intervals

3. Click "Start Monitoring" to begin 24/7 captcha detection

## Requirements

- Python 3.8+
- Windows OS (for screen capture)
- Telegram Bot Token and Chat ID

## License

MIT License