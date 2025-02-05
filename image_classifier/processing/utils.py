import numpy as np
import cv2
import logging

logger = logging.getLogger(__name__)


def rgb_to_lab(colors: list[tuple[int, int, int]]) -> np.ndarray:
    """
    Converts a list of RGB colors to CIE-LAB color space.

    Args:
        colors (list of tuple[int, int, int]): List of RGB colors.

    Returns:
        np.ndarray: Array of LAB colors with shape (num_colors, 3).
    """
    # Convert to NumPy array with correct shape
    color_array = np.array(colors, dtype=np.uint8)  # Shape (num_colors, 3)
    logger.debug(f"Color array shape: {color_array.shape}")

    # Convert RGB to Lab
    lab_colors = cv2.cvtColor(color_array[np.newaxis, :, :], cv2.COLOR_RGB2LAB)[0]
    logger.debug(f"Converted Lab colors: {lab_colors}")

    return lab_colors
