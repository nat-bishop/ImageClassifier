import cv2
import numpy as np


def sort_by_lab(colors):
    """
    Sorts colors based on perceived lightness and contrast using CIE Lab space.

    Args:
        colors (list): List of RGB colors (e.g., [[255, 0, 0], [0, 255, 0], ...])

    Returns:
        list: Sorted list of RGB colors.
    """
    color_array = np.array([colors], dtype=np.uint8)  # Shape (1, num_colors, 3)
    lab_colors = cv2.cvtColor(color_array, cv2.COLOR_RGB2LAB)[0]  # Convert to Lab
    return [x for _, x in sorted(zip(lab_colors[:, 0], colors), key=lambda pair: pair[0])]