import logging

from PIL import Image
import numpy as np

from image_classifier.classifiers.base_classifier import ColorClassifier


logger = logging.getLogger(__name__)


class MedianCutColorClassifier(ColorClassifier):
    def extract_colors(self, image: np.ndarray, num_colors: int) -> list:
        """Extract colors using the Median Cut algorithm."""
        logger.info(f"Extracting {num_colors} colors using Median Cut Model.")
        pil_image = Image.fromarray(image)
        pil_image = pil_image.convert("P", palette=Image.ADAPTIVE, colors=num_colors)
        palette = pil_image.getpalette()
        return [palette[i:i+3] for i in range(0, num_colors * 3, 3)]