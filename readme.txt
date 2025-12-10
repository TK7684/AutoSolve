Monitoring Loop (The Core Logic)
The program enters an infinite loop that repeats every check_interval (default: 10 seconds).

Step A: Screen Capture

It takes a screenshot of your current screen ensuring it handles high-DPI displays correctly.
Step B: "Live will end in..." Detection (High Priority)

It first scans the screenshot for text like "Live will end in", "ending in", etc., using OCR (Optical Character Recognition).
If found: This triggers the "Critical Mode". It immediately checks for a Jigsaw Captcha.
Step C: Jigsaw Captcha Detection

If Text WAS found: It runs the Jigsaw Detector with high sensitivity (low threshold) because it expects a captcha to be there.
Algorithm:
YOLO: Uses the AI model to find the puzzle piece.
Fallback: If AI detection fails, it looks for circular patterns and edge density (common properties of jigsaw pieces).
Step D: Action (Notification vs. Auto-Solve)

If a Jigsaw Captcha is detected:
Auto-Solve (Current State): the auto-solve function is currently a simulation/placeholder (it waits 1 second and returns False).
Notification: Since the "solve" fails, it sends a Telegram Notification ("CAPTCHA DETECTED... Manual intervention required!") with the screenshot.
Note: use actual mouse-dragging logic (human like drag)
Step E: Secondary Checks (Low Priority)

If "Live will end in..." was NOT found, it performs lower-priority checks:
General Captcha: Looks for generic captcha patterns.
"Start": Checks if the stream has finished Start button appears. If true, it notifies you.
3. Error Handling & Maintenance
Cleanup: Automatically deletes old screenshots from the captured_images folder to save space.
Resilience: If the internet cuts out, it retries Telegram messages 3 times. If the program crashes repeatedly, it pauses to prevent infinite error loops.

USE model 100824-YOLOv8.pt
# Telegram Configuration
TELEGRAM_BOT_TOKEN=7911746488:AAH6dh-F1yIJfF9fo06rB8aymMe97I91x8c
TELEGRAM_CHAT_ID=-1002348216355


the program should be able to:
1. very easy to use, end-user should be able to just double click and the program should be running
2. verify they program setting such as notification test, fast check up 
3. let user enter their computer name as it will show in telegram channel, so they know which computer is sending notification.
4. run 24/7 to monitor the captcha and auto solve them