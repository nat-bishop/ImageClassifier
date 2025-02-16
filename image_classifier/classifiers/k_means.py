import logging

import numpy as np
from sklearn.cluster import KMeans
from image_classifier.color.color import Color, ColorType

from image_classifier.classifiers.base_classifier import ColorClassifier


logger = logging.getLogger(__name__)


class KMeansColorClassifier(ColorClassifier):
    def extract_colors(self, image: np.ndarray, num_colors: int) -> list[Color]:
        """Extract colors using K-Means clustering."""
        logger.info(f"Extracting {num_colors} colors using KMeans.")
        pixels = image.reshape(-1, 3)  # Flatten image
        kmeans = KMeans(n_clusters=num_colors, random_state=0, n_init=10)
        kmeans.fit(pixels)
        return [Color(tuple(color), ColorType.LAB) for color in kmeans.cluster_centers_.astype(int)]
