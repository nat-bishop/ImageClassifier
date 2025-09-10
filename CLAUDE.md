# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Installation
```bash
pip install -r requirements.txt
```
Note: The requirements.txt file has encoding issues. Dependencies are:
- numpy>=1.0,<2.0
- scikit-learn>=1.6,<2.0
- pillow>=11.1,<12.0
- opencv-python>=4.11,<5.0
- PySide6>=6.0,<7.0
- qt-material-icons>=0.2,<1.0
- qt-themes>=0.3,<1.0

### Running the Application
```bash
python main.py
```

### Running Tests
```bash
# Run all tests
python -m unittest discover

# Run specific test file
python -m unittest image_classifier.tests.test_color_harmony
```

### Nuke Integration
For Nuke integration, users need to:
1. Copy `NukeFIles/imageClassifier.gizmo` and `NukeFIles/init.py` to their Nuke installation
2. Update the path in `init.py` to point to this ImageClassifier directory
3. Install dependencies in Nuke's Python environment:
   ```bash
   "<Path to nuke python>" -m pip install "<path to ImageClassifier dir>"
   ```

## Architecture

### Application Structure
This is a PySide6 Qt application for color harmony analysis that processes images in LAB color space.

**Core Flow:**
1. User loads image via drag-drop or file dialog → `ImageDropWidget`
2. Background thread processes image → `ColorGenerationThread`
3. Controller creates palette → `controller.create_palette()`
4. ImageProcessor loads and converts to LAB → `ImageProcessor`
5. Classifier extracts dominant colors → `ColorClassifier` implementations
6. Colors sorted and analyzed for harmony → `color_harmony` scoring functions
7. Results displayed with copy-to-clipboard functionality

### Key Components

**Entry Points:**
- `main.py`: Application entry point, initializes Qt app with 'one_dark_two' theme
- `image_classifier/nuke.py`: Nuke integration module

**MVC Pattern:**
- **Controller**: `controller.py` - Coordinates color extraction and harmony analysis
- **View**: `ui/app.py` - Main window with image display, color palette, and harmony metrics
- **Model**: `Color` class, classifiers, and processing modules

**Color Extraction Algorithms** (in `classifiers/`):
- `KMeansColorClassifier`: K-means clustering
- `GMMColorClassifier`: Gaussian Mixture Model
- `MedianCutColorClassifier`: Median cut algorithm
All inherit from `ColorClassifier` base class

**Color Processing** (in `processing/`):
- `ImageProcessor`: Loads images and converts BGR → LAB color space
- `color_harmony.py`: Scoring functions for triadic, complementary, analogous, monochromatic, etc.
- `color_sorting.py`: Sorts colors by LAB values

**Storage:**
- `PaletteStorage`: Manages saved palettes with JSON persistence
- `Palette` dataclass: Stores palette metadata and colors

**UI Components:**
- `MainWindow`: Main application window with tabbed interface
- `ImageDropWidget`: Drag-and-drop image input area
- `LibraryView`: Displays saved palettes
- `WelcomeDialog`: First-run welcome screen and tour system

### Threading
Background processing uses `ColorGenerationThread` (QThread) to prevent UI blocking during color extraction.

### Color Spaces
- Input: RGB from image files
- Processing: LAB color space (perceptually uniform)
- Output: RGB, HSL, and LAB values with click-to-copy