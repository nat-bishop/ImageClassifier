import logging

from PySide2 import QtCore

from image_classifier.classifiers.base_classifier import ClassifierType
from image_classifier.controller import create_palette

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class ColorGenerationThread(QtCore.QThread):
    colors_generated = QtCore.Signal(list)

    def __init__(self, image_path, num_colors=9):
        super().__init__()
        self.image_path = image_path
        self.num_colors = num_colors

    def run(self):
        classifier = ClassifierType.KMEANS
        palette = create_palette(self.image_path, self.num_colors, classifier)
        logging.info(f'Generated Palette with classifier: {classifier}, image_path: {self.image_path}, num_colors: {self.num_colors}')
        self.colors_generated.emit(palette)