from collections.abc import Sequence
import logging
import numpy as np
from typing import List, Tuple

logger = logging.getLogger(__name__)


def sort_by_lab(colors: List[Tuple[int, int, int]]) -> List[Tuple[int, int, int]]:
    """
    Sorts colors based on perceived lightness using the L channel from the CIE Lab space.

    Args:
        colors (List[Tuple[int, int, int]]): List of Lab colors (e.g., [(L, a, b), (L, a, b), ...]).
            Note: This function assumes that the colors are in Lab space (for example, as provided
            by OpenCV after a conversion via cv2.COLOR_BGR2LAB).

    Returns:
        List[Tuple[int, int, int]]: Sorted list of Lab colors, sorted by the L channel (lightness).
    """
    if not colors:
        logger.error("Received an empty list of colors.")
        raise ValueError("Input cannot be an empty list.")

    if not isinstance(colors, list):
        logger.error(f"Invalid input type: {type(colors)}. Expected a list.")
        raise ValueError("Input must be a list of Lab triplets.")

    if not all(isinstance(c, Sequence) and len(c) == 3 for c in colors):
        logger.error(f"Invalid color format: {colors}. Expected a list of Lab triplets.")
        raise ValueError("Each color must be a sequence (list, tuple, etc.) of 3 values.")

    # Optionally, verify that values are numeric.
    if not all(all(isinstance(value, (int, float)) for value in c) for c in colors):
        logger.error(f"Invalid Lab values: {colors}. Values must be numeric.")
        raise ValueError("Each Lab value must be numeric.")

    logger.info(f"Received {len(colors)} Lab colors for sorting.")

    # Sort colors by the L channel (the first element of each Lab triplet)
    sorted_colors = sorted(colors, key=lambda c: c[0])

    logger.info("Sorting completed.")
    return sorted_colors
