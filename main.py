from pathlib import Path
from image_classifier.classifiers.base_classifier import ClassifierType
from image_classifier.processing.utils import lab_to_rgb
from image_classifier.ui.ui import display_multiple_classifiers
from image_classifier.controllers.controller import create_palette, analyze_palette_harmony
import logging


if __name__ == '__main__':

    # Load Image
    image_paths = [Path("testimages/duneposter.jpg"),
                   Path("testimages/annetx.jpg"),
                   Path("testimages/batman.jpg"),
                   Path("testimages/howtobesingle.jpg"),
                   Path("testimages/johnwick.jpg"),
                   Path("testimages/thebear.jpg")]

    logging.basicConfig(
        level=logging.WARNING,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    )

    logger = logging.getLogger(__name__)  # Main logger
    logger.info("Logging is set up!")

    num_colors = 3
    classifier = ClassifierType.KMEANS
    palettes = {}
    for path in image_paths:
        palette = create_palette(path, num_colors, classifier)
        print(path)
        print(palette)
        print(analyze_palette_harmony(palette))
        palettes[path] = [lab_to_rgb(lab) for lab in palette]

    display_multiple_classifiers(palettes)





