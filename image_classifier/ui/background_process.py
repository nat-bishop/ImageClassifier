from PySide2 import QtCore

from image_classifier.classifiers.base_classifier import ClassifierType
from image_classifier.controller import create_palette


class ColorGenerationThread(QtCore.QThread):
    colors_generated = QtCore.Signal(list)

    def __init__(self, image_path, num_colors=9):
        super().__init__()
        self.image_path = image_path
        self.num_colors = num_colors
        print('########')

    def run(self):
        palette = create_palette(self.image_path, self.num_colors, ClassifierType.KMEANS)
        self.colors_generated.emit(palette)