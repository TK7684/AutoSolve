"""
Jigsaw detector module for AutoSolve.
Detects jigsaw puzzle captchas using YOLO and fallback algorithms.
"""

import time
import cv2
import numpy as np
from PIL import Image, ImageDraw
from typing import List, Tuple, Dict, Optional, Any
from pathlib import Path
from dataclasses import dataclass
import torch

try:
    from ultralytics import YOLO
except ImportError:
    YOLO = None

from config.settings import settings
from utils.logger import get_logger
from config.constants import YOLO_CLASS_NAMES, DetectionBox


@dataclass
class JigsawDetectionResult:
    """Result of jigsaw detection."""
    is_detected: bool
    confidence: float
    detection_method: str  # 'yolo' or 'fallback'
    boxes: List[DetectionBox]
    processing_time: float
    image_size: Tuple[int, int]


class JigsawDetector:
    """Detects jigsaw puzzles using YOLO with fallback algorithms."""

    def __init__(
        self,
        model_path: str = None,
        confidence_threshold: float = None,
        iou_threshold: float = None,
        enable_gpu: bool = None,
        fallback_enabled: bool = True
    ):
        self.logger = get_logger(f"{__name__}.JigsawDetector")

        # Configuration
        self.model_path = model_path or settings.config.paths.yolo_model_path
        self.confidence_threshold = confidence_threshold or settings.config.detection.yolo_confidence_threshold
        self.iou_threshold = iou_threshold or settings.config.detection.yolo_iou_threshold
        self.enable_gpu = enable_gpu if enable_gpu is not None else settings.config.detection.enable_gpu
        self.fallback_enabled = fallback_enabled

        # Initialize YOLO model
        self.model = None
        self.device = self._get_device()
        self.model_loaded = False

        # Performance tracking
        self.detection_times = []
        self.total_detections = 0
        self.successful_detections = 0
        self.fallback_used = 0

        self._load_model()

        self.logger.info(
            f"Jigsaw Detector initialized: model={self.model_path}, "
            f"device={self.device}, fallback={self.fallback_enabled}"
        )

    def _get_device(self) -> str:
        """Determine the best device for YOLO inference."""
        if not self.enable_gpu:
            return 'cpu'

        if torch.cuda.is_available():
            return 'cuda:0'
        elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            # Apple Silicon GPU
            return 'mps'
        else:
            self.logger.warning("GPU not available, falling back to CPU")
            return 'cpu'

    def _load_model(self):
        """Load the YOLO model."""
        model_path = Path(self.model_path)

        if not model_path.exists():
            self.logger.error(f"YOLO model not found at {self.model_path}")
            return

        if YOLO is None:
            self.logger.error("Ultralytics YOLO not installed")
            return

        try:
            self.logger.info(f"Loading YOLO model from {self.model_path}")

            # Load model with optimizations for CPU
            self.model = YOLO(str(model_path))

            # Optimize for CPU
            if self.device == 'cpu':
                # Set model to evaluation mode
                self.model.eval()

                # Disable gradients
                for param in self.model.model.parameters():
                    param.requires_grad = False

                # Use torch.jit.script for potential optimization
                try:
                    self.model.fuse()  # Fuse Conv2D + BatchNorm for speed
                except:
                    pass  # Not all models support fusion

            # Warm up the model with a dummy inference
            test_image = np.random.randint(0, 255, (640, 640, 3), dtype=np.uint8)
            with torch.no_grad():
                _ = self.model(test_image, verbose=False, device=self.device)

            self.model_loaded = True
            self.logger.info(
                f"YOLO model loaded successfully on {self.device}"
            )

        except Exception as e:
            self.logger.error(f"Failed to load YOLO model: {e}")
            self.model_loaded = False

    def detect_jigsaw(
        self,
        image: Image.Image,
        region: Optional[Tuple[int, int, int, int]] = None,
        use_fallback_if_needed: bool = True
    ) -> JigsawDetectionResult:
        """
        Detect jigsaw puzzle in the image.

        Args:
            image: PIL Image to analyze
            region: Optional region to crop (left, top, right, bottom)
            use_fallback_if_needed: Whether to use fallback if YOLO fails

        Returns:
            JigsawDetectionResult with detection information
        """
        start_time = time.time()

        try:
            # Crop to region if specified
            if region:
                image = image.crop(region)
                self.logger.debug(f"Cropped image to region: {region}")

            image_size = image.size

            # First try YOLO detection
            if self.model_loaded:
                result = self._detect_with_yolo(image)
                if result.is_detected:
                    self._update_statistics(True, 'yolo', time.time() - start_time)
                    return result

            # Fallback detection
            if self.fallback_enabled and use_fallback_if_needed:
                self.logger.debug("Using fallback detection method")
                result = self._detect_with_fallback(image)
                self._update_statistics(result.is_detected, 'fallback', time.time() - start_time)
                return result

            # No detection
            processing_time = time.time() - start_time
            self._update_statistics(False, 'none', processing_time)
            return JigsawDetectionResult(
                is_detected=False,
                confidence=0.0,
                detection_method='none',
                boxes=[],
                processing_time=processing_time,
                image_size=image_size
            )

        except Exception as e:
            self.logger.error(f"Jigsaw detection failed: {e}")
            processing_time = time.time() - start_time
            return JigsawDetectionResult(
                is_detected=False,
                confidence=0.0,
                detection_method='error',
                boxes=[],
                processing_time=processing_time,
                image_size=image.size if hasattr(image, 'size') else (0, 0)
            )

    def _detect_with_yolo(self, image: Image.Image) -> JigsawDetectionResult:
        """Detect jigsaw using YOLO model."""
        try:
            # Convert PIL to numpy array (RGB format)
            img_array = np.array(image)

            # Optimizations for CPU
            if self.device == 'cpu':
                # Resize image for faster processing on CPU
                # Keep aspect ratio
                height, width = img_array.shape[:2]
                if max(height, width) > 640:
                    scale = 640 / max(height, width)
                    new_height = int(height * scale)
                    new_width = int(width * scale)
                    img_array = cv2.resize(img_array, (new_width, new_height))

            # Run YOLO inference with optimized settings
            results = self.model(
                img_array,
                verbose=False,
                conf=self.confidence_threshold,
                iou=self.iou_threshold,
                device=self.device,
                # Optimizations for CPU
                half=False,  # Disable FP16 on CPU
                augment=False,  # Disable augmentation for faster inference
                classes=[0],  # Assuming class 0 is jigsaw/puzzle
                max_det=10  # Limit maximum detections
            )

            # Process results
            boxes = []
            max_confidence = 0.0

            # Get the first result (single image)
            result = results[0] if results else None

            if result is not None and result.boxes is not None:
                # Convert boxes to CPU if needed
                boxes_tensor = result.boxes.xyxy.cpu().numpy()
                conf_tensor = result.boxes.conf.cpu().numpy()
                cls_tensor = result.boxes.cls.cpu().numpy()

                for i in range(len(boxes_tensor)):
                    x1, y1, x2, y2 = boxes_tensor[i]
                    conf = float(conf_tensor[i])
                    cls_id = int(cls_tensor[i])

                    # Get class name
                    class_name = YOLO_CLASS_NAMES.get(cls_id, f'class_{cls_id}')

                    # Scale coordinates back if image was resized
                    if self.device == 'cpu' and max(image.size) > 640:
                        scale = max(image.size) / 640
                        x1 = int(x1 * scale)
                        y1 = int(y1 * scale)
                        x2 = int(x2 * scale)
                        y2 = int(y2 * scale)
                    else:
                        x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)

                    # Create detection box
                    detection_box = DetectionBox(
                        x1=x1,
                        y1=y1,
                        x2=x2,
                        y2=y2,
                        confidence=conf,
                        class_id=cls_id,
                        class_name=class_name
                    )

                    boxes.append(detection_box)
                    max_confidence = max(max_confidence, conf)

            # Check if we detected any jigsaw-related objects
            # For now, treat all detections as potential jigsaws
            jigsaw_boxes = boxes  # Since the model should be trained specifically for jigsaws

            return JigsawDetectionResult(
                is_detected=len(jigsaw_boxes) > 0,
                confidence=max_confidence,
                detection_method='yolo',
                boxes=jigsaw_boxes,
                processing_time=0.0,  # Will be set by caller
                image_size=image.size
            )

        except Exception as e:
            self.logger.error(f"YOLO detection failed: {e}")
            raise

    def _detect_with_fallback(self, image: Image.Image) -> JigsawDetectionResult:
        """Detect jigsaw using fallback algorithms."""
        start_time = time.time()

        try:
            # Convert to OpenCV format
            img_cv = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)

            # Method 1: Circle detection for puzzle pieces
            circles = self._detect_circles(gray)

            # Method 2: Edge density detection
            edge_boxes = self._detect_edge_density(gray)

            # Method 3: Contour-based detection
            contour_boxes = self._detect_contours(gray)

            # Combine results
            all_boxes = circles + edge_boxes + contour_boxes

            # Filter overlapping boxes
            filtered_boxes = self._filter_overlapping_boxes(all_boxes)

            # Calculate confidence based on number and quality of detections
            confidence = self._calculate_fallback_confidence(filtered_boxes, len(circles), len(edge_boxes), len(contour_boxes))

            processing_time = time.time() - start_time

            return JigsawDetectionResult(
                is_detected=len(filtered_boxes) > 0,
                confidence=confidence,
                detection_method='fallback',
                boxes=filtered_boxes,
                processing_time=processing_time,
                image_size=image.size
            )

        except Exception as e:
            self.logger.error(f"Fallback detection failed: {e}")
            return JigsawDetectionResult(
                is_detected=False,
                confidence=0.0,
                detection_method='fallback_error',
                boxes=[],
                processing_time=time.time() - start_time,
                image_size=image.size
            )

    def _detect_circles(self, gray: np.ndarray) -> List[DetectionBox]:
        """Detect circular patterns that might be puzzle pieces."""
        circles = []

        try:
            # Apply Gaussian blur
            blurred = cv2.GaussianBlur(gray, (9, 9), 2)

            # Detect circles
            detected_circles = cv2.HoughCircles(
                blurred,
                cv2.HOUGH_GRADIENT,
                dp=1.2,
                minDist=50,
                param1=50,
                param2=30,
                minRadius=20,
                maxRadius=100
            )

            if detected_circles is not None:
                detected_circles = np.round(detected_circles[0, :]).astype("int")

                for (x, y, r) in detected_circles:
                    confidence = min(1.0, (r - 20) / 50.0)  # Confidence based on size

                    box = DetectionBox(
                        x1=max(0, x - r),
                        y1=max(0, y - r),
                        x2=x + r,
                        y2=y + r,
                        confidence=confidence,
                        class_id=0,
                        class_name='circle'
                    )
                    circles.append(box)

        except Exception as e:
            self.logger.debug(f"Circle detection failed: {e}")

        return circles

    def _detect_edge_density(self, gray: np.ndarray) -> List[DetectionBox]:
        """Detect regions with high edge density (puzzle piece edges)."""
        boxes = []

        try:
            # Apply Canny edge detection
            edges = cv2.Canny(gray, 50, 150)

            # Create sliding window to find edge-dense regions
            window_size = 100
            stride = 50

            height, width = edges.shape
            for y in range(0, height - window_size, stride):
                for x in range(0, width - window_size, stride):
                    window = edges[y:y+window_size, x:x+window_size]
                    edge_density = np.sum(window > 0) / (window_size * window_size)

                    if edge_density > 0.15:  # Threshold for edge density
                        confidence = min(1.0, edge_density * 2)

                        box = DetectionBox(
                            x1=x,
                            y1=y,
                            x2=x + window_size,
                            y2=y + window_size,
                            confidence=confidence,
                            class_id=1,
                            class_name='edge_dense'
                        )
                        boxes.append(box)

        except Exception as e:
            self.logger.debug(f"Edge density detection failed: {e}")

        return boxes

    def _detect_contours(self, gray: np.ndarray) -> List[DetectionBox]:
        """Detect puzzle piece-like contours."""
        boxes = []

        try:
            # Apply threshold
            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

            # Find contours
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            for contour in contours:
                # Calculate contour properties
                area = cv2.contourArea(contour)
                if area < 500:  # Skip small contours
                    continue

                # Get bounding rectangle
                x, y, w, h = cv2.boundingRect(contour)

                # Calculate shape properties
                perimeter = cv2.arcLength(contour, True)
                if perimeter == 0:
                    continue

                circularity = 4 * np.pi * area / (perimeter * perimeter)
                aspect_ratio = w / h if h > 0 else 0

                # Check if it looks like a puzzle piece
                # Puzzle pieces typically have:
                # - Moderate circularity (not perfect circles)
                # - Reasonable aspect ratio
                if 0.3 < circularity < 0.8 and 0.5 < aspect_ratio < 2.0:
                    confidence = min(1.0, area / 5000.0)

                    box = DetectionBox(
                        x1=x,
                        y1=y,
                        x2=x + w,
                        y2=y + h,
                        confidence=confidence,
                        class_id=2,
                        class_name='contour'
                    )
                    boxes.append(box)

        except Exception as e:
            self.logger.debug(f"Contour detection failed: {e}")

        return boxes

    def _filter_overlapping_boxes(
        self,
        boxes: List[DetectionBox],
        iou_threshold: float = 0.5
    ) -> List[DetectionBox]:
        """Filter overlapping boxes using Non-Maximum Suppression."""
        if not boxes:
            return []

        # Sort boxes by confidence
        boxes.sort(key=lambda b: b.confidence, reverse=True)

        # Convert to numpy array for NMS
        box_array = np.array([[b.x1, b.y1, b.x2, b.y2] for b in boxes])
        confidence_array = np.array([b.confidence for b in boxes])

        # Apply NMS
        indices = cv2.dnn.NMSBoxes(
            box_array.tolist(),
            confidence_array.tolist(),
            self.confidence_threshold,
            iou_threshold
        )

        if len(indices) > 0:
            return [boxes[i[0]] for i in indices]
        else:
            return []

    def _calculate_fallback_confidence(
        self,
        boxes: List[DetectionBox],
        num_circles: int,
        num_edges: int,
        num_contours: int
    ) -> float:
        """Calculate confidence for fallback detection."""
        if not boxes:
            return 0.0

        # Base confidence from number of detections
        base_confidence = min(1.0, len(boxes) * 0.2)

        # Boost based on detection method diversity
        method_boost = 0.0
        if num_circles > 0:
            method_boost += 0.2
        if num_edges > 0:
            method_boost += 0.2
        if num_contours > 0:
            method_boost += 0.2

        # Average confidence of all boxes
        avg_confidence = np.mean([b.confidence for b in boxes]) if boxes else 0.0

        # Combine all factors
        total_confidence = min(1.0, base_confidence + method_boost + avg_confidence)

        return total_confidence

    def _update_statistics(
        self,
        success: bool,
        method: str,
        processing_time: float
    ):
        """Update detection statistics."""
        self.detection_times.append(processing_time)
        self.total_detections += 1

        if success:
            self.successful_detections += 1
        if method == 'fallback':
            self.fallback_used += 1

        # Keep only recent performance data
        if len(self.detection_times) > 100:
            self.detection_times = self.detection_times[-100:]

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get detection performance statistics."""
        if not self.detection_times:
            return {
                'avg_detection_time': 0,
                'total_detections': 0,
                'success_rate': 0,
                'fallback_rate': 0,
                'model_loaded': self.model_loaded
            }

        avg_time = sum(self.detection_times) / len(self.detection_times)
        success_rate = (
            self.successful_detections / self.total_detections
            if self.total_detections > 0 else 0
        )
        fallback_rate = (
            self.fallback_used / self.total_detections
            if self.total_detections > 0 else 0
        )

        return {
            'avg_detection_time': avg_time,
            'total_detections': self.total_detections,
            'success_rate': success_rate,
            'fallback_rate': fallback_rate,
            'model_loaded': self.model_loaded,
            'device': self.device,
            'confidence_threshold': self.confidence_threshold
        }

    def update_thresholds(
        self,
        confidence_threshold: Optional[float] = None,
        iou_threshold: Optional[float] = None
    ):
        """Update detection thresholds."""
        if confidence_threshold is not None and 0 <= confidence_threshold <= 1:
            self.confidence_threshold = confidence_threshold
            self.logger.info(f"Updated confidence threshold to {confidence_threshold}")

        if iou_threshold is not None and 0 <= iou_threshold <= 1:
            self.iou_threshold = iou_threshold
            self.logger.info(f"Updated IoU threshold to {iou_threshold}")

    def draw_detections(
        self,
        image: Image.Image,
        detections: List[DetectionBox],
        color: Tuple[int, int, int] = (255, 0, 0)
    ) -> Image.Image:
        """Draw detection boxes on image."""
        draw = ImageDraw.Draw(image)

        for box in detections:
            # Draw bounding box
            draw.rectangle(
                [(box.x1, box.y1), (box.x2, box.y2)],
                outline=color,
                width=2
            )

            # Draw label
            label = f"{box.class_name}: {box.confidence:.2f}"
            draw.text(
                (box.x1, box.y1 - 20),
                label,
                fill=color
            )

        return image

    def reset_statistics(self):
        """Reset detection statistics."""
        self.detection_times.clear()
        self.total_detections = 0
        self.successful_detections = 0
        self.fallback_used = 0
        self.logger.info("Jigsaw detection statistics reset")

    def __del__(self):
        """Cleanup resources."""
        if hasattr(self, 'model') and self.model is not None:
            try:
                del self.model
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except:
                pass