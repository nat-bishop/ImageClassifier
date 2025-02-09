from typing import Tuple

import numpy as np
import cv2
import logging
import math

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


def lab_to_rgb(lab_color: tuple[int, int, int]) -> tuple[int, ...]:
    lab_array = np.uint8(np.asarray([[lab_color]]))
    rgb_array = cv2.cvtColor(lab_array, cv2.COLOR_LAB2RGB)
    return tuple(int(x) for x in rgb_array[0, 0])


def lab_to_hue(lab_color: tuple[int, int, int]) -> float:
    """
    Extracts the hue angle (in degrees) from a Lab color.

    Args:
        lab_color (np.ndarray): A Lab color with shape (3,).

    Returns:
        float: The hue angle in degrees.
    """
    a = int(lab_color[1]) - 128
    b = int(lab_color[2]) - 128
    hue = (math.degrees(math.atan2(b, a)) + 360) % 360
    return hue
