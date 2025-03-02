import logging

import numpy as np
from PIL import Image

from image_classifier.classifiers.base_classifier import ColorClassifier
from image_classifier.color import Color, ColorType

logger = logging.getLogger(__name__)


class MedianCutColorClassifier(ColorClassifier):
    def extract_colors(self, image: np.ndarray, num_colors: int) -> list[Color]:
        """Extract colors using the Median Cut algorithm."""
        logger.info(f"Extracting {num_colors} colors using Median Cut Model.")
        pil_image = Image.fromarray(image)
        pil_image = pil_image.convert("P", palette=Image.ADAPTIVE, colors=num_colors)
        palette = pil_image.getpalette()
        extracted_colors = [tuple(palette[i:i+3]) for i in range(0, num_colors * 3, 3)]
        return [Color(color, ColorType.LAB) for color in extracted_colors]
