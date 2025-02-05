from collections.abc import Sequence
import logging
import numpy as np
import cv2

from image_classifier.processing.utils import rgb_to_lab

logger = logging.getLogger(__name__)


def sort_by_lab(colors: list[tuple[int, int, int]]) -> list[tuple[int, int, int]]:
    """
    Sorts colors based on perceived lightness and contrast using CIE Lab space.

    Args:
        colors (list): List of RGB colors (e.g., [[255, 0, 0], [0, 255, 0], ...])

    Returns:
        list: Sorted list of RGB colors.
    """
    if not colors:
        logger.error("Received an empty list of colors.")
        raise ValueError("Input cannot be an empty list.")

    if not isinstance(colors, list):
        logger.error(f"Invalid input type: {type(colors)}. Expected a list.")
        raise ValueError("Input must be a list of RGB triplets.")

    if not all(isinstance(c, Sequence) and len(c) == 3 for c in colors):
        logger.error(f"Invalid color format: {colors}. Expected list of RGB triplets.")
        raise ValueError("Each color must be a sequence (list, tuple, etc.) of 3 values.")

    if not all(all(0 <= value <= 255 for value in c) for c in colors):
        logger.error(f"Invalid RGB values: {colors}. Values must be between 0 and 255.")
        raise ValueError("Each RGB value must be between 0 and 255.")

    logger.info(f"Received {len(colors)} colors for sorting.")

    lab_colors = rgb_to_lab(colors)

    # Sort by the L channel (lightness)
    sorted_colors = [x for _, x in sorted(zip(lab_colors[:, 0], colors), key=lambda pair: pair[0])]

    logger.info("Sorting completed.")
    return sorted_colors
