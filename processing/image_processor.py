import cv2
import numpy as np

from classifiers.base_classifier import ColorClassifier


class ImageProcessor:
    def __init__(self, image_path: str, classifier: ColorClassifier):
        self.image_path = image_path
        self.classifier = classifier
        self.image = self.load_image()

    def load_image(self) -> np.ndarray:
        """Loads an image using OpenCV."""
        image = cv2.imread(self.image_path)
        return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)  # Convert to RGB

    def extract_colors(self, num_colors=5) -> list:
        """Uses the selected classifier to extract colors."""
        return self.classifier.extract_colors(self.image, num_colors)