import matplotlib

matplotlib.use("TkAgg")  # Force the correct backend
import matplotlib.pyplot as plt
import numpy as np
import cv2


def generate_color_wheel(size=300):
    """Generates an HSV-based color wheel with 0 saturation in the center."""
    radius = size // 2
    x, y = np.meshgrid(np.linspace(-1, 1, size), np.linspace(-1, 1, size))
    r = np.sqrt(x**2 + y**2)  # Distance from center
    theta = np.arctan2(y, x) * (180 / np.pi)  # Convert to degrees

    # Normalize theta to 0-360°
    hue = (theta + 360) % 360
    sat = np.clip(r, 0, 1)  # Keep saturation between 0 and 1
    val = np.ones_like(hue)  # Full brightness (V=1)

    # Stack to create HSV image
    hsv = np.stack([hue / 2, sat * 255, val * 255], axis=-1).astype(np.uint8)
    color_wheel = cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)

    return color_wheel


def plot_color_wheel_with_highlights(ax, colors, wheel_size=300):
    """Plots the color wheel and highlights extracted colors."""
    color_wheel = generate_color_wheel(wheel_size)

    ax.imshow(color_wheel, extent=[-1, 1, -1, 1], aspect='auto')
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title("Color Wheel", fontsize=10)

    # Convert RGB colors to HSV for correct placement
    for color in colors:
        hsv_color = cv2.cvtColor(np.uint8([[color]]), cv2.COLOR_RGB2HSV)[0][0]
        hue = hsv_color[0] * 2  # OpenCV scales hue from 0-180
        sat = hsv_color[1] / 255.0  # Normalize saturation

        # Convert hue and saturation to x, y for plotting
        x = sat * np.cos(np.radians(hue))
        y = sat * np.sin(np.radians(hue))

        ax.plot(x, y, 'o', markersize=8, markeredgecolor='black', markerfacecolor=np.array(color) / 255.0)


def display_multiple_classifiers(classifier_results, title="Extracted Colors from Different Classifiers"):
    """Displays extracted colors as gradients and plots a color wheel."""
    num_classifiers = len(classifier_results)
    max_colors = max(len(colors) for colors in classifier_results.values())

    fig, axes = plt.subplots(num_classifiers, 2, figsize=(max_colors * 1.5, num_classifiers * 2), constrained_layout=True)

    if num_classifiers == 1:
        axes = [axes]

    for i, (classifier_name, colors) in enumerate(classifier_results.items()):
        gradient = np.zeros((1, len(colors), 3), dtype=np.uint8)

        for j, color in enumerate(colors):
            gradient[:, j] = color

        # Left panel: Display extracted color gradient
        axes[i][0].imshow(gradient, aspect='auto')
        axes[i][0].set_xticks([])
        axes[i][0].set_yticks([])
        axes[i][0].set_title(classifier_name, fontsize=10)

        # Right panel: Display color wheel with highlights
        plot_color_wheel_with_highlights(axes[i][1], colors)

    plt.suptitle(title, fontsize=12)
    plt.show()