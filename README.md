Color Harmony Analyzer
------------------------

Color Harmony Analyzer extracts and evaluates the dominant colors of an image
using LAB color space. Its features include:

• Drag-and-drop UI for image analysis.
• Dominant color extraction via K-Means/GaussianMixture/MedianCut clustering in LAB space.
• Harmony analysis (triadic, square, analogous, complementary, split complementary, monochromatic),
  plus metrics for saturation, contrast.
• Export of the palette as a PNG with color codes in the image.
• Click-to-copy functionality for RGB, HSL, and LAB color codes.
• Automatic descriptive analysis of the image’s color harmony.

"<Path to nuke python>" -m pip install "<path to Image Classifier dir"
example:
  "C:\Program Files\Nuke15.1v2\python.exe" -m pip install "C:\Users\17143\PycharmProjects\ImageClassifier"

add imageClassifier.gizmo and init.py to nuke
inside imageClassifier make sure to change the path to Image Classifier dir
