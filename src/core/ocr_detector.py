"""
OCR detector module for AutoSolve.
Detects trigger text using Optical Character Recognition.
"""

import time
import cv2
import numpy as np
from PIL import Image
from typing import List, Tuple, Dict, Optional, Any
import easyocr
import re
from dataclasses import dataclass

from config.settings import settings
from utils.logger import get_logger
from config.constants import OCR_TRIGGER_PHRASES


@dataclass
class DetectionResult:
    """Result of OCR detection."""
    text: str
    confidence: float
    bbox: Tuple[int, int, int, int]  # (left, top, right, bottom)
    trigger_type: Optional[str] = None
    timestamp: float = 0.0


class OCRDetector:
    """OCR-based text detector for captcha triggers."""

    def __init__(
        self,
        languages: List[str] = None,
        confidence_threshold: float = None,
        gpu_enabled: bool = True,
        text_detector: str = 'easyocr'  # or 'tesseract'
    ):
        self.logger = get_logger(f"{__name__}.OCRDetector")

        # Configuration
        self.languages = languages or ['en', 'ch_sim']
        self.confidence_threshold = confidence_threshold or settings.config.detection.ocr_confidence_threshold
        self.gpu_enabled = gpu_enabled and settings.config.detection.enable_gpu
        self.text_detector = text_detector

        # Compile trigger phrase patterns
        self.trigger_patterns = self._compile_trigger_patterns()

        # Initialize OCR reader
        self.reader = None
        self._initialize_ocr()

        # Performance tracking
        self.detection_times = []
        self.total_detections = 0
        self.trigger_detections = 0

        self.logger.info(
            f"OCR Detector initialized: {text_detector}, "
            f"languages: {self.languages}, "
            f"GPU: {self.gpu_enabled}"
        )

    def _compile_trigger_patterns(self) -> List[Tuple[re.Pattern, str]]:
        """Compile regex patterns for trigger phrases."""
        patterns = []

        for phrase in OCR_TRIGGER_PHRASES:
            # Create flexible regex pattern
            # Case insensitive, allow extra characters between words
            words = phrase.split()
            pattern = '.*?'.join([re.escape(word) for word in words])

            # Add word boundaries and make case insensitive
            full_pattern = r'\b' + pattern + r'\b'

            try:
                compiled = re.compile(full_pattern, re.IGNORECASE)
                patterns.append((compiled, phrase))
                self.logger.debug(f"Compiled trigger pattern: {phrase}")
            except re.error as e:
                self.logger.warning(f"Failed to compile pattern '{phrase}': {e}")

        return patterns

    def _initialize_ocr(self):
        """Initialize the OCR engine."""
        try:
            if self.text_detector == 'easyocr':
                self._initialize_easyocr()
            elif self.text_detector == 'tesseract':
                self._initialize_tesseract()
            else:
                raise ValueError(f"Unsupported OCR engine: {self.text_detector}")

        except Exception as e:
            self.logger.error(f"Failed to initialize OCR: {e}")
            raise

    def _initialize_easyocr(self):
        """Initialize EasyOCR reader."""
        try:
            self.reader = easyocr.Reader(
                self.languages,
                gpu=self.gpu_enabled,
                download_enabled=True,
                detector=True,
                recognizer=True
            )
            self.logger.info("EasyOCR reader initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize EasyOCR: {e}")
            # Fallback to CPU if GPU fails
            if self.gpu_enabled:
                self.logger.info("Falling back to CPU for EasyOCR")
                self.gpu_enabled = False
                self.reader = easyocr.Reader(
                    self.languages,
                    gpu=False,
                    download_enabled=True
                )
            else:
                raise

    def _initialize_tesseract(self):
        """Initialize Tesseract OCR."""
        try:
            import pytesseract
            # Test if Tesseract is available
            pytesseract.get_tesseract_version()
            self.logger.info("Tesseract OCR initialized successfully")
        except ImportError:
            self.logger.error("pytesseract not installed")
            raise
        except Exception as e:
            self.logger.error(f"Tesseract not found or not working: {e}")
            raise

    def detect_text(
        self,
        image: Image.Image,
        region: Optional[Tuple[int, int, int, int]] = None,
        min_text_length: int = 3
    ) -> List[DetectionResult]:
        """
        Detect text in an image and check for trigger phrases.

        Args:
            image: PIL Image to analyze
            region: Optional region to crop (left, top, right, bottom)
            min_text_length: Minimum text length to consider

        Returns:
            List of detection results
        """
        start_time = time.time()

        try:
            # Crop to region if specified
            if region:
                image = image.crop(region)
                self.logger.debug(f"Cropped image to region: {region}")

            # Convert to numpy array
            img_array = np.array(image)

            # Preprocess image for better OCR
            img_array = self._preprocess_image(img_array)

            # Perform OCR
            detections = self._perform_ocr(img_array, region)

            # Filter and process detections
            filtered_detections = self._process_detections(
                detections,
                min_text_length
            )

            # Update statistics
            detection_time = time.time() - start_time
            self.detection_times.append(detection_time)
            self.total_detections += 1

            # Check if any trigger phrases were found
            for detection in filtered_detections:
                if detection.trigger_type:
                    self.trigger_detections += 1
                    self.logger.info(
                        f"Trigger phrase detected: '{detection.text}' "
                        f"(confidence: {detection.confidence:.2f})"
                    )

            # Keep only recent performance data
            if len(self.detection_times) > 100:
                self.detection_times = self.detection_times[-100:]

            self.logger.debug(
                f"OCR completed in {detection_time:.3f}s, "
                f"found {len(filtered_detections)} text regions"
            )

            return filtered_detections

        except Exception as e:
            self.logger.error(f"OCR detection failed: {e}")
            return []

    def _preprocess_image(self, img_array: np.ndarray) -> np.ndarray:
        """Preprocess image for better OCR accuracy."""
        try:
            # For EasyOCR, minimal preprocessing works better
            if self.text_detector == 'easyocr':
                # Just ensure RGB format, no heavy preprocessing
                if len(img_array.shape) == 2:
                    # Convert grayscale to RGB
                    return cv2.cvtColor(img_array, cv2.COLOR_GRAY2RGB)
                return img_array

            # For Tesseract, do more aggressive preprocessing
            # Convert to grayscale if needed
            if len(img_array.shape) == 3:
                img_gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            else:
                img_gray = img_array

            # Apply contrast enhancement
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            img_enhanced = clahe.apply(img_gray)

            # Apply denoising
            img_denoised = cv2.fastNlMeansDenoising(img_enhanced)

            # Threshold to get binary image
            _, img_binary = cv2.threshold(
                img_denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
            )

            return img_binary

        except Exception as e:
            self.logger.warning(f"Image preprocessing failed: {e}")
            return img_array

    def _perform_ocr(
        self,
        img_array: np.ndarray,
        region: Optional[Tuple[int, int, int, int]] = None
    ) -> List[Dict[str, Any]]:
        """Perform OCR using the configured engine."""
        if self.text_detector == 'easyocr':
            return self._easyocr_detect(img_array)
        elif self.text_detector == 'tesseract':
            return self._tesseract_detect(img_array, region)
        else:
            return []

    def _easyocr_detect(self, img_array: np.ndarray) -> List[Dict[str, Any]]:
        """Perform OCR using EasyOCR."""
        try:
            # EasyOCR expects RGB images (preprocessing already handles this)
            if len(img_array.shape) == 2:
                img_array = cv2.cvtColor(img_array, cv2.COLOR_GRAY2RGB)

            results = self.reader.readtext(
                img_array,
                detail=1,
                paragraph=False,
                width_ths=0.7,
                height_ths=0.7
            )

            detections = []
            for (bbox, text, confidence) in results:
                if confidence > 0:  # Filter out very low confidence
                    # Convert bbox to consistent format
                    left = min([point[0] for point in bbox])
                    top = min([point[1] for point in bbox])
                    right = max([point[0] for point in bbox])
                    bottom = max([point[1] for point in bbox])

                    detections.append({
                        'text': text.strip(),
                        'confidence': confidence,
                        'bbox': (int(left), int(top), int(right), int(bottom))
                    })

            return detections

        except Exception as e:
            self.logger.error(f"EasyOCR detection failed: {e}")
            return []

    def _tesseract_detect(
        self,
        img_array: np.ndarray,
        region: Optional[Tuple[int, int, int, int]] = None
    ) -> List[Dict[str, Any]]:
        """Perform OCR using Tesseract."""
        try:
            import pytesseract
            from PIL import Image

            # Convert to PIL Image
            pil_image = Image.fromarray(img_array)

            # Get detailed OCR data
            data = pytesseract.image_to_data(
                pil_image,
                output_type=pytesseract.Output.DICT,
                config='--psm 6'  # Assume uniform block of text
            )

            detections = []
            n_boxes = len(data['text'])

            for i in range(n_boxes):
                text = data['text'][i].strip()
                if text and int(data['conf'][i]) > 0:
                    left = data['left'][i]
                    top = data['top'][i]
                    right = left + data['width'][i]
                    bottom = top + data['height'][i]

                    # Adjust for region offset
                    if region:
                        left += region[0]
                        right += region[0]
                        top += region[1]
                        bottom += region[1]

                    detections.append({
                        'text': text,
                        'confidence': data['conf'][i] / 100.0,
                        'bbox': (left, top, right, bottom)
                    })

            return detections

        except Exception as e:
            self.logger.error(f"Tesseract detection failed: {e}")
            return []

    def _process_detections(
        self,
        detections: List[Dict[str, Any]],
        min_text_length: int
    ) -> List[DetectionResult]:
        """Process and filter OCR detections."""
        results = []
        current_time = time.time()

        for detection in detections:
            text = detection['text']
            confidence = detection['confidence']
            bbox = detection['bbox']

            # Filter by text length
            if len(text) < min_text_length:
                continue

            # Filter by confidence threshold
            if confidence < self.confidence_threshold:
                continue

            # Check for trigger phrases
            trigger_type = self._check_trigger_phrase(text)

            result = DetectionResult(
                text=text,
                confidence=confidence,
                bbox=bbox,
                trigger_type=trigger_type,
                timestamp=current_time
            )

            results.append(result)

        return results

    def _check_trigger_phrase(self, text: str) -> Optional[str]:
        """Check if text contains any trigger phrases."""
        for pattern, phrase in self.trigger_patterns:
            if pattern.search(text):
                return phrase
        return None

    def has_trigger_phrase(self, detections: List[DetectionResult]) -> bool:
        """Check if any detections contain trigger phrases."""
        return any(d.trigger_type is not None for d in detections)

    def get_trigger_detections(
        self,
        detections: List[DetectionResult]
    ) -> List[DetectionResult]:
        """Get only the detections that contain trigger phrases."""
        return [d for d in detections if d.trigger_type is not None]

    def update_confidence_threshold(self, threshold: float):
        """Update the confidence threshold for detections."""
        if 0 <= threshold <= 1:
            self.confidence_threshold = threshold
            self.logger.info(f"Updated OCR confidence threshold to {threshold}")
        else:
            self.logger.warning(f"Invalid confidence threshold: {threshold}")

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get OCR performance statistics."""
        if not self.detection_times:
            return {
                'avg_detection_time': 0,
                'total_detections': 0,
                'trigger_detections': 0,
                'trigger_rate': 0
            }

        avg_time = sum(self.detection_times) / len(self.detection_times)
        trigger_rate = (
            self.trigger_detections / self.total_detections
            if self.total_detections > 0 else 0
        )

        return {
            'avg_detection_time': avg_time,
            'total_detections': self.total_detections,
            'trigger_detections': self.trigger_detections,
            'trigger_rate': trigger_rate,
            'confidence_threshold': self.confidence_threshold,
            'ocr_engine': self.text_detector,
            'gpu_enabled': self.gpu_enabled
        }

    def reset_statistics(self):
        """Reset detection statistics."""
        self.detection_times.clear()
        self.total_detections = 0
        self.trigger_detections = 0
        self.logger.info("OCR detection statistics reset")

    def __del__(self):
        """Cleanup resources."""
        if hasattr(self, 'reader') and self.reader is not None:
            # EasyOCR doesn't have explicit cleanup, but we can try
            try:
                del self.reader
            except:
                pass