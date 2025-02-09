import logging
from pathlib import Path
from typing import List

import numpy as np

from image_classifier.classifiers.base_classifier import ClassifierType, ColorClassifier
from image_classifier.classifiers.k_means import KMeansColorClassifier
from image_classifier.classifiers.guassian_mixture import GMMColorClassifier
from image_classifier.classifiers.median_cut import MedianCutColorClassifier
from image_classifier.processing.color_harmony import score_triadic, score_analogous, score_square, score_complementary, \
    score_split_complementary, score_monochromatic, score_contrast_absolute, score_saturation_absolute
from image_classifier.processing.color_sorting import sort_by_lab
from image_classifier.processing.image_processor import ImageProcessor
from image_classifier.processing.utils import rgb_to_lab, lab_to_hue

logger = logging.getLogger(__name__)

# Classifier mapping
CLASSIFIER_MAP = {
    ClassifierType.KMEANS: KMeansColorClassifier,
    ClassifierType.GUASSIANMIXTURE: GMMColorClassifier,
    ClassifierType.MEDIANCUT: MedianCutColorClassifier
}


def create_palette(image_path: Path, num_colors: int, classifier_type: ClassifierType) -> List[tuple[int, int, int]]:
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
        logger.info(f"Extracted {len(colors)} colors from image.")

        sorted_colors = sort_by_lab(colors)
        logger.info("Color sorting completed.")

        return sorted_colors

    except FileNotFoundError:
        logger.error(f"Image file not found: {image_path}")
        raise

    except Exception as e:
        logger.exception(f"An unexpected error occurred while creating palette: {e}")
        raise


def analyze_palette_harmony(palette: List[tuple[int, int, int]]) -> str:
    """Analyzes a palette of LAB colors as a whole and assigns a single harmony type."""
    hues = [lab_to_hue(lab) for lab in palette]
    print("HUES")
    print(hues)
    print("Triadic score:", score_triadic(hues))

    print("Square score:", score_square(hues))

    print("Analogous score:", score_analogous(hues))

    print("Complementary score:", score_complementary(hues))

    print("Split Complementary score:", score_split_complementary(hues))

    print("Monochromatic score: ", score_monochromatic(hues))

    print("Contrast score: ", score_contrast_absolute(palette))

    print("Saturation score: ", score_saturation_absolute(palette))

