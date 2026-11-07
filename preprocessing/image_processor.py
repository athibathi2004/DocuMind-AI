import cv2
import numpy as np
from PIL import Image
from pathlib import Path
from typing import Tuple, Optional, Union
from pydantic import BaseModel


class PreprocessingConfig(BaseModel):
    """Configuration options for document image preprocessing pipeline."""
    resize_target_width: Optional[int] = 1800
    enable_grayscale: bool = True
    enable_denoise: bool = True
    denoise_kernel_size: int = 3
    enable_deskew: bool = True
    max_deskew_angle: float = 45.0
    enable_clahe: bool = True
    clahe_clip_limit: float = 2.0
    clahe_tile_grid_size: int = 8
    enable_adaptive_threshold: bool = False
    adaptive_block_size: int = 15
    adaptive_c: int = 5
    orientation_correction: bool = True


class ImageProcessor:
    """Provides computer vision filters and preprocessing operations for optimal OCR accuracy."""

    def __init__(self, config: Optional[PreprocessingConfig] = None):
        self.config = config or PreprocessingConfig()

    def load_image(self, image_input: Union[str, Path, np.ndarray, Image.Image]) -> np.ndarray:
        """Load image into BGR/RGB numpy array."""
        if isinstance(image_input, (str, Path)):
            img = cv2.imread(str(image_input))
            if img is None:
                # Fallback to PIL for complex formats
                pil_img = Image.open(str(image_input)).convert("RGB")
                img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
            return img
        elif isinstance(image_input, Image.Image):
            return cv2.cvtColor(np.array(image_input), cv2.COLOR_RGB2BGR)
        elif isinstance(image_input, np.ndarray):
            return image_input.copy()
        else:
            raise ValueError(f"Unsupported image input type: {type(image_input)}")

    def resize(self, image: np.ndarray, target_width: int) -> np.ndarray:
        """Resize image preserving aspect ratio."""
        h, w = image.shape[:2]
        if w == 0 or h == 0 or w == target_width:
            return image
        scaling = target_width / float(w)
        new_h = int(h * scaling)
        return cv2.resize(image, (target_width, new_h), interpolation=cv2.INTER_CUBIC)

    def to_grayscale(self, image: np.ndarray) -> np.ndarray:
        """Convert BGR image to single-channel 8-bit grayscale."""
        if len(image.shape) == 2:
            return image
        return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    def reduce_noise(self, image: np.ndarray, kernel_size: int = 3) -> np.ndarray:
        """Reduce salt-and-pepper and sensor noise using Gaussian blur."""
        if kernel_size % 2 == 0:
            kernel_size += 1
        return cv2.GaussianBlur(image, (kernel_size, kernel_size), 0)

    def enhance_contrast(self, image: np.ndarray) -> np.ndarray:
        """Apply Contrast Limited Adaptive Histogram Equalization (CLAHE)."""
        gray = self.to_grayscale(image)
        clahe = cv2.createCLAHE(
            clipLimit=self.config.clahe_clip_limit,
            tileGridSize=(self.config.clahe_tile_grid_size, self.config.clahe_tile_grid_size),
        )
        return clahe.apply(gray)

    def adaptive_threshold(self, image: np.ndarray) -> np.ndarray:
        """Apply adaptive Gaussian thresholding to separate text foreground from background."""
        gray = self.to_grayscale(image)
        bs = self.config.adaptive_block_size
        if bs % 2 == 0:
            bs += 1
        return cv2.adaptiveThreshold(
            gray,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            bs,
            self.config.adaptive_c,
        )

    def estimate_skew_angle(self, gray: np.ndarray) -> float:
        """
        Estimate skew angle in degrees using bounding box of detected foreground contours.
        """
        # Invert colors so text is white
        thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
        coords = np.column_stack(np.where(thresh > 0))
        if len(coords) < 50:
            return 0.0

        angle = cv2.minAreaRect(coords)[-1]
        # Normalize angle
        if angle < -45:
            angle = -(90 + angle)
        elif angle > 45:
            angle = 90 - angle
        else:
            angle = -angle

        # If angle is negligible or too extreme, skip
        if abs(angle) < 0.2 or abs(angle) > self.config.max_deskew_angle:
            return 0.0
        return angle

    def rotate_image(self, image: np.ndarray, angle: float) -> np.ndarray:
        """Rotate image by given angle in degrees with white background padding."""
        if abs(angle) < 0.01:
            return image
        h, w = image.shape[:2]
        center = (w // 2, h // 2)
        rot_mat = cv2.getRotationMatrix2D(center, angle, 1.0)

        # Compute new bounding dimensions
        cos = np.abs(rot_mat[0, 0])
        sin = np.abs(rot_mat[0, 1])
        new_w = int((h * sin) + (w * cos))
        new_h = int((h * cos) + (w * sin))

        rot_mat[0, 2] += (new_w / 2) - center[0]
        rot_mat[1, 2] += (new_h / 2) - center[1]

        border_val = 255 if len(image.shape) == 2 else (255, 255, 255)
        return cv2.warpAffine(
            image, rot_mat, (new_w, new_h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_CONSTANT, borderValue=border_val
        )

    def deskew(self, image: np.ndarray) -> Tuple[np.ndarray, float]:
        """Detect and correct document skew."""
        gray = self.to_grayscale(image)
        angle = self.estimate_skew_angle(gray)
        if abs(angle) > 0.1:
            rotated = self.rotate_image(image, angle)
            return rotated, angle
        return image, 0.0

    def process(self, image_input: Union[str, Path, np.ndarray, Image.Image]) -> Tuple[np.ndarray, dict]:
        """
        Run the full modular preprocessing pipeline according to configuration.
        Returns (preprocessed_image_array, preprocessing_diagnostics).
        """
        raw = self.load_image(image_input)
        diagnostics = {
            "initial_shape": list(raw.shape),
            "skew_detected": 0.0,
            "steps_applied": [],
        }

        current = raw

        # Step 1: Resize if configured and wider than target
        if self.config.resize_target_width and current.shape[1] > self.config.resize_target_width:
            current = self.resize(current, self.config.resize_target_width)
            diagnostics["steps_applied"].append(f"resize({self.config.resize_target_width})")

        # Step 2: Deskew
        if self.config.enable_deskew:
            current, angle = self.deskew(current)
            if abs(angle) > 0.1:
                diagnostics["skew_detected"] = round(float(angle), 2)
                diagnostics["steps_applied"].append(f"deskew({diagnostics['skew_detected']}deg)")

        # Step 3: Grayscale
        if self.config.enable_grayscale:
            current = self.to_grayscale(current)
            diagnostics["steps_applied"].append("grayscale")

        # Step 4: Noise Reduction
        if self.config.enable_denoise:
            current = self.reduce_noise(current, self.config.denoise_kernel_size)
            diagnostics["steps_applied"].append("denoise")

        # Step 5: CLAHE Contrast Enhancement
        if self.config.enable_clahe:
            current = self.enhance_contrast(current)
            diagnostics["steps_applied"].append("clahe_contrast")

        # Step 6: Adaptive Thresholding (optional)
        if self.config.enable_adaptive_threshold:
            current = self.adaptive_threshold(current)
            diagnostics["steps_applied"].append("adaptive_threshold")

        diagnostics["final_shape"] = list(current.shape)
        return current, diagnostics

    def save_image(self, image: np.ndarray, output_path: Union[str, Path]) -> Path:
        """Save preprocessed image to disk."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(output_path), image)
        return output_path


default_image_processor = ImageProcessor()

