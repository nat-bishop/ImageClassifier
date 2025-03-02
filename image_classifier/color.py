import colorsys
from enum import Enum

import cv2
import numpy as np

ColorTuple = tuple[int, int, int]


class ColorType(Enum):
    LAB = 0
    RGB = 1
    HSV = 2


class Color:
    """
    A simpler color class that stores an internal RGB color in [0..255].
    On-the-fly properties for .lab or .hsv by converting from RGB.
    No direct lab->hsv or hsv->lab method (we chain via RGB).
    """

    def __init__(self, value: ColorTuple, color_type: ColorType = ColorType.RGB) -> None:
        """
        value:
            if color_type=RGB => (R,G,B) each in [0..255]
            if color_type=LAB => (L,A,B) each in [0..255] (OpenCV 8-bit Lab)
            if color_type=HSV => (H,S,V) with H in [0..359], S,V in [0..255]
        """
        if color_type == ColorType.RGB:
            self._rgb = value
        elif color_type == ColorType.LAB:
            self._rgb = self._lab_to_rgb(value)
        elif color_type == ColorType.HSV:
            self._rgb = self._hsv_to_rgb(value)
        else:
            raise ValueError("Unsupported color space: use RGB, LAB, or HSV.")

    # -----------------------------------------------------------
    # Internal conversions (only the four we really need)
    # -----------------------------------------------------------
    @staticmethod
    def _lab_to_rgb(lab: ColorTuple) -> ColorTuple:
        """Convert (L,A,B) in [0..255] to (R,G,B) in [0..255]."""
        arr = np.uint8([[[lab[0], lab[1], lab[2]]]])
        rgb_arr = cv2.cvtColor(arr, cv2.COLOR_LAB2RGB)
        r, g, b = rgb_arr[0, 0]
        return (int(r), int(g), int(b))

    @staticmethod
    def _rgb_to_lab(rgb: ColorTuple) -> ColorTuple:
        """Convert (R,G,B) in [0..255] to (L,A,B) in [0..255] (OpenCV Lab)."""
        arr = np.uint8([[[rgb[0], rgb[1], rgb[2]]]])
        lab_arr = cv2.cvtColor(arr, cv2.COLOR_RGB2LAB)
        L, A, B = lab_arr[0, 0]
        return (int(L), int(A), int(B))

    @staticmethod
    def _hsv_to_rgb(hsv: ColorTuple) -> ColorTuple:
        """
        Convert (H,S,V) with H in [0..359], S,V in [0..255]
        to (R,G,B) in [0..255].
        """
        h, s, v = hsv
        h_f = (h % 360) / 360.0
        s_f = s / 255.0
        v_f = v / 255.0
        r_f, g_f, b_f = colorsys.hsv_to_rgb(h_f, s_f, v_f)
        return (
            int(round(r_f * 255)),
            int(round(g_f * 255)),
            int(round(b_f * 255))
        )

    @staticmethod
    def _rgb_to_hsv(rgb: ColorTuple) -> ColorTuple:
        """
        Convert (R,G,B) in [0..255] to (H,S,V),
        with H in [0..359], S,V in [0..255].
        """
        r, g, b = rgb
        r_f, g_f, b_f = r / 255.0, g / 255.0, b / 255.0
        h_f, s_f, v_f = colorsys.rgb_to_hsv(r_f, g_f, b_f)
        h_deg = int(round(h_f * 360)) % 360
        s_i = int(round(s_f * 255))
        v_i = int(round(v_f * 255))
        return (h_deg, s_i, v_i)

    # -----------------------------------------------------------
    # Properties
    # -----------------------------------------------------------
    @property
    def rgb(self) -> ColorTuple:
        """
        Internal representation (R,G,B) in [0..255].
        """
        return self._rgb

    @property
    def lab(self) -> ColorTuple:
        """
        Convert from self._rgb to Lab on the fly.
        """
        return self._rgb_to_lab(self._rgb)

    @property
    def hsv(self) -> ColorTuple:
        """
        Convert from self._rgb to HSV on the fly.
        """
        return self._rgb_to_hsv(self._rgb)

    @property
    def hex(self) -> str:
        r, g, b = self.rgb
        return f"#{r:02x}{g:02x}{b:02x}"

    def __repr__(self) -> str:
        return f"Color(rgb={self._rgb})"
