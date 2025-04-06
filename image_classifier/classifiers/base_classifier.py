import logging
from abc import ABC, abstractmethod
from enum import Enum

import numpy as np

from image_classifier.color import Color

logger = logging.getLogger(__name__)  # Logger for this file


class ClassifierType(Enum):
    KMEANS = 0
    GUASSIANMIXTURE = 1
    MEDIANCUT = 2


class ColorClassifier(ABC):
    @abstractmethod
    def extract_colors(self, image: np.ndarray, num_colors: int) -> list[Color]:
        """Extracts dominant colors from an image."""
        pass
