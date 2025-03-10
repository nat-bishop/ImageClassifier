import nuke
import os
import tempfile
from pathlib import Path

from image_classifier.classifiers.base_classifier import ClassifierType
from image_classifier.controller import create_palette


def generate_palette(node):
    # 1) Read user knob values
    num_colors = int(node["num_colors"].value())
    classifier_str = node["classifier_type"].value()

    # Map string to enum
    classifier_map = {
        "GaussianMixture": ClassifierType.GaussianMixture,
        "MedianCut": ClassifierType.MedianCut,
        "KMeans": ClassifierType.KMeans
    }
    classifier = classifier_map.get(classifier_str, ClassifierType.KMeans)

    input_node = node.input(0)
    if not input_node:
        nuke.message("Please connect an input to the MyPaletteExtractor node.")
        return

    # 2) Save a temporary frame as EXR
    frame = int(nuke.root().frame())
    temp_dir = tempfile.gettempdir()
    out_path = os.path.join(temp_dir, "palette_extract_temp.exr")

    write_node = nuke.createNode("Write", inpanel=False)
    write_node.setInput(0, input_node)
    write_node["channels"].setValue("rgb")
    write_node["file"].setValue(out_path)
    write_node["use_limit"].setValue(False)
    write_node["create_directories"].setValue(True)

    nuke.execute(write_node.name(), frame, frame)
    nuke.delete(write_node)  # Cleanup

    # 3) Extract palette
    palette = create_palette(Path(out_path), num_colors, classifier)

    # 4) Store colors in knobs
    for i in range(5):
        knob_name = f"color{i + 1}"
        if i < len(palette):
            r, g, b = palette[i].rgb
            node[knob_name].setValue(f"{r},{g},{b}")
        else:
            node[knob_name].setValue("")
