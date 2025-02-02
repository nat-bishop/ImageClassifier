from abc import ABC, abstractmethod
import numpy as np


class ColorClassifier(ABC):
    @abstractmethod
    def extract_colors(self, image: np.ndarray, num_colors: int) -> list:
        """Extracts dominant colors from an image."""
        pass