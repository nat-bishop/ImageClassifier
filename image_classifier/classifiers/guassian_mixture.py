import logging

import numpy as np
from sklearn.mixture import GaussianMixture
from image_classifier.color.color import Color, ColorType

from image_classifier.classifiers.base_classifier import ColorClassifier


logger = logging.getLogger(__name__)


class GMMColorClassifier(ColorClassifier):
    def extract_colors(self, image: np.ndarray, num_colors: int) -> list[Color]:
        """Extracts dominant colors using Gaussian Mixture Models."""
        logger.info(f"Extracting {num_colors} colors using Gaussian Mixture Model.")
        pixels = image.reshape(-1, 3)  # Flatten image
        gmm = GaussianMixture(n_components=num_colors).fit(pixels)
        return [Color(tuple(color), ColorType.LAB) for color in gmm.means_.astype(int)]
