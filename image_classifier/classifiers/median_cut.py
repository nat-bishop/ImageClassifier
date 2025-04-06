import logging
import time

import numpy as np
from PIL import Image

from image_classifier.classifiers.base_classifier import ColorClassifier
from image_classifier.color import Color, ColorType

# Configure logging for this module
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class MedianCutColorClassifier(ColorClassifier):
    def extract_colors(self, image: np.ndarray, num_colors: int) -> list[Color]:
        """Extract colors using the Median Cut algorithm."""
        start_time = time.time()
        logger.info(f"Starting Median Cut color extraction for {num_colors} colors")
        logger.info(f"Input image shape: {image.shape}")
        
        # Convert to PIL Image
        logger.info("Converting to PIL Image")
        pil_image = Image.fromarray(image)
        
        # Apply median cut
        logger.info("Applying median cut quantization")
        pil_image = pil_image.convert("P", palette=Image.ADAPTIVE, colors=num_colors)
        
        processing_time = time.time()
        logger.info(f"Median cut processing took: {processing_time - start_time:.3f} seconds")
        
        # Extract palette
        logger.info("Extracting color palette")
        palette = pil_image.getpalette()
        extracted_colors = [tuple(palette[i:i+3]) for i in range(0, num_colors * 3, 3)]
        
        # Convert to Color objects
        colors = [Color(color, ColorType.LAB) for color in extracted_colors]
        
        total_time = time.time() - start_time
        logger.info(f"Total Median Cut color extraction took: {total_time:.3f} seconds")
        logger.info(f"Extracted {len(colors)} colors")
        
        return colors
