import numpy as np
from sklearn.mixture import GaussianMixture
from image_classifier.classifiers.base_classifier import ColorClassifier
from image_classifier.color import Color, ColorType


class GMMColorClassifier(ColorClassifier):
    def extract_colors(self, image: np.ndarray, num_colors: int, num_samples: int = 50000) -> list[Color]:
        """Extracts dominant colors using Gaussian Mixture Models with stride-based downsampling."""

        pixels = image.reshape(-1, 3)  # Flatten image
        indices = np.random.choice(len(pixels), num_samples, replace=False)
        pixels = pixels[indices]


        # Fit GMM
        gmm = GaussianMixture(n_components=num_colors).fit(pixels)

        return [Color(tuple(color), ColorType.LAB) for color in gmm.means_.astype(int)]
