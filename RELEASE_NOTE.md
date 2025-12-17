# Release Note - Version 1.0.1
## Date: 2025-12-10

### 🐛 Bug Fixes

#### Core Detection Issues
- **Fixed Screen Capture Bug**: Resolved an issue where region-based screen capture wasn't actually capturing images, causing the monitoring loop to fail
- **Improved OCR Detection**: Fixed aggressive image preprocessing that was converting images to binary format, making EasyOCR unable to detect text
- **Optimized Performance**: Implemented optimized region capture (80% width, 30% height from top) for faster OCR processing

#### Configuration Updates
- **Lowered OCR Confidence Threshold**: Changed default from 0.7 to 0.5 to improve text detection rates
- **Better Error Handling**: Fixed variable scoping issues in the monitoring loop that caused crashes

### ✅ Improvements

#### User Experience
- ✅ Removed verbose logging - only ERROR level messages show in console
- ✅ Computer name is now displayed in monitoring status
- ✅ Added status display every 10 seconds showing:
  - Number of checks performed
  - Screenshots taken
  - Detections found
- ✅ Optimized codebase for better CPU performance

#### Testing
- Created comprehensive test scripts for OCR detection
- Added integration tests for monitoring loop
- Verified detection of "Live will end in..." trigger text

### 📝 Technical Details

#### Files Modified
- `src/core/screen_capture.py` - Fixed region capture implementation
- `src/core/ocr_detector.py` - Simplified preprocessing for EasyOCR
- `src/config/settings.py` - Updated default confidence threshold
- `src/main_v3.py` - Added optimized monitoring with status display
- `src/utils/logger_v2.py` - Improved logging with reduced verbosity

#### Known Issues
- Monitoring loop may stop after first cycle (requires further investigation)
- Telegram notifications may show event loop warnings (non-blocking)

### 🚀 Next Steps
1. Investigate and fix monitoring loop issue
2. Test with real jigsaw captchas
3. Optimize YOLO detection performance
4. Add unit tests for all modules

---

**Summary**: This release fixes critical detection issues that were preventing the AutoSolve application from detecting captchas. The application can now successfully detect trigger text and should be able to identify jigsaw captchas when they appear on screen.