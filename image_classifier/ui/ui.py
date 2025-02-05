import matplotlib

matplotlib.use("TkAgg")  # Force the correct backend
import matplotlib.pyplot as plt
import numpy as np


def display_multiple_classifiers(classifier_results, title="Extracted Colors from Different Classifiers"):
    num_classifiers = len(classifier_results)
    max_colors = max(len(colors) for colors in classifier_results.values())

    fig, ax = plt.subplots(num_classifiers, 1, figsize=(max_colors, num_classifiers * 1.5), constrained_layout=True)

    if num_classifiers == 1:
        ax = [ax]

    for i, (classifier_name, colors) in enumerate(classifier_results.items()):
        gradient = np.zeros((1, len(colors), 3), dtype=np.uint8)

        for j, color in enumerate(colors):
            gradient[:, j] = color

        ax[i].imshow(gradient, aspect='auto')
        ax[i].set_xticks([])
        ax[i].set_yticks([])
        ax[i].set_title(classifier_name, fontsize=10)

    plt.suptitle(title, fontsize=12)
    plt.show()
