import logging
from pathlib import Path

from image_classifier.classifiers.base_classifier import ClassifierType
from image_classifier.classifiers.guassian_mixture import GMMColorClassifier
from image_classifier.classifiers.k_means import KMeansColorClassifier
from image_classifier.classifiers.median_cut import MedianCutColorClassifier
from image_classifier.color import Color
from image_classifier.processing.color_harmony import score_triadic, score_analogous, score_square, score_complementary, \
    score_split_complementary, score_monochromatic, score_contrast_absolute, score_saturation_absolute
from image_classifier.processing.color_sorting import sort_by_lab
from image_classifier.processing.image_processor import ImageProcessor

logger = logging.getLogger(__name__)

# Classifier mapping
CLASSIFIER_MAP = {
    ClassifierType.KMEANS: KMeansColorClassifier,
    ClassifierType.GUASSIANMIXTURE: GMMColorClassifier,
    ClassifierType.MEDIANCUT: MedianCutColorClassifier
}


def create_palette(image_path: Path, num_colors: int, classifier_type: ClassifierType) -> list[Color]:
    """
    Creates a color palette from an image using the given classifier type.

    Args:
        image_path (Path): Path to the image file.
        num_colors (int): Number of dominant colors to extract.
        classifier_type (ClassifierType): The classifier type to use.

    Returns:
        List[List[int]]: Sorted list of extracted LAB colors.
    """
    if classifier_type not in CLASSIFIER_MAP:
        logger.error(f"Invalid classifier type: {classifier_type}")
        raise ValueError(f"Unsupported classifier type: {classifier_type}")

    classifier = CLASSIFIER_MAP[classifier_type]()  # Instantiate the classifier
    logger.info(f"Using classifier: {classifier.__class__.__name__} for image: {image_path}")

    try:
        processor = ImageProcessor(image_path, classifier)
        colors = processor.extract_colors(num_colors)

        sorted_colors = sort_by_lab(colors)

        return sorted_colors

    except FileNotFoundError:
        logger.error(f"Image file not found: {image_path}")
        raise

    except Exception as e:
        logger.exception(f"An unexpected error occurred while creating palette: {e}")
        raise


def analyze_palette_harmony(palette: list[Color]) -> dict:
    """Analyzes a palette of LAB colors"""
    hues = [color.hsv[0] for color in palette]
    color_harmony = {
        'Triadic': score_triadic(hues)[0],
        'Square': score_square(hues)[0],
        'Complementary': score_complementary(hues)[0],
        'Split Complementary': score_split_complementary(hues)[0],
        'Monochromatic': score_monochromatic(hues)[0],
        'Contrast': score_contrast_absolute(palette),
        'Saturation': score_saturation_absolute(palette)
    }

    for score_type, score in color_harmony.items():
        logger.info(f'{score_type}: {score:.2f}')
    return color_harmony
