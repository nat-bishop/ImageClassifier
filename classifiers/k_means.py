import numpy as np
from sklearn.cluster import KMeans

from classifiers.base_classifier import ColorClassifier


class KMeansColorClassifier(ColorClassifier):
    def extract_colors(self, image: np.ndarray, num_colors: int) -> list:
        """Extract colors using K-Means clustering."""
        pixels = image.reshape(-1, 3)  # Flatten image
        kmeans = KMeans(n_clusters=num_colors, random_state=0, n_init=10)
        kmeans.fit(pixels)
        return kmeans.cluster_centers_.astype(int).tolist()