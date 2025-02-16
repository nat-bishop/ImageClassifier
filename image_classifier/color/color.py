import math
from enum import Enum
import numpy as np
import cv2

# Define a single alias for a color tuple (3 integers).
ColorTuple = tuple[int, int, int]


class ColorType(Enum):
    LAB = 0
    RGB = 1


class Color:
    """
    A flexible color class that accepts a color in either RGB or LAB color space.
    The color is stored internally in both representations for easy access.

    The input is expected as a ColorTuple (a 3-tuple of integers).
    - For RGB, values should be in the range 0–255.
    - For LAB, use OpenCV's 8-bit LAB format: (L, a, b) with L in [0,255] and a, b in [0,255]
      (with 128 as the neutral point).
    """

    def __init__(self, value: ColorTuple, color_type: ColorType = ColorType.RGB) -> None:
        if color_type not in ColorType:
            raise ValueError("Unsupported color space. Use ColorType.RGB or ColorType.LAB.")

        if color_type == ColorType.RGB:
            self._rgb = value
            self._lab = self._rgb_to_lab(value)
        elif color_type == ColorType.LAB:
            self._lab = value
            self._rgb = self._lab_to_rgb(value)

    @staticmethod
    def _rgb_to_lab(rgb: ColorTuple) -> ColorTuple:
        """Converts an RGB color (0–255) to LAB using OpenCV."""
        rgb_array = np.uint8([[list(rgb)]])
        lab_array = cv2.cvtColor(rgb_array, cv2.COLOR_RGB2LAB)
        return int(lab_array[0, 0, 0]), int(lab_array[0, 0, 1]), int(lab_array[0, 0, 2])

    @staticmethod
    def _lab_to_rgb(lab: ColorTuple) -> ColorTuple:
        """Converts a LAB color (OpenCV 8-bit) to RGB using OpenCV."""
        lab_array = np.uint8([[list(lab)]])
        rgb_array = cv2.cvtColor(lab_array, cv2.COLOR_LAB2RGB)
        return int(rgb_array[0, 0, 0]), int(rgb_array[0, 0, 1]), int(rgb_array[0, 0, 2])

    @staticmethod
    def _lab_to_hue(lab: ColorTuple) -> float:
        """
        Extracts the hue angle (in degrees) from a Lab color.

        Args:
            lab (np.ndarray): A Lab color with shape (3,).

        Returns:
            float: The hue angle in degrees.
        """
        a = int(lab[1]) - 128
        b = int(lab[2]) - 128
        hue = (math.degrees(math.atan2(b, a)) + 360) % 360
        return hue

    @property
    def rgb(self) -> ColorTuple:
        """Returns the RGB representation."""
        return self._rgb

    @property
    def lab(self) -> ColorTuple:
        """Returns the LAB representation."""
        return self._lab

    @property
    def lab_hue(self) -> float:
        """returns hue in range 0-359"""
        return self._lab_to_hue(self._lab)

    def __repr__(self) -> str:
        return f"Color(RGB={self.rgb}, LAB={self.lab})"
