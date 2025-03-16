import time

import nuke
import os
import tempfile
from pathlib import Path

from image_classifier.classifiers.base_classifier import ClassifierType
from image_classifier.controller import create_palette


def generate_palette(node):
    """
    Triggers the Write node in the Gizmo, extracts the image,
    and runs the palette generation script.
    """
    # Get user settings
    num_colors = int(nuke.value('numcolors'))
    classifier_str = nuke.value('Classifier')

    # Map string to enum
    classifier_map = {
        "Guassian Mixture": ClassifierType.GUASSIANMIXTURE,
        "Median Cut": ClassifierType.MEDIANCUT,
        "K-Means": ClassifierType.KMEANS
    }
    classifier = classifier_map[classifier_str]

    # Get the internal Write node
    write_node = node.node("Write1")
    if not write_node:
        nuke.message("Error: Internal Write node not found in Gizmo.")
        return

    # Set up temp output file
    temp_dir = tempfile.gettempdir()
    #out_path = os.path.join(temp_dir, "palette_tmp.png")

    # Update Write node settings
    #write_node["file"].setValue(out_path)
    #nuke.message(out_path)

    # Execute Write node
    frame = int(nuke.frame())
    nuke.execute(write_node, frame, frame)
    palette = create_palette("C:/palette_tmp.png", num_colors, classifier)


    node.begin()

    # 🛑 Delete old Constant nodes & ContactSheet if they exist
    for existing in node.nodes():
        if existing.Class() in ["Constant", "ContactSheet"]:
            nuke.delete(existing)

    # ✅ Create new Constant nodes inside the Group
    constants = []
    for i, color in enumerate(palette):
        const = nuke.createNode("Constant", f"name Constant{i}")
        rgb = [clr/255 for clr in color.rgb]
        rgb.append(1)
        const["color"].setValue(rgb)  # Set the extracted color
        # Ensure the format exists (Creates a new 10x10 format if it doesn't exist)
        palette_format = nuke.addFormat("10 10 1")  # Width, Height, Pixel Aspect Ratio

        # Set the format on the Constant node
        const["format"].setValue(palette_format)
        const["xpos"].setValue(i * 50)  # Space out nodes in the Node Graph
        constants.append(const)

    # ✅ Create ContactSheet
    contactsheet = nuke.createNode("ContactSheet", "name ContactSheet")
    contactsheet["columns"].setValue(num_colors)  # One row, multiple columns
    contactsheet["rows"].setValue(1)
    contactsheet["width"].setValue(10 * num_colors)  # 10px width per color
    contactsheet["height"].setValue(10)  # Fixed height
    contactsheet["center"].setValue(True)

    # Connect all Constant nodes to ContactSheet
    for i, const in enumerate(constants):
        contactsheet.setInput(i, const)

    # ✅ Connect ContactSheet to Output
    output_node = node.node("Output1")
    if output_node:
        output_node.setInput(0, contactsheet)
    else:
        print("⚠️ Warning: Output1 node not found.")

    # ✅ Exit Group context ONCE
    node.end()
