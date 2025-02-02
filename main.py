from UI.ui import display_multiple_classifiers
from classifiers.guassian_mixture import GMMColorClassifier
from classifiers.k_means import KMeansColorClassifier
from classifiers.median_cut import MedianCutColorClassifier
from processing.color_sorting import sort_by_lab
from processing.image_processor import ImageProcessor

if __name__ == '__main__':

    # Load Image
    image_path = "testimages/duneposter.jpg"
    image_processor = ImageProcessor(image_path, None)  # No classifier yet

    # Run all classifiers
    classifier_results = {
        "K-Means": sort_by_lab(KMeansColorClassifier().extract_colors(image_processor.image, 5)),
        "Median Cut": sort_by_lab(MedianCutColorClassifier().extract_colors(image_processor.image, 5)),
        "Guassian Mixture": sort_by_lab(GMMColorClassifier().extract_colors(image_processor.image, 5)),
    }

    # Display all results
    display_multiple_classifiers(classifier_results)