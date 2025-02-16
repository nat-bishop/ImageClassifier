import sys
from pathlib import Path
from image_classifier.classifiers.base_classifier import ClassifierType
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
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],  # Ensure logs appear in PyCharm's console
        force=True  # Ensures reconfiguration of logging
    )

    logger = logging.getLogger(__name__)  # Main logger
    logger.info("Logging is set up!")

    num_colors = 3
    classifier = ClassifierType.KMEANS
    palettes = {}
    for path in image_paths:
        palette = create_palette(path, num_colors, classifier)
        logging.info(f'Image Name: {path.name}')
        color_harmony = analyze_palette_harmony(palette)
        palettes[path] = [color.rgb for color in palette]

    display_multiple_classifiers(palettes)
