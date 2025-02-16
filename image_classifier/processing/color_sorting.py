from collections.abc import Sequence
import logging
from image_classifier.color.color import Color

logger = logging.getLogger(__name__)


def sort_by_lab(colors: list[Color]) -> list[Color]:
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

    logger.info(f"Received {len(colors)} Lab colors for sorting.")

    # Sort colors by the L channel (the first element of each Lab triplet)
    sorted_colors = sorted(colors, key=lambda c: c.lab[0])

    logger.info("Sorting completed.")
    return sorted_colors
