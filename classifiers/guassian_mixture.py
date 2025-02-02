import numpy as np
from sklearn.mixture import GaussianMixture

from classifiers.base_classifier import ColorClassifier


class GMMColorClassifier(ColorClassifier):
    def extract_colors(self, image: np.ndarray, num_colors: int) -> list:
        """Extracts dominant colors using Gaussian Mixture Models."""
        pixels = image.reshape(-1, 3)  # Flatten image
        gmm = GaussianMixture(n_components=num_colors).fit(pixels)
        return gmm.means_.astype(int).tolist()