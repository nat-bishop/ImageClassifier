import math
import sys

import PySide2.QtCore as QtCore
import PySide2.QtGui as QtGui
import PySide2.QtWidgets as QtWidgets
# from qt_material import apply_stylesheet

from image_classifier.color import Color, ColorType
from image_classifier.controller import analyze_palette_harmony
from image_classifier.ui.background_process import ColorGenerationThread


########################################################
# ImageDropWidget (Fills most of the window)
########################################################
class ImageDropWidget(QtWidgets.QLabel):
    image_selected = QtCore.Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        # Ignore the pixmap’s default size; label can shrink below it
        self.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Ignored)

        self.setAcceptDrops(True)
        self.setAlignment(QtCore.Qt.AlignCenter)
        self.setText("Drop Image Here or Click to Browse")
        self.setStyleSheet("border: 2px dashed gray;")

        self._original_pixmap = QtGui.QPixmap()

    def load_image(self, path):
        pixmap = QtGui.QPixmap(path)
        if not pixmap.isNull():
            self._original_pixmap = pixmap
            self._update_displayed_pixmap()
            # remove dashed border once loaded
            self.setStyleSheet("")
            self.setText("")
        self.image_selected.emit(path)

    def _update_displayed_pixmap(self):
        """Manually scale from the original pixmap to fit current label size."""
        if not self._original_pixmap.isNull():
            scaled = self._original_pixmap.scaled(
                self.size(),
                QtCore.Qt.KeepAspectRatio,
                QtCore.Qt.SmoothTransformation
            )
            self.setPixmap(scaled)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_displayed_pixmap()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls:
            file_path = urls[0].toLocalFile()
            self.load_image(file_path)

    def mousePressEvent(self, event):
        # Let user browse for image
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Open Image", "",
            "Images (*.png *.jpg *.jpeg *.bmp)"
        )
        if file_path:
            self.load_image(file_path)


########################################################
# ColorBox & ColorPalette (Bottom section)
########################################################
class ColorBox(QtWidgets.QLabel):
    """
    A color box that expands within the layout and displays the hex code
    at the bottom. Clicking copies the code to the clipboard.
    """

    def __init__(self, color: Color, parent=None):
        super().__init__(parent)
        self.color = color
        self.copied_timer = QtCore.QTimer(self)
        self.copied_timer.setSingleShot(True)
        self.copied_timer.timeout.connect(self.reset_label)

        # Enable background painting
        self.setAutoFillBackground(True)
        self.setAlignment(QtCore.Qt.AlignBottom | QtCore.Qt.AlignHCenter)
        self.setContentsMargins(0, 0, 0, 5)
        self.update_appearance()
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

    def update_appearance(self):
        # Use QPalette for background color
        palette = self.palette()
        qcolor = QtGui.QColor(*self.color.rgb)
        palette.setColor(QtGui.QPalette.Window, qcolor)
        # White text by default
        palette.setColor(QtGui.QPalette.WindowText, QtCore.Qt.white)

        self.setPalette(palette)
        self.setBackgroundRole(QtGui.QPalette.Window)
        self.setForegroundRole(QtGui.QPalette.WindowText)

        if not self.copied_timer.isActive():
            self.setText(self.color.hex.upper())

    def mousePressEvent(self, event):
        # Copy the hex to clipboard
        QtGui.QGuiApplication.clipboard().setText(self.color.hex.upper())
        self.setText("Copied!")
        self.copied_timer.start(1000)
        super().mousePressEvent(event)

    def reset_label(self):
        self.update_appearance()


class ColorPalette(QtWidgets.QWidget):
    """
    Horizontally displayed color palette beneath the image.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QtWidgets.QHBoxLayout(self)
        self.layout.setSpacing(0)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.layout)
        self.setMinimumHeight(120)
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)

        # Current visible colors
        self.colors = []
        # All generated colors from background
        self.generated_colors = []
        self.image_path = None

        # references to color wheel & color harmony
        self.color_wheel = None
        self.color_harmony = None

        # Progress label: stays in the layout permanently
        self.loading_label = QtWidgets.QLabel("Processing...")
        self.loading_label.setAlignment(QtCore.Qt.AlignCenter)
        self.loading_label.hide()
        self.layout.addWidget(self.loading_label)

        self.color_thread = None
        self.set_default_colors()

    def set_default_colors(self):
        default_colors = [
            Color((252, 231, 200), ColorType.RGB),
            Color((177, 194, 158), ColorType.RGB),
            Color((250, 218, 122), ColorType.RGB),
            Color((240, 160, 75), ColorType.RGB),
        ]
        self.colors = default_colors[:]
        self.generated_colors = default_colors[:]
        self.update_colors()

    def set_image_path(self, image_path: str):
        self.image_path = image_path
        self.generate_colors()

    def set_color_wheel(self, color_wheel):
        self.color_wheel = color_wheel

    def set_color_harmony(self, color_harmony):
        self.color_harmony = color_harmony

    def generate_colors(self):
        if not self.image_path:
            return
        self.loading_label.show()
        self.clear_colors_except_label()

        self.color_thread = ColorGenerationThread(self.image_path, num_colors=9)
        self.color_thread.colors_generated.connect(self.on_colors_generated)
        self.color_thread.start()

    def on_colors_generated(self, colors):
        if not colors:
            return
        self.generated_colors = colors
        # Only show as many colors as before
        self.colors = colors[:len(self.colors)]
        self.loading_label.hide()
        self.update_colors()

        # Update color wheel and color harmony
        if self.color_wheel:
            self.color_wheel.update()
            self.color_wheel.repaint()

        if self.color_harmony:
            self.color_harmony.update_harmony()

    def clear_colors_except_label(self):
        for i in reversed(range(self.layout.count())):
            item = self.layout.itemAt(i)
            widget = item.widget()
            if widget is self.loading_label:
                continue
            self.layout.takeAt(i).widget().deleteLater()

    def update_colors(self):
        self.clear_colors_except_label()
        for c in self.colors:
            box = ColorBox(c)
            self.layout.addWidget(box)

    def add_color(self):
        if len(self.colors) < len(self.generated_colors):
            self.colors.append(self.generated_colors[len(self.colors)])
            self.update_colors()
            if self.color_wheel:
                self.color_wheel.repaint()
            if self.color_harmony:
                self.color_harmony.update_harmony()

    def remove_color(self):
        if self.colors:
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

    def __init__(self, palette_widget, parent=None):
        super().__init__(parent)
        self.palette_widget = palette_widget
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.setMinimumHeight(300)

        self.base_wheel_size = 1024
        self.wheel_image = self.generate_wheel_image(self.base_wheel_size)

    def generate_wheel_image(self, diameter):
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

    def paintEvent(self, event):
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
                dot_radius = 18
                pen = QtGui.QPen(QtCore.Qt.white, 4)
                painter.setPen(pen)
                painter.setBrush(QtGui.QColor(*color_obj.rgb))
                painter.drawEllipse(QtCore.QPointF(px, py), dot_radius, dot_radius)
        painter.end()


class ColorHarmony(QtWidgets.QTableWidget):
    """
    Displays color harmony info side-by-side with the color wheel.
    """
    def __init__(self, palette_widget, parent=None):
        super().__init__(parent)
        self.palette_widget = palette_widget
        self.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        self.setShowGrid(False)
        self.setFrameStyle(0)
        self.setRowCount(8)
        self.setColumnCount(2)

        # Hide headers
        self.horizontalHeader().setVisible(False)
        self.verticalHeader().setVisible(False)

        self.verticalHeader().setDefaultSectionSize(1)

        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        self.setFixedSize(230, 300)

        # Initialize placeholders
        for r in range(8):
            self.setItem(r, 0, QtWidgets.QTableWidgetItem(""))
            self.setItem(r, 1, QtWidgets.QTableWidgetItem(""))

    def update_harmony(self):
        color_harmony = analyze_palette_harmony(self.palette_widget.colors)
        row = 0
        for cat, val in color_harmony.items():
            if row < self.rowCount():
                percent = f"{val:.2f}"
                self.setItem(row, 0, QtWidgets.QTableWidgetItem(cat))
                self.setItem(row, 1, QtWidgets.QTableWidgetItem(percent))
            row += 1
        # Clear remaining rows
        while row < self.rowCount():
            self.setItem(row, 0, QtWidgets.QTableWidgetItem(""))
            self.setItem(row, 1, QtWidgets.QTableWidgetItem(""))
            row += 1


class ControlPanel(QtWidgets.QWidget):
    """
    Simple control panel for generating colors or adding/removing them.
    """
    def __init__(self, palette_widget, parent=None):
        super().__init__(parent)
        self.palette_widget = palette_widget
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        btn_refresh = QtWidgets.QPushButton("@")
        btn_refresh.setFixedSize(40, 40)
        btn_refresh.clicked.connect(self.palette_widget.generate_colors)

        btn_add = QtWidgets.QPushButton("+")
        btn_add.setFixedSize(40, 40)
        btn_add.clicked.connect(self.palette_widget.add_color)

        btn_remove = QtWidgets.QPushButton("-")
        btn_remove.setFixedSize(40, 40)
        btn_remove.clicked.connect(self.palette_widget.remove_color)

        layout.addWidget(btn_refresh)
        layout.addWidget(btn_add)
        layout.addWidget(btn_remove)
        layout.addStretch()
        self.setLayout(layout)


class ExpandableSection(QtWidgets.QWidget):
    """
    A togglable section that shows color wheel, color harmony, and control panel side by side.
    """
    def __init__(self, color_wheel, color_harmony, control_panel, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.layout)

        self.toggle_button = QtWidgets.QPushButton("▼ More Info")
        self.toggle_button.setCheckable(True)
        self.toggle_button.setChecked(False)
        self.toggle_button.clicked.connect(self.toggle_visibility)
        self.layout.addWidget(self.toggle_button)

        self.content_widget = QtWidgets.QWidget()
        content_layout = QtWidgets.QHBoxLayout(self.content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)

        content_layout.addWidget(color_wheel, stretch=3)
        content_layout.addWidget(color_harmony, stretch=2)
        content_layout.addWidget(control_panel, stretch=1)

        self.content_widget.setLayout(content_layout)
        self.content_widget.setVisible(False)
        self.layout.addWidget(self.content_widget)

        self.color_harmony = color_harmony

    def toggle_visibility(self):
        is_expanded = self.toggle_button.isChecked()
        self.content_widget.setVisible(is_expanded)
        self.toggle_button.setText("▲ Less Info" if is_expanded else "▼ More Info")

        # If expanded, update the harmony table
        if is_expanded:
            self.color_harmony.update_harmony()


########################################################
# MainWindow
########################################################
class MainWindow(QtWidgets.QMainWindow):
    """
    Redesigned UI:
      1) Large image at the top
      2) Color palette at the bottom, slightly taller
      3) Expandable section to show color wheel, color harmony, control panel
    """

    def __init__(self):
        super().__init__()
        self.setGeometry(100, 100, 1000, 600)
        self.setWindowTitle("Palette Generator")

        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        main_layout = QtWidgets.QVBoxLayout(central)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        central.setLayout(main_layout)

        self.image_drop = ImageDropWidget()
        main_layout.addWidget(self.image_drop, stretch=5)

        self.palette = ColorPalette()
        main_layout.addWidget(self.palette, stretch=0)

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

        self.image_drop.image_selected.connect(self.palette.set_image_path)


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    # apply_stylesheet(app, theme='dark_teal.xml')  # optional
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
