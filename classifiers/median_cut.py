from PIL import Image
import cv2
import numpy as np

from classifiers.base_classifier import ColorClassifier


class MedianCutColorClassifier(ColorClassifier):
    def extract_colors(self, image: np.ndarray, num_colors: int) -> list:
        """Extract colors using the Median Cut algorithm."""
        pil_image = Image.fromarray(image)
        pil_image = pil_image.convert("P", palette=Image.ADAPTIVE, colors=num_colors)
        palette = pil_image.getpalette()
        return [palette[i:i+3] for i in range(0, num_colors * 3, 3)]