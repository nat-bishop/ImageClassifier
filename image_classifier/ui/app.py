from __future__ import annotations

import logging
import math
import sys

from image_classifier.preferences import load_preferences, store_preferences

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logging.getLogger().setLevel(logging.WARNING)

import PySide2.QtCore as QtCore
import PySide2.QtGui as QtGui
import PySide2.QtWidgets as QtWidgets
import qt_themes
from qt_material_icons import MaterialIcon

from image_classifier.color import Color, ColorType
from image_classifier.controller import analyze_palette_harmony
from image_classifier.ui.background_process import ColorGenerationThread

########################################################
# ImageDropWidget (Fills most of the window)
########################################################
class ImageDropWidget(QtWidgets.QLabel):
    image_selected = QtCore.Signal(str)

    def __init__(self, parent: QtWidgets.QWidget = None) -> None:
        super().__init__(parent)
        # Ignore the pixmap's default size; label can shrink below it
        self.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Ignored)

        self.setAcceptDrops(True)
        self.setAlignment(QtCore.Qt.AlignCenter)
        self.icon_pixmap = MaterialIcon("place_item").pixmap(QtCore.QSize(75, 75))

        self._original_pixmap = QtGui.QPixmap()
        self.show_border = True  # Initially show the border
        logging.info('initializing ImageDropWidget')

        # Show pointing-hand cursor on hover
        self.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))

        self.update_icon()

    def update_icon(self) -> None:
        if not self.icon_pixmap.isNull():
            self.setPixmap(self.icon_pixmap)
        else:
            logging.warning("Icon failed to load.")

    def load_image(self, path: str) -> None:
        pixmap = QtGui.QPixmap(path)
        if not pixmap.isNull():
            self._original_pixmap = pixmap
            self._update_displayed_pixmap()
            self.show_border = False  # Hide border when an image is loaded
            self.setStyleSheet("background-color: black;")

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

    def mousePressEvent(self, event) -> None:
        # Let user browse for image
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Open Image", "",
            "Images (*.png *.jpg *.jpeg *.bmp)"
        )
        if file_path:
            logging.info(f'selected image at filepath: {file_path}')
            self.load_image(file_path)

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

    def set_border_visibility(self, visible: bool) -> None:
        logging.debug(f'changing border visibility to: {visible}')
        self.show_border = visible
        self.update()


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
        palette_widget: ColorPalette,
        parent: QtWidgets.QWidget = None
    ) -> None:
        super().__init__(parent)
        self.color = color
        self.index = index
        self.palette_widget = palette_widget
        self.setAutoFillBackground(True)
        self.setAlignment(QtCore.Qt.AlignCenter)
        self.setContentsMargins(0, 0, 0, 0)
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

        # Show pointing-hand cursor on hover
        self.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))

        self.update_appearance()
        self.setToolTip("Click to pick a new color")

    def update_appearance(self) -> None:
        palette = self.palette()
        qcolor = QtGui.QColor(*self.color.rgb)
        palette.setColor(QtGui.QPalette.Window, qcolor)
        # White text by default if we decide to display text
        palette.setColor(QtGui.QPalette.WindowText, QtCore.Qt.white)

        self.setPalette(palette)
        self.setBackgroundRole(QtGui.QPalette.Window)
        self.setForegroundRole(QtGui.QPalette.WindowText)

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
        self.preferences = load_preferences()  # Load preferences
        self.current_num_colors = self.preferences.get("num_colors", 5)  # Track current number of colors

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
        self.clear_colors_except_label()
        logging.info('updating colors')
        for i, c in enumerate(self.colors):
            box = ColorBox(c, i, self, parent=self)
            self.layout.addWidget(box)

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
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.setMinimumHeight(200)

        self.base_wheel_size = 1024
        self.wheel_image = self.generate_wheel_image(self.base_wheel_size)

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

        if hasattr(self.palette_widget, 'colors'):
            for color_obj in self.palette_widget.colors:
                hue, sat, val = color_obj.hsv
                hue_rad = math.radians(hue)
                sat_f = sat / 255.0
                px = top_left_x + radius + math.cos(hue_rad) * sat_f * radius
                py = top_left_y + radius - math.sin(hue_rad) * sat_f * radius
                dot_radius = 12
                pen = QtGui.QPen(QtCore.Qt.white, 2)
                painter.setPen(pen)
                painter.setBrush(QtGui.QColor(*color_obj.rgb))
                painter.drawEllipse(QtCore.QPointF(px, py), dot_radius, dot_radius)
        painter.end()


class ColorHarmony(QtWidgets.QWidget):
    """
    Displays color harmony info as 8 read-only sliders side-by-side
    with the color wheel.
    """
    def __init__(self, palette_widget: ColorPalette, parent: QtWidgets.QWidget = None) -> None:
        super().__init__(parent)
        logging.info('initializing ColorHarmony widget')
        self.palette_widget = palette_widget

        # We'll fix width=200, height=230 as before
        self.setFixedSize(200, 230)

        # Build a vertical layout with up to 8 lines:
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setSpacing(6)
        main_layout.setContentsMargins(4, 4, 4, 4)
        self.setLayout(main_layout)

        self.rows = []
        for _ in range(8):
            row_widget = QtWidgets.QWidget()
            row_layout = QtWidgets.QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(4)

            # We fix the label's width so all sliders end up same length
            label = QtWidgets.QLabel("")
            label.setFixedWidth(90)  # Increased from 70 to 90 to prevent text cutoff
            label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

            slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
            slider.setRange(0, 100)
            slider.setValue(0)
            slider.setEnabled(False)  # read-only slider
            slider.setFixedHeight(16) # visually smaller
            # The slider automatically becomes the same length since the row has a fixed total width of 200,
            # minus the label's 90 px plus some margins.

            row_layout.addWidget(label)
            row_layout.addWidget(slider, 1)  # 'stretch=1' ensures the slider takes leftover space
            row_widget.setLayout(row_layout)

            self.rows.append((label, slider))
            main_layout.addWidget(row_widget)

    def update_harmony(self) -> None:
        logging.info('updating color harmonies as sliders')
        color_harmony = analyze_palette_harmony(self.palette_widget.colors)
        items = list(color_harmony.items())

        for i in range(8):
            if i < len(items):
                cat, val = items[i]
                slider_percent = int(val * 100)  # if val is [0..1]
                self.rows[i][0].setText(cat)
                self.rows[i][1].setValue(slider_percent)
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

        self.num_colors_label = QtWidgets.QLabel("Number of Colors:")
        self.num_colors_spinbox = QtWidgets.QSpinBox()
        self.num_colors_spinbox.setRange(1, 20)
        self.num_colors_spinbox.setValue(self.preferences["num_colors"])

        self.classifier_label = QtWidgets.QLabel("Classifier:")
        self.classifier_combobox = QtWidgets.QComboBox()
        self.classifier_combobox.addItems(["KMeans", "GaussianMixture", "MedianCut"])
        self.classifier_combobox.setCurrentText(self.preferences["classifier"])

        self.save_button = QtWidgets.QPushButton("Save Preferences")
        self.save_button.clicked.connect(self.save_preferences)

        self.layout.addWidget(self.num_colors_label)
        self.layout.addWidget(self.num_colors_spinbox)
        self.layout.addWidget(self.classifier_label)
        self.layout.addWidget(self.classifier_combobox)
        self.layout.addWidget(self.save_button)

    def save_preferences(self):
        new_preferences = {
            "num_colors": self.num_colors_spinbox.value(),
            "classifier": self.classifier_combobox.currentText(),
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
        self.setGeometry(100, 100, 1200, 800)  # Made window wider to accommodate right panel
        self.setWindowTitle("Palette Generator")

        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        main_layout = QtWidgets.QHBoxLayout(central)  # Changed to horizontal layout
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        central.setLayout(main_layout)

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

        expandable_section = ExpandableSection(
            self.color_wheel,
            self.color_harmony,
            self.control_panel
        )
        main_layout.addWidget(expandable_section, stretch=0)

        # Set up connections
        self.image_drop.image_selected.connect(self.palette.set_image_path)


class ExpandableSection(QtWidgets.QWidget):
    def __init__(self, color_wheel: ColorWheel, color_harmony: ColorHarmony, control_panel: ControlPanel, parent: QtWidgets.QWidget = None) -> None:
        super().__init__(parent)
        logging.info('initializing ExpandableSection widget')
        self.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Expanding)
        self.layout = QtWidgets.QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.layout)

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

        btn_preferences = QtWidgets.QPushButton()
        btn_preferences.setIcon(MaterialIcon('settings'))
        btn_preferences.setFixedHeight(120)
        btn_preferences.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        btn_preferences.clicked.connect(control_panel.open_preferences)

        top_control_layout.addWidget(btn_refresh)
        top_control_layout.addWidget(btn_preferences)
        content_layout.addWidget(top_control, stretch=0)

        # Add color wheel and harmony in the middle
        content_layout.addWidget(color_wheel, stretch=1)
        content_layout.addWidget(color_harmony, stretch=1)

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

        btn_remove = QtWidgets.QPushButton()
        btn_remove.setIcon(MaterialIcon('remove'))
        btn_remove.setFixedHeight(120)
        btn_remove.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        btn_remove.clicked.connect(control_panel.palette_widget.remove_color)

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

        self.layout.addWidget(self.content_widget)
        self.layout.addWidget(self.toggle_button)

        self.color_harmony = color_harmony

    def toggle_visibility(self) -> None:
        is_expanded = self.toggle_button.isChecked()
        logging.info('toggling visibility of expandable section.')
        self.content_widget.setVisible(is_expanded)
        self.toggle_button.setIcon(MaterialIcon('chevron_right') if is_expanded else MaterialIcon('chevron_left'))  # Fixed icon logic
        if is_expanded:
            self.color_harmony.update_harmony()
