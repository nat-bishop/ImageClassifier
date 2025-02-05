from pathlib import Path

import cv2
import numpy as np
import logging

from image_classifier.classifiers.base_classifier import ColorClassifier

logger = logging.getLogger(__name__)


class ImageProcessor:
    def __init__(self, image_path: Path, classifier: ColorClassifier):
        self.image_path = image_path
        self.classifier = classifier
        self.image = self.load_image
        logger.info(f"Initialized ImageProcessor with image path: {self.image_path}")

    def load_image(self) -> np.ndarray:
        logger.debug(f"Attempting to load image from: {self.image_path}")
        image = cv2.imread(str(self.image_path))
        if image is None:
            logger.error(f"Failed to load image: {self.image_path}")
            raise FileNotFoundError(f"Image not found at path: {self.image_path}")

        logger.info(f"Successfully loaded image: {self.image_path}")
        return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)  # Convert to RGB

    def extract_colors(self, num_colors: int = 5) -> list:
        """Uses the selected classifier to extract colors."""
        logger.info(f"Extracting {num_colors} colors using {self.classifier.__class__.__name__}")
        colors = self.classifier.extract_colors(self.image, num_colors)
        logger.debug(f"Extracted colors: {colors}")
        return colors
