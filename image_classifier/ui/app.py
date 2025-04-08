from __future__ import annotations

import logging
import math
import sys
import numpy as np
import time  # Add at the top with other imports

from image_classifier.preferences import load_preferences, store_preferences
from image_classifier.processing.color_harmony import (
    circular_mean,
    circular_diff,
    score_complementary,
    score_split_complementary,
    score_triadic,
    score_square,
    score_monochromatic
)
from image_classifier.storage.palette_storage import Palette, PaletteStorage
from datetime import datetime

# Configure logging to show INFO messages
logging.basicConfig(level=logging.WARNING, format="%(asctime)s - %(levelname)s - %(message)s")
logging.getLogger().setLevel(logging.WARNING)

import PySide6.QtCore as QtCore
import PySide6.QtGui as QtGui
import PySide6.QtWidgets as QtWidgets
import qt_themes
from qt_material_icons import MaterialIcon

from image_classifier.color import Color, ColorType
from image_classifier.controller import analyze_palette_harmony
from image_classifier.ui.background_process import ColorGenerationThread
from image_classifier.ui.library_view import LibraryView


########################################################
# ImageDropWidget (Fills most of the window)
########################################################
class ImageDropWidget(QtWidgets.QLabel):
    image_selected = QtCore.Signal(str)

    def __init__(self, parent: QtWidgets.QWidget = None) -> None:
        super().__init__(parent)
        # Create a container widget for the icon and text
        self.container = QtWidgets.QWidget(self)
        self.container.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        
        # Create a vertical layout for the container
        layout = QtWidgets.QVBoxLayout(self.container)
        layout.setAlignment(QtCore.Qt.AlignCenter)
        layout.setSpacing(10)  # Space between icon and text
        
        # Add top spacer to push everything up
        layout.addStretch(1)
        
        # Create and add the title label
        self.title_label = QtWidgets.QLabel("Extract color from an image and\nsave them as color palette")
        self.title_label.setAlignment(QtCore.Qt.AlignCenter)
        self.title_label.setStyleSheet("color: rgba(255, 255, 255, 150); font-size: 14pt;")
        layout.addWidget(self.title_label)
        
        # Add fixed-height spacer between title and icon
        spacer = QtWidgets.QSpacerItem(0, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed)
        layout.addSpacerItem(spacer)
        
        # Create and add the icon label
        self.icon_label = QtWidgets.QLabel()
        self.icon_label.setAlignment(QtCore.Qt.AlignCenter)
        self.icon_pixmap = MaterialIcon("place_item").pixmap(QtCore.QSize(75, 75))
        self.icon_label.setPixmap(self.icon_pixmap)
        layout.addWidget(self.icon_label)
        
        # Create and add the instruction labels
        self.drag_label = QtWidgets.QLabel("Drag and Drop your file")
        self.drag_label.setAlignment(QtCore.Qt.AlignCenter)
        self.drag_label.setStyleSheet("color: rgba(255, 255, 255, 200); font-size: 24pt; font-weight: bold;")
        layout.addWidget(self.drag_label)
        
        self.or_label = QtWidgets.QLabel("or Select a file from your computer")
        self.or_label.setAlignment(QtCore.Qt.AlignCenter)
        self.or_label.setStyleSheet("color: rgba(255, 255, 255, 200); font-size: 12pt;")
        layout.addWidget(self.or_label)
        
        # Add bottom spacer
        layout.addStretch(1)
        
        # Set the container as the widget's layout
        self.setLayout(QtWidgets.QVBoxLayout())
        self.layout().addWidget(self.container)
        
        # Ignore the pixmap's default size; label can shrink below it
        self.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Ignored)
        self.setAcceptDrops(True)
        self.setAlignment(QtCore.Qt.AlignCenter)
        
        self._original_pixmap = QtGui.QPixmap()
        self.show_border = True  # Initially show the border
        logging.info('initializing ImageDropWidget')

        # Show pointing-hand cursor on hover
        self.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))

        # Enable mouse tracking for hover events
        self.setMouseTracking(True)
        self.is_hovered = False

        # Add attributes for color sampling circles
        self.sampling_points = []  # List of (x, y) coordinates for each color
        self.circle_radius = 20  # Increased radius from 10 to 20
        self.dragging_index = -1  # Track which circle is being dragged
        self.dragging_radius = 20  # Radius for detecting drag
        self.press_time = None  # Track when mouse was pressed
        self.click_threshold = 200  # milliseconds to consider it a click
        self.is_dragging = False  # Track if we're currently dragging

        # Add caching for color matches
        self._color_cache = {}  # Cache for color matches
        self._last_image_hash = None  # Track if image changed
        self._cached_pixels = None  # Cache for pixel coordinates
        self._cached_width = None
        self._cached_height = None

        # Add a flag to track if we're currently dragging
        self.is_user_dragging = False

    def update_icon(self) -> None:
        if not self.icon_pixmap.isNull():
            self.icon_label.setPixmap(self.icon_pixmap)
        else:
            logging.warning("Icon failed to load.")

    def load_image(self, path: str) -> None:
        pixmap = QtGui.QPixmap(path)
        if not pixmap.isNull():
            self._original_pixmap = pixmap
            self._update_displayed_pixmap()
            self.show_border = False  # Hide border when an image is loaded
            self.setStyleSheet("background-color: black;")
            # Hide the container when an image is loaded
            self.container.hide()
            self.update()
        self.image_selected.emit(path)

    def _update_displayed_pixmap(self) -> None:
        if not self._original_pixmap.isNull():
            scaled = self._original_pixmap.scaled(
                self.size(),
                QtCore.Qt.KeepAspectRatio,
                QtCore.Qt.SmoothTransformation
            )
            self.setPixmap(scaled)
        else:
            # Show the container again if no image is loaded
            self.container.show()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._update_displayed_pixmap()

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        urls = event.mimeData().urls()
        if urls:
            logging.info(f"dropped image: {urls}")
            file_path = urls[0].toLocalFile()
            self.load_image(file_path)

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.button() == QtCore.Qt.LeftButton:
            # First check if we're clicking on a circle
            idx = self.find_circle_under_mouse(event.pos())
            if idx != -1:
                self.dragging_index = idx
                self.press_time = QtCore.QTime.currentTime()
                self.is_dragging = False
                self.is_user_dragging = True  # Set the flag when user starts dragging
            else:
                # If not clicking on a circle, handle image selection
                file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
                    self, "Open Image", "",
                    "Images (*.png *.jpg *.jpeg *.bmp)"
                )
                if file_path:
                    logging.info(f'selected image at filepath: {file_path}')
                    self.load_image(file_path)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        if self.dragging_index != -1:
            self.is_dragging = True
            # Get the new position
            new_pos = self.pos_to_image_coords(event.pos())
            if new_pos:
                x, y = new_pos
                # Update the sampling point
                old_point, color = self.sampling_points[self.dragging_index]
                self.sampling_points[self.dragging_index] = ((x, y), color)
                # Update the color from the new position
                self.update_color_from_position(self.dragging_index)
                self.update()  # Trigger a repaint
            self.setCursor(QtGui.QCursor(QtCore.Qt.CrossCursor))
        else:
            # Check if we're hovering over a circle
            idx = self.find_circle_under_mouse(event.pos())
            if idx != -1:
                self.setCursor(QtGui.QCursor(QtCore.Qt.CrossCursor))
                self.hovered_index = idx  # Track which circle is being hovered
                self.update()  # Trigger a repaint to show transparency
            else:
                self.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
                self.hovered_index = -1  # Clear hover state
                self.update()  # Trigger a repaint to remove transparency
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.button() == QtCore.Qt.LeftButton and self.dragging_index != -1:
            # Check if this was a quick click (less than threshold)
            if self.press_time is not None:
                elapsed = self.press_time.msecsTo(QtCore.QTime.currentTime())
                if elapsed < self.click_threshold and not self.is_dragging:
                    # It was a click, show color picker
                    self.show_color_picker(self.dragging_index)
            self.dragging_index = -1
            self.press_time = None
            self.is_dragging = False
            self.is_user_dragging = False  # Clear the flag when user stops dragging
        super().mouseReleaseEvent(event)

    def find_circle_under_mouse(self, pos: QtCore.QPointF) -> int:
        """Returns the index of the circle under the mouse, or -1 if none."""
        if not self._original_pixmap.isNull():
            # Calculate scaling factors
            pixmap_width = self._original_pixmap.width()
            pixmap_height = self._original_pixmap.height()
            widget_width = self.width()
            widget_height = self.height()
            
            scale = min(widget_width / pixmap_width, widget_height / pixmap_height)
            scaled_width = pixmap_width * scale
            scaled_height = pixmap_height * scale
            
            x_offset = (widget_width - scaled_width) / 2
            y_offset = (widget_height - scaled_height) / 2
            
            # Check each circle
            for i, ((x, y), _) in enumerate(self.sampling_points):
                scaled_x = x * scale + x_offset
                scaled_y = y * scale + y_offset
                
                dx = scaled_x - pos.x()
                dy = scaled_y - pos.y()
                if (dx*dx + dy*dy) <= (self.dragging_radius*self.dragging_radius):
                    return i
        return -1

    def pos_to_image_coords(self, pos: QtCore.QPointF) -> tuple[int, int] | None:
        """Convert widget coordinates to image coordinates."""
        if self._original_pixmap.isNull():
            return None
            
        pixmap_width = self._original_pixmap.width()
        pixmap_height = self._original_pixmap.height()
        widget_width = self.width()
        widget_height = self.height()
        
        scale = min(widget_width / pixmap_width, widget_height / pixmap_height)
        scaled_width = pixmap_width * scale
        scaled_height = pixmap_height * scale
        
        x_offset = (widget_width - scaled_width) / 2
        y_offset = (widget_height - scaled_height) / 2
        
        # Convert widget coordinates to image coordinates
        x = int((pos.x() - x_offset) / scale)
        y = int((pos.y() - y_offset) / scale)
        
        # Check if the coordinates are within the image bounds
        if 0 <= x < pixmap_width and 0 <= y < pixmap_height:
            return (x, y)
        return None

    def update_color_from_position(self, index: int) -> None:
        """Update the color at the given index based on its current position."""
        if not self._original_pixmap.isNull():
            image = self._original_pixmap.toImage()
            (x, y), _ = self.sampling_points[index]
            
            if 0 <= x < image.width() and 0 <= y < image.height():
                color = QtGui.QColor(image.pixel(x, y))
                new_color = Color((color.red(), color.green(), color.blue()), ColorType.RGB)
                self.sampling_points[index] = ((x, y), new_color)
                
                # Find the main window and update the palette
                main_window = self.window()
                if main_window and hasattr(main_window, 'palette'):
                    main_window.palette.colors[index] = new_color
                    main_window.palette.update_colors()
                    # Update color wheel if it exists
                    if hasattr(main_window.palette, 'color_wheel'):
                        main_window.palette.color_wheel.update()
                    # Update color harmony if it exists
                    if hasattr(main_window.palette, 'color_harmony'):
                        main_window.palette.color_harmony.update_harmony()

    def show_color_picker(self, index: int) -> None:
        """Show the color picker dialog for the color at the given index."""
        _, color = self.sampling_points[index]
        initial = QtGui.QColor(*color.rgb)
        chosen = QtWidgets.QColorDialog.getColor(
            initial=initial,
            parent=self,
            title="Select a Color"
        )
        if chosen.isValid():
            new_color = Color((chosen.red(), chosen.green(), chosen.blue()), ColorType.RGB)
            self.sampling_points[index] = (self.sampling_points[index][0], new_color)
            if hasattr(self.parent(), 'palette_widget'):
                self.parent().palette_widget.colors[index] = new_color
                self.parent().palette_widget.update_colors()
            self.update()

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        super().paintEvent(event)
        if self.show_border:
            painter = QtGui.QPainter(self)
            painter.setRenderHint(QtGui.QPainter.Antialiasing)

            # Dashed border
            pen = QtGui.QPen(QtGui.QColor(150, 150, 150))
            pen.setStyle(QtCore.Qt.DashLine)
            pen.setWidth(2)
            painter.setPen(pen)

            rect = self.rect().adjusted(6, 6, -6, -6)
            painter.drawRect(rect)

        # Draw sampling circles if we have an image
        if not self._original_pixmap.isNull() and self.sampling_points:
            painter = QtGui.QPainter(self)
            painter.setRenderHint(QtGui.QPainter.Antialiasing)
            
            # Calculate scaling factors based on the actual image dimensions
            pixmap_width = self._original_pixmap.width()
            pixmap_height = self._original_pixmap.height()
            widget_width = self.width()
            widget_height = self.height()
            
            # Calculate the scaled dimensions while maintaining aspect ratio
            scale = min(widget_width / pixmap_width, widget_height / pixmap_height)
            scaled_width = pixmap_width * scale
            scaled_height = pixmap_height * scale
            
            # Calculate the offset to center the image
            x_offset = (widget_width - scaled_width) / 2
            y_offset = (widget_height - scaled_height) / 2
            
            for i, ((x, y), color) in enumerate(self.sampling_points):
                # Scale and offset the coordinates
                scaled_x = x * scale + x_offset
                scaled_y = y * scale + y_offset
                
                # Draw the circle with white border
                painter.setPen(QtGui.QPen(QtCore.Qt.white, 2))
                
                # Set transparency based on hover/drag state
                alpha = 128 if (i == self.hovered_index or i == self.dragging_index) else 255
                brush_color = QtGui.QColor(*color.rgb)
                brush_color.setAlpha(alpha)
                painter.setBrush(brush_color)
                
                # Make the circle being dragged slightly larger
                radius = self.circle_radius * 1.2 if i == self.dragging_index else self.circle_radius
                painter.drawEllipse(QtCore.QPointF(scaled_x, scaled_y), radius, radius)

    def set_border_visibility(self, visible: bool) -> None:
        logging.debug(f'changing border visibility to: {visible}')
        self.show_border = visible
        self.update()

    def enterEvent(self, event: QtGui.QEvent) -> None:
        self.is_hovered = True
        super().enterEvent(event)

    def leaveEvent(self, event: QtGui.QEvent) -> None:
        self.is_hovered = False
        super().leaveEvent(event)

    def _get_image_hash(self) -> str:
        """Generate a simple hash of the image for caching purposes."""
        if self._original_pixmap.isNull():
            return ""
        return str(self._original_pixmap.cacheKey())

    def _generate_pixel_coordinates(self, width: int, height: int) -> list:
        """Generate or retrieve cached pixel coordinates."""
        if (self._cached_pixels is not None and 
            self._cached_width == width and 
            self._cached_height == height):
            return self._cached_pixels
        
        # Generate coordinates using numpy for speed
        y_coords, x_coords = np.mgrid[0:height, 0:width]
        pixels = np.column_stack((x_coords.ravel(), y_coords.ravel()))
        self._cached_pixels = pixels
        self._cached_width = width
        self._cached_height = height
        return pixels

    def update_circles(self, colors: list[Color]) -> None:
        """Update the sampling points for the given colors."""
        if self._original_pixmap.isNull() or self.is_user_dragging:
            return

        start_time = time.time()
        logging.info("Starting update_circles")

        # Check if we can use cached results
        current_image_hash = self._get_image_hash()
        if current_image_hash == self._last_image_hash:
            # Try to use cached results for each color
            cached_points = []
            for color in colors:
                color_key = tuple(color.rgb)
                if color_key in self._color_cache:
                    cached_points.append((self._color_cache[color_key], color))
                else:
                    break
            else:
                # All colors were in cache
                self.sampling_points = cached_points
                self.update()
                logging.info(f"Using cached results, took: {time.time() - start_time:.3f} seconds")
                return

        # Convert pixmap to image for pixel access
        image = self._original_pixmap.toImage()
        width = image.width()
        height = image.height()

        # Further reduce number of samples
        num_samples = 10000  # Reduced from 50000
        
        # Get pixel coordinates (using cached if available)
        all_pixels = self._generate_pixel_coordinates(width, height)
        
        # Sample random pixels using numpy
        sample_indices = np.random.choice(len(all_pixels), num_samples, replace=False)
        sample_points_np = all_pixels[sample_indices]
        
        # Pre-calculate all pixel colors as numpy array
        pixel_colors_np = np.zeros((num_samples, 3), dtype=np.uint8)
        for i, (x, y) in enumerate(sample_points_np):
            color = QtGui.QColor(image.pixel(int(x), int(y)))
            pixel_colors_np[i] = [color.red(), color.green(), color.blue()]
        
        sampling_time = time.time()
        logging.info(f"Sampling setup took: {sampling_time - start_time:.3f} seconds")
        
        # Process colors that aren't in cache
        self.sampling_points = []
        for color in colors:
            color_key = tuple(color.rgb)
            if color_key in self._color_cache:
                # Use cached position for existing colors
                self.sampling_points.append((self._color_cache[color_key], color))
            else:
                # Calculate new position for new or changed colors
                target_rgb = np.array(color.rgb)
                distances = np.sum((pixel_colors_np - target_rgb) ** 2, axis=1)
                closest_index = np.argmin(distances)
                closest_point = tuple(sample_points_np[closest_index])
                self.sampling_points.append((closest_point, color))
                self._color_cache[color_key] = closest_point
        
        self._last_image_hash = current_image_hash
        
        color_matching_time = time.time()
        logging.info(f"Color matching took: {color_matching_time - sampling_time:.3f} seconds")
        
        self.update()  # Trigger a repaint
        
        total_time = time.time() - start_time
        logging.info(f"Total update_circles took: {total_time:.3f} seconds")


########################################################
# ColorBox
########################################################
class ColorBox(QtWidgets.QLabel):
    """
    A color box that displays its background color.
    Clicking on the box opens a QColorDialog to pick a new color.
    That updates the parent's palette, color wheel, and color harmony.
    """

    def __init__(
        self,
        color: Color,
        index: int,
        palette_widget: 'ColorPalette',
        parent: QtWidgets.QWidget = None
    ) -> None:
        super().__init__(parent)
        self.color = color
        self.index = index
        self.palette_widget = palette_widget
        self.setAutoFillBackground(True)
        self.setAlignment(QtCore.Qt.AlignBottom | QtCore.Qt.AlignHCenter)  # Align text to bottom center
        self.setContentsMargins(0, 0, 0, 10)  # Add bottom margin for text
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

        # Show pointing-hand cursor on hover
        self.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))

        # Enable mouse tracking for hover events
        self.setMouseTracking(True)
        self.is_hovered = False

        self.update_appearance()
        self.setToolTip("Click to pick a new color")

    def update_appearance(self) -> None:
        palette = self.palette()
        qcolor = QtGui.QColor(*self.color.rgb)
        palette.setColor(QtGui.QPalette.Window, qcolor)
        
        # Set text color to white or black based on background brightness
        brightness = (qcolor.red() * 299 + qcolor.green() * 587 + qcolor.blue() * 114) / 1000
        text_color = QtCore.Qt.white if brightness < 128 else QtCore.Qt.black
        
        # Create semi-transparent text color
        text_color = QtGui.QColor(text_color)
        text_color.setAlpha(128 if not self.is_hovered else 255)
        palette.setColor(QtGui.QPalette.WindowText, text_color)

        self.setPalette(palette)
        self.setBackgroundRole(QtGui.QPalette.Window)
        self.setForegroundRole(QtGui.QPalette.WindowText)
        
        # Only show RGB text if we're not in progress animation
        if not self.palette_widget.in_progress_animation:
            self.setText(f"RGB: {self.color.rgb[0]}, {self.color.rgb[1]}, {self.color.rgb[2]}")
        else:
            self.setText("")

    def enterEvent(self, event: QtGui.QEvent) -> None:
        self.is_hovered = True
        self.update_appearance()
        super().enterEvent(event)

    def leaveEvent(self, event: QtGui.QEvent) -> None:
        self.is_hovered = False
        self.update_appearance()
        super().leaveEvent(event)

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.button() == QtCore.Qt.LeftButton:
            initial = QtGui.QColor(*self.color.rgb)
            chosen = QtWidgets.QColorDialog.getColor(
                initial=initial,
                parent=self,
                title="Select a Color"
            )
            if chosen.isValid():
                new_color = Color((chosen.red(), chosen.green(), chosen.blue()), ColorType.RGB)
                self.color = new_color
                self.update_appearance()
                self.palette_widget.colors[self.index] = new_color
                self.palette_widget.update_colors()
                if self.palette_widget.color_wheel:
                    self.palette_widget.color_wheel.repaint()
                if self.palette_widget.color_harmony:
                    self.palette_widget.color_harmony.update_harmony()
        super().mousePressEvent(event)


########################################################
# ColorPalette
########################################################
class ColorPalette(QtWidgets.QWidget):
    """
    Horizontally displayed color palette beneath the image.
    """

    def __init__(self, parent: QtWidgets.QWidget = None) -> None:
        super().__init__(parent)
        self.layout = QtWidgets.QHBoxLayout(self)
        self.layout.setSpacing(0)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.layout)
        self.setMinimumHeight(120)
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        logging.info('initializing ColorPalette widget')

        # Show pointing-hand cursor for the entire palette
        self.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))

        self.colors = []
        self.generated_colors = []
        self.image_path = None
        self.color_wheel = None
        self.color_harmony = None
        self.image_drop = None  # Initialize image_drop attribute
        self.preferences = load_preferences()  # Load preferences
        self.current_num_colors = self.preferences.get("num_colors", 5)  # Track current number of colors
        self.in_progress_animation = False  # Flag to track progress animation state

        self.progress_timer = QtCore.QTimer(self)
        self.progress_timer.timeout.connect(self.update_progress)
        self.progress_index = 0
        self.color_thread = None
        self.set_default_colors()

    def set_default_colors(self) -> None:
        # Store all default colors
        self.generated_colors = [
            Color((252, 231, 200), ColorType.RGB),  # Warm beige
            Color((177, 194, 158), ColorType.RGB),  # Sage green
            Color((250, 218, 122), ColorType.RGB),  # Soft yellow
            Color((240, 160, 75), ColorType.RGB),   # Warm orange
            Color((200, 180, 220), ColorType.RGB),  # Soft purple
            Color((150, 200, 255), ColorType.RGB),  # Light blue
            Color((255, 150, 150), ColorType.RGB),  # Soft pink
            Color((180, 220, 180), ColorType.RGB),  # Mint green
            Color((255, 200, 150), ColorType.RGB),  # Peach
        ]
        
        # Show the current number of colors
        self.colors = self.generated_colors[:self.current_num_colors]
        self.update_colors()
        logging.info(f'Set default colors for color palette with {self.current_num_colors} colors')

    def set_image_path(self, image_path: str) -> None:
        self.image_path = image_path
        self.generate_colors()

    def set_color_wheel(self, color_wheel: 'ColorWheel') -> None:
        self.color_wheel = color_wheel

    def set_color_harmony(self, color_harmony: 'ColorHarmony') -> None:
        self.color_harmony = color_harmony

    def set_image_drop(self, image_drop: 'ImageDropWidget') -> None:
        self.image_drop = image_drop

    def generate_colors(self) -> None:
        if not self.image_path:
            logging.warning('No image path when generating colors')
            return

        self.clear_colors_except_label()
        self.start_progress_animation()
        logging.info('Starting color generation')

        # Always generate 9 colors, but only display the number from preferences
        self.color_thread = ColorGenerationThread(self.image_path, num_colors=9)
        self.color_thread.colors_generated.connect(self.on_colors_generated)
        self.color_thread.start()

    def start_progress_animation(self) -> None:
        self.in_progress_animation = True  # Set progress animation flag
        self.progress_index = 0
        self.progress_timer.start(200)
        theme_bg_color = self.palette().color(QtGui.QPalette.Window)
        self.colors = [Color((theme_bg_color.red(), theme_bg_color.green(), theme_bg_color.blue()), ColorType.RGB)
                       for _ in range(len(self.colors))]
        self.update_colors()

    def update_progress(self) -> None:
        if self.progress_index >= len(self.colors):
            self.progress_index = 0

        theme_bg_color = self.palette().color(QtGui.QPalette.Window)
        theme_progress_color = theme_bg_color.lighter(120)
        self.colors = [Color((theme_bg_color.red(), theme_bg_color.green(), theme_bg_color.blue()), ColorType.RGB)
                       for _ in range(len(self.colors))]

        if self.progress_index < len(self.colors):
            self.colors[self.progress_index] = Color(
                (theme_progress_color.red(), theme_progress_color.green(), theme_progress_color.blue()),
                ColorType.RGB
            )
        self.update_colors()
        self.progress_index += 1

    def on_colors_generated(self, colors: list[Color]) -> None:
        self.progress_timer.stop()
        self.in_progress_animation = False  # Clear progress animation flag
        if not colors:
            return
        logging.info('completed color generation, stopping progress animation and updating colors.')
        self.generated_colors = colors
        # Show the current number of colors
        self.colors = colors[:self.current_num_colors]
        self.update_colors()
        if self.color_wheel:
            self.color_wheel.update()
            self.color_wheel.repaint()
        if self.color_harmony:
            self.color_harmony.update_harmony()

    def clear_colors_except_label(self) -> None:
        logging.info('clearing colors from color palette')
        for i in reversed(range(self.layout.count())):
            item = self.layout.itemAt(i)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def update_colors(self) -> None:
        start_time = time.time()
        self.clear_colors_except_label()
        logging.info('updating colors')
        for i, c in enumerate(self.colors):
            box = ColorBox(c, i, self, parent=self)
            self.layout.addWidget(box)
        if self.color_harmony:
            self.color_harmony.update_harmony()
        # Only update circles if we're not in progress animation
        if self.image_drop and not self.in_progress_animation:
            self.image_drop.update_circles(self.colors)
        logging.info(f"Total update_colors took: {time.time() - start_time:.3f} seconds")

    def add_color(self) -> None:
        if len(self.colors) < len(self.generated_colors):
            self.current_num_colors += 1  # Update the current number of colors
            self.colors.append(self.generated_colors[len(self.colors)])
            self.update_colors()
            logging.info(f'adding color: {self.generated_colors[len(self.colors)]} to color palette')
            if self.color_wheel:
                self.color_wheel.repaint()
            if self.color_harmony:
                self.color_harmony.update_harmony()

    def remove_color(self) -> None:
        if self.colors:
            self.current_num_colors -= 1  # Update the current number of colors
            logging.info(f'removing color: {self.colors[-1]} from color palette')
            self.colors.pop()
            self.update_colors()
            if self.color_wheel:
                self.color_wheel.repaint()
            if self.color_harmony:
                self.color_harmony.update_harmony()


########################################################
# ColorWheel + ColorHarmony + ControlPanel
# in a togglable section
########################################################
class ColorWheel(QtWidgets.QWidget):
    """
    A hue–saturation wheel at full brightness.
    """

    def __init__(self, palette_widget: ColorPalette, parent: QtWidgets.QWidget = None) -> None:
        super().__init__(parent)
        logging.info('initializing ColorWheel widget')
        self.palette_widget = palette_widget
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)  # Add horizontal margins
        self.setLayout(layout)
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.setMinimumHeight(200)

        self.base_wheel_size = 1024
        self.wheel_image = self.generate_wheel_image(self.base_wheel_size)

        self.hovered_harmony = None  # Track which harmony is being hovered

        # -- Dragging state for color dots --
        self.dragging_index = -1
        self.dragging_radius = 12
        self.press_time = None  # Track when mouse was pressed
        self.click_threshold = 200  # milliseconds to consider it a click
        self.is_dragging = False  # Track if we're currently dragging

        # Enable mouse tracking for cursor changes
        self.setMouseTracking(True)
        self.hovered_index = -1  # Track which color is being hovered

    def set_hovered_harmony(self, harmony_name: str) -> None:
        """Set which harmony is currently being hovered over"""
        self.hovered_harmony = harmony_name
        self.update()  # Trigger a repaint

    def get_wheel_center_and_radius(self) -> tuple:
        """Get the center point and radius of the color wheel in widget coordinates."""
        w = self.width()
        h = self.height()
        diameter = min(w, h)
        radius = diameter / 2.0
        center_x = w / 2.0
        center_y = h / 2.0
        return (center_x, center_y), radius

    def get_point_on_wheel(self, hue_deg: float, sat: float = 1.0) -> QtCore.QPointF:
        """
        Convert a hue angle (in degrees) + saturation ∈ [0..1]
        to a point on the wheel.
        """
        w = self.width()
        h = self.height()
        diameter = min(w, h)
        radius = diameter / 2.0
        top_left_x = (w - diameter) / 2.0
        top_left_y = (h - diameter) / 2.0
        
        hue_rad = math.radians(hue_deg)
        x = top_left_x + radius + math.cos(hue_rad) * sat * radius
        y = top_left_y + radius - math.sin(hue_rad) * sat * radius
        return QtCore.QPointF(x, y)

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.button() == QtCore.Qt.LeftButton:
            idx = self.find_color_under_mouse(event.pos())
            if idx != -1:
                self.dragging_index = idx
                self.press_time = QtCore.QTime.currentTime()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        if self.dragging_index != -1:
            self.is_dragging = True
            hue, sat = self.pos_to_hue_sat(event.pos())
            self.update_color_hsv(self.dragging_index, hue, sat, update_circles=False)
            self.update()  # redraw the wheel & dots
        else:
            # Check if we're hovering over a color circle
            idx = self.find_color_under_mouse(event.pos())
            if idx != self.hovered_index:
                self.hovered_index = idx
                if idx != -1:
                    self.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
                else:
                    self.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.button() == QtCore.Qt.LeftButton and self.dragging_index != -1:
            # Check if this was a quick click (less than threshold)
            if self.press_time is not None:
                elapsed = self.press_time.msecsTo(QtCore.QTime.currentTime())
                if elapsed < self.click_threshold:
                    # It was a click, show color picker
                    self.show_color_picker(self.dragging_index)
                elif self.is_dragging:
                    # It was a drag, update the circles
                    self.palette_widget.update_colors()
            self.dragging_index = -1
            self.press_time = None
            self.is_dragging = False
        super().mouseReleaseEvent(event)

    def show_color_picker(self, index: int) -> None:
        """Show the color picker dialog for the color at the given index."""
        initial = QtGui.QColor(*self.palette_widget.colors[index].rgb)
        chosen = QtWidgets.QColorDialog.getColor(
            initial=initial,
            parent=self,
            title="Select a Color"
        )
        if chosen.isValid():
            new_color = Color((chosen.red(), chosen.green(), chosen.blue()), ColorType.RGB)
            self.palette_widget.colors[index] = new_color
            self.palette_widget.update_colors()
            self.update()  # redraw the wheel & dots

    def find_color_under_mouse(self, pos: QtCore.QPointF) -> int:
        """
        Returns the index of the color dot the user clicked on,
        or -1 if none.
        """
        x_click, y_click = pos.x(), pos.y()
        for i, color_obj in enumerate(self.palette_widget.colors):
            hue, sat, _ = color_obj.hsv
            dot_center = self.get_point_on_wheel(hue, sat / 255.0)
            dx = dot_center.x() - x_click
            dy = dot_center.y() - y_click
            if (dx*dx + dy*dy) <= (self.dragging_radius*self.dragging_radius):
                return i
        return -1

    def pos_to_hue_sat(self, pos: QtCore.QPointF) -> tuple[float, float]:
        """
        Convert mouse position to (hue, sat).
        Hue is [0..360), sat is [0..1].
        """
        (cx, cy), radius = self.get_wheel_center_and_radius()
        dx = pos.x() - cx
        dy = cy - pos.y()  # invert y for standard geometry
        dist = math.sqrt(dx*dx + dy*dy)
        sat = min(dist / radius, 1.0)
        hue = (math.degrees(math.atan2(dy, dx)) + 360.0) % 360.0
        return hue, sat

    def update_color_hsv(self, index: int, hue: float, saturation: float, update_circles: bool = True):
        """
        Update the color at 'index' in the palette to new hue/sat,
        while preserving the original value (brightness).
        If brightness is below 15%, set it to 15% to prevent arithmetic errors.
        """
        # Get the original HSV values
        current_hsv = self.palette_widget.colors[index].hsv
        # Enforce minimum brightness of 15% (38 in 0-255 range)
        min_brightness = 38  # 15% of 255
        value = max(current_hsv[2], min_brightness)
        # Create new HSV color with updated hue and saturation, and minimum brightness
        new_hsv = (int(round(hue)), int(round(saturation * 255)), value)
        new_color = Color(new_hsv, color_type=ColorType.HSV)
        self.palette_widget.colors[index] = new_color
        if update_circles:
            self.palette_widget.update_colors()

    def get_harmony_lines(self) -> list[tuple[QtCore.QPointF, QtCore.QPointF]]:
        """
        Calculate the lines to draw for the currently hovered harmony,
        so we can visualize it on the wheel.
        """
        if not self.hovered_harmony or not self.palette_widget.colors:
            return []

        center, _ = self.get_wheel_center_and_radius()
        center_point = QtCore.QPointF(center[0], center[1])
        lines = []

        # All hues from the palette
        hues = [color.hsv[0] for color in self.palette_widget.colors]

        # The original code for drawing harmony lines remains unchanged below:
        if self.hovered_harmony == "Monochromatic":
            _, mean_hue = score_monochromatic(hues)
            if mean_hue is not None:
                end_point = self.get_point_on_wheel(mean_hue)
                lines.append((center_point, end_point))

        elif self.hovered_harmony == "Complementary":
            _, (cluster1, cluster2, mean1, mean2) = score_complementary(hues)
            if mean1 is not None and mean2 is not None:
                w = self.width()
                h = self.height()
                diameter = min(w, h)
                radius = diameter / 2.0
                top_left_x = (w - diameter) / 2.0
                top_left_y = (h - diameter) / 2.0
                center_x = top_left_x + radius
                center_y = top_left_y + radius
                
                # Use mean1 directly as the angle to draw the line
                angle_rad = math.radians(mean1)
                dx = math.cos(angle_rad)
                dy = -math.sin(angle_rad)  # Negative because y increases downward in screen coordinates
                t = radius
                intersection1 = QtCore.QPointF(center_x - dx * t, center_y - dy * t)
                intersection2 = QtCore.QPointF(center_x + dx * t, center_y + dy * t)
                lines.append((intersection1, intersection2))

        elif self.hovered_harmony == "Split Complementary":
            # Get the clusters and their means from the split complementary score function
            _, (base_cluster, split1_cluster, split2_cluster, base_mean, split1_mean, split2_mean) = score_split_complementary(hues)
            if base_mean is not None:
                w = self.width()
                h = self.height()
                diameter = min(w, h)
                radius = diameter / 2.0
                top_left_x = (w - diameter) / 2.0
                top_left_y = (h - diameter) / 2.0
                center_x = top_left_x + radius
                center_y = top_left_y + radius
                center_point = QtCore.QPointF(center_x, center_y)
                
                # Draw three lines: one at base angle and two at 150 degrees from it
                for angle in [base_mean, (base_mean + 150) % 360, (base_mean + 210) % 360]:
                    angle_rad = math.radians(angle)
                    dx = math.cos(angle_rad)
                    dy = -math.sin(angle_rad)  # Negative because y increases downward in screen coordinates
                    t = radius
                    intersection = QtCore.QPointF(center_x + dx * t, center_y + dy * t)
                    lines.append((center_point, intersection))

        elif self.hovered_harmony == "Triadic":
            _, start_hue = score_triadic(hues)
            if start_hue is not None:
                w = self.width()
                h = self.height()
                diameter = min(w, h)
                radius = diameter / 2.0
                top_left_x = (w - diameter) / 2.0
                top_left_y = (h - diameter) / 2.0
                center_x = top_left_x + radius
                center_y = top_left_y + radius
                center_point = QtCore.QPointF(center_x, center_y)
                
                # Draw three lines at 120-degree angles from the center
                for angle in [start_hue, start_hue + 120, start_hue + 240]:
                    angle_rad = math.radians(angle)
                    dx = math.cos(angle_rad)
                    dy = -math.sin(angle_rad)  # Negative because y increases downward in screen coordinates
                    t = radius
                    intersection = QtCore.QPointF(center_x + dx * t, center_y + dy * t)
                    lines.append((center_point, intersection))

        elif self.hovered_harmony == "Square":
            _, start_hue = score_square(hues)
            if start_hue is not None:
                w = self.width()
                h = self.height()
                diameter = min(w, h)
                radius = diameter / 2.0
                top_left_x = (w - diameter) / 2.0
                top_left_y = (h - diameter) / 2.0
                center_x = top_left_x + radius
                center_y = top_left_y + radius
                center_point = QtCore.QPointF(center_x, center_y)
                
                # Draw four lines at 90-degree angles from the center
                for angle in [start_hue, start_hue + 90, start_hue + 180, start_hue + 270]:
                    angle_rad = math.radians(angle)
                    dx = math.cos(angle_rad)
                    dy = -math.sin(angle_rad)  # Negative because y increases downward in screen coordinates
                    t = radius
                    intersection = QtCore.QPointF(center_x + dx * t, center_y + dy * t)
                    lines.append((center_point, intersection))

        return lines

    def generate_wheel_image(self, diameter: int):
        logging.info('generating wheel image')
        image = QtGui.QImage(diameter, diameter, QtGui.QImage.Format_RGB32)
        image.fill(QtCore.Qt.black)
        radius = diameter / 2.0
        bg_color = self.palette().window().color()
        bg_pixel = bg_color.rgb()
        for y in range(diameter):
            for x in range(diameter):
                dx = x - radius
                dy = y - radius
                dist = math.sqrt(dx * dx + dy * dy)
                if dist <= radius:
                    hue_deg = (math.degrees(math.atan2(-dy, dx)) + 360) % 360
                    sat = dist / radius
                    c = QtGui.QColor.fromHsvF(hue_deg / 360.0, sat, 1.0)
                    image.setPixel(x, y, c.rgb())
                else:
                    image.setPixel(x, y, bg_pixel)
        return image

    def paintEvent(self, event) -> None:
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing, True)

        painter.fillRect(self.rect(), self.palette().window())
        w = self.width()
        h = self.height()
        diameter = min(w, h)
        scaled_wheel = self.wheel_image.scaled(
            diameter, diameter,
            QtCore.Qt.KeepAspectRatio,
            QtCore.Qt.SmoothTransformation
        )
        radius = diameter / 2.0
        top_left_x = (w - diameter) / 2.0
        top_left_y = (h - diameter) / 2.0
        painter.drawImage(int(top_left_x), int(top_left_y), scaled_wheel)

        # Draw harmony lines if a harmony is being hovered
        if self.hovered_harmony:
            harmony_lines = self.get_harmony_lines()
            pen = QtGui.QPen(QtCore.Qt.white, 2, QtCore.Qt.DashLine)
            painter.setPen(pen)
            for start, end in harmony_lines:
                painter.drawLine(start, end)

        # Draw color points (the circles)
        if hasattr(self.palette_widget, 'colors'):
            for color_obj in self.palette_widget.colors:
                hue, sat, val = color_obj.hsv
                sat_f = sat / 255.0
                px = top_left_x + radius + math.cos(math.radians(hue)) * sat_f * radius
                py = top_left_y + radius - math.sin(math.radians(hue)) * sat_f * radius
                dot_radius = 12
                pen = QtGui.QPen(QtCore.Qt.white, 2)
                painter.setPen(pen)
                painter.setBrush(QtGui.QColor(*color_obj.rgb))
                painter.drawEllipse(QtCore.QPointF(px, py), dot_radius, dot_radius)

        painter.end()

    def leaveEvent(self, event: QtGui.QEvent) -> None:
        """Reset cursor when mouse leaves the widget"""
        self.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
        self.hovered_index = -1
        super().leaveEvent(event)


class ColorHarmony(QtWidgets.QWidget):
    """
    Displays color harmony info as 7 read-only sliders side-by-side
    with the color wheel.
    """
    def __init__(self, palette_widget: ColorPalette, parent: QtWidgets.QWidget = None) -> None:
        super().__init__(parent)
        logging.info('initializing ColorHarmony widget')
        self.palette_widget = palette_widget

        # Set minimum width instead of fixed width
        self.setMinimumWidth(300)
        self.setFixedHeight(230)

        # Build a vertical layout with up to 7 lines:
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setSpacing(6)
        main_layout.setContentsMargins(4, 4, 4, 4)
        self.setLayout(main_layout)

        self.rows = []
        for _ in range(7):
            row_widget = QtWidgets.QWidget()
            row_layout = QtWidgets.QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(4)

            label = QtWidgets.QLabel("")
            label.setFixedWidth(160)
            label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
            label.setStyleSheet("color: white;")

            # Enable hover tracking
            label.setMouseTracking(True)
            label.enterEvent = lambda e, l=label: self.on_label_hover(l, True)
            label.leaveEvent = lambda e, l=label: self.on_label_hover(l, False)

            slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
            slider.setRange(0, 100)
            slider.setValue(0)
            slider.setEnabled(False)  # read-only slider
            slider.setFixedHeight(16)
            slider.setMinimumWidth(100)

            row_layout.addWidget(label)
            row_layout.addWidget(slider, 1)
            row_widget.setLayout(row_layout)

            self.rows.append((label, slider))
            main_layout.addWidget(row_widget)

    def on_label_hover(self, label: QtWidgets.QLabel, entering: bool) -> None:
        """Handle hover events on harmony labels."""
        if entering:
            harmony_name = label.text()
            if self.palette_widget.color_wheel:
                self.palette_widget.color_wheel.set_hovered_harmony(harmony_name)
        else:
            if self.palette_widget.color_wheel:
                self.palette_widget.color_wheel.set_hovered_harmony(None)

    def update_harmony(self) -> None:
        logging.info('updating color harmonies as sliders')
        color_harmony = analyze_palette_harmony(self.palette_widget.colors)
        items = list(color_harmony.items())

        for i in range(7):
            if i < len(items):
                cat, val = items[i]
                slider_percent = int(val * 100)  # if val is [0..1]
                self.rows[i][0].setText(cat)
                self.rows[i][1].setValue(slider_percent)
                
                # Gray out text for triadic and square when there aren't enough or too many colors
                if cat == "Triadic" and (len(self.palette_widget.colors) < 3 or len(self.palette_widget.colors) > 3):
                    self.rows[i][0].setStyleSheet("color: gray;")
                elif cat == "Square" and (len(self.palette_widget.colors) < 4 or len(self.palette_widget.colors) > 4):
                    self.rows[i][0].setStyleSheet("color: gray;")
                else:
                    self.rows[i][0].setStyleSheet("color: white;")
            else:
                self.rows[i][0].setText("")
                self.rows[i][1].setValue(0)


class ControlPanel(QtWidgets.QWidget):
    def __init__(self, palette_widget: ColorPalette, parent: QtWidgets.QWidget = None) -> None:
        super().__init__(parent)
        logging.info('initializing ControlPanel widget')
        self.palette_widget = palette_widget
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

    def open_preferences(self):
        dialog = PreferencesDialog(self)
        dialog.exec_()


class PreferencesDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Preferences")
        self.setModal(True)
        self.layout = QtWidgets.QVBoxLayout(self)

        # Load current preferences
        self.preferences = load_preferences()

        # Create a horizontal layout for classifier selection
        classifier_layout = QtWidgets.QHBoxLayout()
        
        self.classifier_label = QtWidgets.QLabel("Classifier:")
        self.classifier_combobox = QtWidgets.QComboBox()
        self.classifier_combobox.addItems([
            "GaussianMixture (Best, Slowest)",
            "K-Means (Good, Slow)",
            "Median Cut (Innacurate, Fast)"
        ])
        
        # Map the display names to the actual classifier names
        self.classifier_map = {
            "GaussianMixture (Best, Slowest)": "GaussianMixture",
            "K-Means (Good, Slow)": "KMeans",
            "Median Cut (Innacurate, Fast)": "MedianCut"
        }
        
        # Set the current classifier in the combobox
        current_classifier = self.preferences["classifier"]
        for display_name, actual_name in self.classifier_map.items():
            if actual_name == current_classifier:
                self.classifier_combobox.setCurrentText(display_name)
                break

        classifier_layout.addWidget(self.classifier_label)
        classifier_layout.addWidget(self.classifier_combobox)
        classifier_layout.addStretch()

        # Add tour reset option
        tour_layout = QtWidgets.QHBoxLayout()
        self.tour_reset_button = QtWidgets.QPushButton("Reset Welcome Tour")
        self.tour_reset_button.setToolTip("Show the welcome tour again on next launch")
        self.tour_reset_button.clicked.connect(self.reset_tour)
        tour_layout.addWidget(self.tour_reset_button)
        tour_layout.addStretch()

        self.save_button = QtWidgets.QPushButton("Save Preferences")
        self.save_button.clicked.connect(self.save_preferences)

        self.layout.addLayout(classifier_layout)
        self.layout.addLayout(tour_layout)
        self.layout.addWidget(self.save_button)

    def reset_tour(self):
        """Reset the tour preferences"""
        self.preferences["show_welcome_tour"] = True
        self.preferences["tour_completed"] = False
        store_preferences(self.preferences)
        QtWidgets.QMessageBox.information(
            self,
            "Tour Reset",
            "The welcome tour will be shown on the next launch."
        )

    def save_preferences(self):
        # Always use 4 colors
        new_preferences = {
            "num_colors": 4,
            "classifier": self.classifier_map[self.classifier_combobox.currentText()],
            "show_welcome_tour": self.preferences["show_welcome_tour"],
            "tour_completed": self.preferences["tour_completed"]
        }
        store_preferences(new_preferences)
        logging.info(f"Saved preferences: {new_preferences}")
        
        # Update the parent's preferences if it exists
        if hasattr(self.parent(), 'palette_widget'):
            self.parent().palette_widget.preferences = new_preferences
        
        self.accept()


########################################################
# MainWindow
########################################################
class MainWindow(QtWidgets.QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setGeometry(100, 100, 1200, 800)
        self.setWindowTitle("Themes")

        # Create the main widget and layout
        main_widget = QtWidgets.QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QtWidgets.QVBoxLayout(main_widget)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Create the view selector buttons
        self.create_view_selector(main_layout)

        # Create the stacked widget to hold different views
        self.stacked_widget = QtWidgets.QStackedWidget()
        main_layout.addWidget(self.stacked_widget)

        # Create and add the palette generator view
        self.palette_generator_view = self.create_palette_generator_view()
        self.stacked_widget.addWidget(self.palette_generator_view)

        # Create and add the library view
        self.library_view = LibraryView()
        self.stacked_widget.addWidget(self.library_view)

        # Connect the palette_saved signal to refresh the library view
        expandable_section = self.palette_generator_view.findChild(ExpandableSection)
        if expandable_section:
            expandable_section.palette_saved.connect(self.library_view.load_palettes)

        # Show welcome dialog if needed
        self.show_welcome_dialog()

    def create_view_selector(self, parent_layout: QtWidgets.QVBoxLayout) -> None:
        """Create the view selector buttons at the top of the window"""
        # Create a container widget for the buttons
        button_container = QtWidgets.QWidget()
        button_container.setFixedHeight(40)  # Fixed height for the button bar
        button_layout = QtWidgets.QHBoxLayout(button_container)
        button_layout.setSpacing(0)
        button_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create the buttons
        self.palette_generator_button = QtWidgets.QPushButton("Theme Extraction")
        self.library_button = QtWidgets.QPushButton("Library")
        
        # Style the buttons
        button_style = """
            QPushButton {
                border: none;
                padding: 8px 16px;
                background-color: #2d2d2d;
                color: white;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #3d3d3d;
            }
            QPushButton:pressed {
                background-color: #4d4d4d;
            }
            QPushButton:checked {
                background-color: #4d4d4d;
            }
        """
        
        # Apply the style
        self.palette_generator_button.setStyleSheet(button_style)
        self.library_button.setStyleSheet(button_style)
        
        # Make buttons checkable
        self.palette_generator_button.setCheckable(True)
        self.library_button.setCheckable(True)
        
        # Set initial state
        self.palette_generator_button.setChecked(True)
        
        # Connect signals
        self.palette_generator_button.clicked.connect(
            lambda: self.switch_view(self.palette_generator_view, self.palette_generator_button)
        )
        self.library_button.clicked.connect(
            lambda: self.switch_view(self.library_view, self.library_button)
        )
        
        # Add buttons to layout
        button_layout.addWidget(self.palette_generator_button)
        button_layout.addWidget(self.library_button)
        
        # Add the button container to the parent layout
        parent_layout.addWidget(button_container)

    def switch_view(self, view: QtWidgets.QWidget, button: QtWidgets.QPushButton) -> None:
        """Switch to the specified view and update button states"""
        self.stacked_widget.setCurrentWidget(view)
        # Uncheck all buttons
        self.palette_generator_button.setChecked(False)
        self.library_button.setChecked(False)
        # Check the selected button
        button.setChecked(True)

    def create_palette_generator_view(self) -> QtWidgets.QWidget:
        """Create and return the palette generator view (current UI)"""
        view = QtWidgets.QWidget()
        main_layout = QtWidgets.QHBoxLayout(view)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Left side container for image and palette
        left_container = QtWidgets.QWidget()
        left_layout = QtWidgets.QVBoxLayout(left_container)
        left_layout.setSpacing(0)
        left_layout.setContentsMargins(0, 0, 0, 0)

        self.image_drop = ImageDropWidget()
        left_layout.addWidget(self.image_drop, stretch=5)

        self.palette = ColorPalette()
        left_layout.addWidget(self.palette, stretch=0)

        main_layout.addWidget(left_container, stretch=1)

        # Create the expandable section
        self.color_wheel = ColorWheel(self.palette)
        self.color_harmony = ColorHarmony(self.palette)
        self.control_panel = ControlPanel(self.palette)

        self.palette.set_color_wheel(self.color_wheel)
        self.palette.set_color_harmony(self.color_harmony)
        self.palette.set_image_drop(self.image_drop)

        # Create a horizontal layout for the color wheel with spacers
        wheel_container = QtWidgets.QWidget()
        wheel_layout = QtWidgets.QHBoxLayout(wheel_container)
        wheel_layout.setContentsMargins(0, 0, 0, 0)
        wheel_layout.setSpacing(0)
        wheel_layout.addStretch(1)  # Left spacer
        wheel_layout.addWidget(self.color_wheel, 8)  # Color wheel takes 8 parts
        wheel_layout.addStretch(1)  # Right spacer

        expandable_section = ExpandableSection(
            wheel_container,
            self.color_harmony,
            self.control_panel
        )
        main_layout.addWidget(expandable_section, stretch=0)

        # Set up connections
        self.image_drop.image_selected.connect(self.palette.set_image_path)

        return view

    def show_welcome_dialog(self):
        """Show the welcome dialog if preferences indicate it should be shown"""
        preferences = load_preferences()
        if preferences.get("show_welcome_tour", True):
            from image_classifier.ui.welcome_dialog import WelcomeDialog
            dialog = WelcomeDialog(self)
            dialog.exec_()


class ExpandableSection(QtWidgets.QWidget):
    palette_saved = QtCore.Signal()  # Add this signal

    def __init__(self, color_wheel: ColorWheel, color_harmony: ColorHarmony, control_panel: ControlPanel, parent: QtWidgets.QWidget = None) -> None:
        super().__init__(parent)
        logging.info('initializing ExpandableSection widget')
        self.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Expanding)
        self.layout = QtWidgets.QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.layout)

        # Initialize palette storage
        self.palette_storage = PaletteStorage()

        # Content panel
        self.content_widget = QtWidgets.QWidget()
        content_layout = QtWidgets.QVBoxLayout(self.content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # Add top control panel (settings and refresh)
        top_control = QtWidgets.QWidget()
        top_control_layout = QtWidgets.QHBoxLayout(top_control)
        top_control_layout.setContentsMargins(0, 0, 0, 0)
        top_control_layout.setSpacing(0)

        btn_refresh = QtWidgets.QPushButton()
        btn_refresh.setIcon(MaterialIcon('autorenew'))
        btn_refresh.setFixedHeight(120)
        btn_refresh.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        btn_refresh.clicked.connect(control_panel.palette_widget.generate_colors)
        btn_refresh.setToolTip("Regenerate the Theme")

        btn_preferences = QtWidgets.QPushButton()
        btn_preferences.setIcon(MaterialIcon('settings'))
        btn_preferences.setFixedHeight(120)
        btn_preferences.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        btn_preferences.clicked.connect(control_panel.open_preferences)
        btn_preferences.setToolTip("Settings/Preferences")

        top_control_layout.addWidget(btn_refresh)
        top_control_layout.addWidget(btn_preferences)
        content_layout.addWidget(top_control, stretch=0)

        # Add palette name input and save button
        palette_control = QtWidgets.QWidget()
        palette_control_layout = QtWidgets.QHBoxLayout(palette_control)
        palette_control_layout.setContentsMargins(8, 8, 8, 8)
        palette_control_layout.setSpacing(8)

        # Palette name input
        self.palette_name_input = QtWidgets.QLineEdit()
        self.palette_name_input.setPlaceholderText("Enter theme name...")
        self.palette_name_input.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                background-color: #2d2d2d;
                color: white;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
            }
            QLineEdit:focus {
                border: 1px solid #4d4d4d;
            }
        """)
        palette_control_layout.addWidget(self.palette_name_input)

        # Save palette button
        self.save_palette_button = QtWidgets.QPushButton("Save Theme")
        self.save_palette_button.setToolTip("Save the theme to the Library")
        self.save_palette_button.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                background-color: #2d2d2d;
                color: white;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #3d3d3d;
            }
            QPushButton:pressed {
                background-color: #4d4d4d;
            }
        """)
        self.save_palette_button.clicked.connect(self.save_current_palette)
        palette_control_layout.addWidget(self.save_palette_button)

        content_layout.addWidget(palette_control, stretch=0)

        # Add spacer above color wheel
        content_layout.addSpacerItem(QtWidgets.QSpacerItem(0, 0, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding))

        # Add color wheel and harmony in the middle
        content_layout.addWidget(color_wheel, stretch=0)
        content_layout.addWidget(color_harmony, stretch=0)

        # Add bottom control panel (add and remove)
        bottom_control = QtWidgets.QWidget()
        bottom_control_layout = QtWidgets.QHBoxLayout(bottom_control)
        bottom_control_layout.setContentsMargins(0, 0, 0, 0)
        bottom_control_layout.setSpacing(0)

        btn_add = QtWidgets.QPushButton()
        btn_add.setIcon(MaterialIcon('add'))
        btn_add.setFixedHeight(120)
        btn_add.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        btn_add.clicked.connect(control_panel.palette_widget.add_color)
        btn_add.setToolTip("Add one color to the Theme")

        btn_remove = QtWidgets.QPushButton()
        btn_remove.setIcon(MaterialIcon('remove'))
        btn_remove.setFixedHeight(120)
        btn_remove.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        btn_remove.clicked.connect(control_panel.palette_widget.remove_color)
        btn_remove.setToolTip("Remove one color from the Theme")

        bottom_control_layout.addWidget(btn_add)
        bottom_control_layout.addWidget(btn_remove)
        content_layout.addWidget(bottom_control, stretch=0)

        self.content_widget.setLayout(content_layout)
        self.content_widget.setVisible(False)

        # Toggle button on the right edge
        self.toggle_button = QtWidgets.QPushButton()
        self.toggle_button.setIcon(MaterialIcon('chevron_left'))
        self.toggle_button.setCheckable(True)
        self.toggle_button.setChecked(False)
        self.toggle_button.setFixedWidth(30)
        self.toggle_button.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Expanding)
        self.toggle_button.clicked.connect(self.toggle_visibility)
        self.toggle_button.setToolTip("Show color controls")  # Initial tooltip

        self.layout.addWidget(self.content_widget)
        self.layout.addWidget(self.toggle_button)

        self.color_harmony = color_harmony
        self.palette_widget = control_panel.palette_widget

    def toggle_visibility(self) -> None:
        is_expanded = self.toggle_button.isChecked()
        logging.info('toggling visibility of expandable section.')
        self.content_widget.setVisible(is_expanded)
        self.toggle_button.setIcon(
            MaterialIcon('chevron_right') if is_expanded else MaterialIcon('chevron_left')
        )
        self.toggle_button.setToolTip("Hide color controls" if is_expanded else "Show color controls")
        if is_expanded:
            self.color_harmony.update_harmony()

    def save_current_palette(self) -> None:
        """Save the current palette to storage"""
        name = self.palette_name_input.text().strip()
        if not name:
            QtWidgets.QMessageBox.warning(
                self,
                "Missing Name",
                "Please enter a name for the palette."
            )
            return

        # Create a new palette with current colors
        palette = Palette(
            name=name,
            colors=self.palette_widget.colors,
            date_created=datetime.now().isoformat()
        )

        try:
            self.palette_storage.save_palette(palette)
            QtWidgets.QMessageBox.information(
                self,
                "Success",
                f"Palette '{name}' saved successfully!"
            )
            self.palette_saved.emit()  # Emit the signal after successful save
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self,
                "Error",
                f"Failed to save palette: {str(e)}"
            )


# If you also need to run this directly (outside a bigger project),
# you can include a simple "if __name__ == '__main__': ..." block:
if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    # Optional: apply a Qt theme if you like
    # qt_themes.apply_stylesheet(app, theme='dark_teal.xml')
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
