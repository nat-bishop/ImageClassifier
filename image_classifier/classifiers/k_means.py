import logging
import time
import numpy as np
from sklearn.cluster import KMeans

from image_classifier.classifiers.base_classifier import ColorClassifier
from image_classifier.color import Color, ColorType

# Configure logging for this module
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class KMeansColorClassifier(ColorClassifier):
    def extract_colors(self, image: np.ndarray, num_colors: int) -> list[Color]:
        """Extract colors using K-Means clustering."""
        start_time = time.time()
        logger.info(f"Starting KMeans color extraction for {num_colors} colors")
        logger.info(f"Input image shape: {image.shape}")
        
        # Flatten and sample pixels
        pixels = image.reshape(-1, 3)  # Flatten image
        logger.info(f"Flattened pixels shape: {pixels.shape}")
        
        num_samples = 250000
        logger.info(f"Sampling {num_samples} pixels from {len(pixels)} total pixels")
        indices = np.random.choice(len(pixels), num_samples, replace=False)
        pixels = pixels[indices]
        
        sampling_time = time.time()
        logger.info(f"Pixel sampling took: {sampling_time - start_time:.3f} seconds")
        
        # Fit KMeans
        logger.info("Starting KMeans fitting")
        kmeans = KMeans(n_clusters=num_colors, random_state=0, n_init=10)
        kmeans.fit(pixels)
        
        fitting_time = time.time()
        logger.info(f"KMeans fitting took: {fitting_time - sampling_time:.3f} seconds")
        logger.info(f"Cluster centers shape: {kmeans.cluster_centers_.shape}")
        logger.info(f"Cluster centers min/max: {kmeans.cluster_centers_.min()}/{kmeans.cluster_centers_.max()}")
        
        # Convert to colors
        colors = [Color(tuple(color), ColorType.LAB) for color in kmeans.cluster_centers_.astype(int)]
        
        total_time = time.time() - start_time
        logger.info(f"Total KMeans color extraction took: {total_time:.3f} seconds")
        
        return colors