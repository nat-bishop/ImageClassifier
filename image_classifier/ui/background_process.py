import logging

from PySide2 import QtCore

from image_classifier.classifiers.base_classifier import ClassifierType
from image_classifier.controller import create_palette
from image_classifier.preferences import load_preferences

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class ColorGenerationThread(QtCore.QThread):
    colors_generated = QtCore.Signal(list)

    def __init__(self, image_path, num_colors=9):
        super().__init__()
        self.image_path = image_path
        self.num_colors = num_colors

    def run(self):
        classifier_types = load_preferences()['classifier']
        if classifier_types == 'GaussianMixture':
            classifier = ClassifierType.GUASSIANMIXTURE
        elif classifier_types == 'KMeans':
            classifier = ClassifierType.KMEANS
        elif classifier_types == 'MedianCut':
            classifier = ClassifierType.MEDIANCUT
        else:
            logging.error(f"classifier: {classifier_types} is not valid")
            exit()
        palette = create_palette(self.image_path, self.num_colors, classifier)
        logging.info(f'Generated Palette with classifier: {classifier}, image_path: {self.image_path}, num_colors: {self.num_colors}')
        self.colors_generated.emit(palette)