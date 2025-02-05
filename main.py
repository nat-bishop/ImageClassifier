from pathlib import Path
from image_classifier.classifiers.base_classifier import ClassifierType
from image_classifier.ui.ui import display_multiple_classifiers
from image_classifier.controllers.controller import create_palette, analyze_palette_harmony
import logging


if __name__ == '__main__':

    # Load Image
    image_path = Path("testimages/duneposter.jpg")

    logging.basicConfig(
        level=logging.INFO,  # Change to DEBUG if needed
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    )

    logger = logging.getLogger(__name__)  # Main logger
    logger.info("Logging is set up!")

    num_colors = 5
    classifier = ClassifierType.KMEANS
    palette = create_palette(image_path, num_colors, classifier)
    print(analyze_palette_harmony(palette))
    display_multiple_classifiers({classifier: palette})
    #palettes = {classifier.name: create_palette(image_path, num_colors, classifier) for classifier in ClassifierType}
    #display_multiple_classifiers(palettes)




