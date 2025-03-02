import math
import sys

import PySide2.QtCore as QtCore
import PySide2.QtGui as QtGui
import PySide2.QtWidgets as QtWidgets
from qt_material import apply_stylesheet

from image_classifier.color import Color, ColorType
from image_classifier.controller import analyze_palette_harmony
from image_classifier.ui.background_process import ColorGenerationThread


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

        self.set_alignment_and_margins()
        self.update_appearance()
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

    def set_alignment_and_margins(self):
        self.setAlignment(QtCore.Qt.AlignBottom | QtCore.Qt.AlignHCenter)
        self.setContentsMargins(0, 0, 0, 5)

    def update_appearance(self):
        # Prepare a QPalette instead of a style sheet
        palette = self.palette()
        # Convert the color to a QtGui.QColor
        qcolor = QtGui.QColor(*self.color.rgb)  # self.color.rgb is (r,g,b)

        # Set the background color to our color
        palette.setColor(QtGui.QPalette.Window, qcolor)
        # Set the text color to white
        palette.setColor(QtGui.QPalette.WindowText, QtCore.Qt.white)

        self.setPalette(palette)
        self.setBackgroundRole(QtGui.QPalette.Window)
        self.setForegroundRole(QtGui.QPalette.WindowText)

        # If we are not currently showing "Copied!", show the hex code text
        if not self.copied_timer.isActive():
            self.setText(self.color.hex.upper())

    def mousePressEvent(self, event):
        QtGui.QGuiApplication.clipboard().setText(self.color.hex.upper())
        self.setText("Copied!")
        self.copied_timer.start(1000)
        super().mousePressEvent(event)

    def reset_label(self):
        self.update_appearance()


class ColorPalette(QtWidgets.QWidget):
    """
    The horizontally displayed color palette.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QtWidgets.QHBoxLayout(self)
        self.layout.setSpacing(0)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.layout)
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

        # Current visible colors
        self.colors = []
        # All generated colors from background
        self.generated_colors = []
        self.image_path = None
        self.color_wheel = None

        # Progress label: stays in the layout permanently
        self.loading_label = QtWidgets.QLabel("Processing...")
        self.loading_label.setAlignment(QtCore.Qt.AlignCenter)
        self.loading_label.hide()
        # We add this widget at index 0 so it doesn't get removed by clear_colors
        self.layout.addWidget(self.loading_label)

        self.color_thread = None
        self.set_default_colors()

    def set_default_colors(self):
        """
        Sets default colors (4) when no image is loaded.
        """
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
        """
        Called by ImageDropWidget when an image is selected or dropped.
        """
        print(f"[DEBUG] set_image_path called with: {image_path}")
        self.image_path = image_path
        self.generate_colors()

    def set_color_wheel(self, color_wheel):
        """
        Keep a reference to the color wheel widget, so we can update it as needed.
        """
        self.color_wheel = color_wheel

    def generate_colors(self):
        """
        Spawns a background thread to generate a new palette if we have an image_path.
        """
        if not self.image_path:
            return
        print("[DEBUG] generate_colors called")
        # Show label & remove color boxes
        self.loading_label.show()
        self.clear_colors_except_label()

        # Start thread to generate new palette
        self.color_thread = ColorGenerationThread(self.image_path, num_colors=9)
        self.color_thread.colors_generated.connect(self.on_colors_generated)
        self.color_thread.start()

    def on_colors_generated(self, colors):
        """
        Called when the background thread finishes generating new colors.
        """
        if not colors:
            return
        self.generated_colors = colors
        # Only show as many colors as before, e.g., if we currently have 4 visible, keep showing 4
        self.colors = colors[:len(self.colors)]

        # Hide label & show boxes
        self.loading_label.hide()
        self.update_colors()

        # Let the color wheel know about the updated palette
        if self.color_wheel:
            self.color_wheel.update_color_harmony()
            self.color_wheel.update()
            self.color_wheel.repaint()

    def clear_colors_except_label(self):
        """
        Remove all color boxes, but leave self.loading_label in place.
        """
        for i in reversed(range(self.layout.count())):
            item = self.layout.itemAt(i)
            widget = item.widget()
            # if it's the label, skip
            if widget is self.loading_label:
                continue
            # else remove the color box
            self.layout.takeAt(i).widget().deleteLater()

    def update_colors(self):
        """
        Refresh the displayed colors in the layout.
        """
        self.clear_colors_except_label()
        # Always keep the loading label at index 0
        for c in self.colors:
            box = ColorBox(c)
            self.layout.addWidget(box)

    def add_color(self):
        """
        If we have more generated colors not displayed, add the next one to visible colors.
        """
        if len(self.colors) < len(self.generated_colors):
            self.colors.append(self.generated_colors[len(self.colors)])
            self.update_colors()
            if self.color_wheel:
                self.color_wheel.update_color_harmony()
                self.color_wheel.repaint()

    def remove_color(self):
        """
        Removes the last color from visible colors.
        """
        if self.colors:
            self.colors.pop()
            self.update_colors()
            if self.color_wheel:
                self.color_wheel.update_color_harmony()
                self.color_wheel.repaint()


class ColorWheel(QtWidgets.QWidget):
    """
    A hue–saturation wheel at full brightness, plus a hover info table.
    Each palette color is drawn as a white-outlined circle at its (hue, saturation) location.
    Also shows a color harmony table that updates automatically.
    """

    def __init__(self, palette_widget, parent=None):
        super().__init__(parent)
        self.palette_widget = palette_widget

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

        # Info table setup (shown on hover)
        self.info_table = QtWidgets.QTableWidget(self)
        self.info_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.info_table.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        self.info_table.setShowGrid(False)
        self.info_table.setFrameStyle(0)
        self.info_table.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.info_table.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.info_table.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, True)
        self.info_table.hide()

        font = QtGui.QFont()
        font.setPointSize(8)
        self.info_table.setFont(font)
        self.info_table.verticalHeader().setDefaultSectionSize(20)
        self.info_table.horizontalHeader().setDefaultSectionSize(60)
        self.info_table.horizontalHeader().setVisible(False)
        self.info_table.verticalHeader().setVisible(False)

        # Remove the style sheet usage; instead use a palette for background color
        self.set_table_translucent_background()

        self.info_table.setFixedSize(300, 200)
        self.info_table.setRowCount(8)
        self.info_table.setColumnCount(2)

        # We'll fill this table dynamically via update_color_harmony()
        for row in range(8):
            self.info_table.setItem(row, 0, QtWidgets.QTableWidgetItem(""))
            self.info_table.setItem(row, 1, QtWidgets.QTableWidgetItem(""))

        layout.addWidget(self.info_table, alignment=QtCore.Qt.AlignCenter)

        # Pre-generate a large wheel image for performance
        self.base_wheel_size = 1024
        self.wheel_image = self.generate_wheel_image(self.base_wheel_size)

    def set_table_translucent_background(self):
        """
        Use QPalette to give the table a semi-transparent background
        and white text, instead of using style sheets.
        """
        table_palette = self.info_table.palette()

        # A semi-transparent black
        translucent_black = QtGui.QColor(0, 0, 0, 140)
        table_palette.setColor(QtGui.QPalette.Base, translucent_black)
        table_palette.setColor(QtGui.QPalette.Text, QtCore.Qt.white)

        self.info_table.setPalette(table_palette)
        # Use the 'Base' color for the background, 'Text' color for text

    def generate_wheel_image(self, diameter):
        """
        Generates a single QImage of a full hue-saturation wheel of size 'diameter'.
        Saturation is radial (0 in the center, 1 on the edge),
        Hue is angular (0 to 360 degrees around).
        Value is always 1.
        """
        image = QtGui.QImage(diameter, diameter, QtGui.QImage.Format_RGB32)
        image.fill(QtCore.Qt.black)

        radius = diameter / 2.0
        bg_color = self.palette().window().color()
        bg_pixel = bg_color.rgb()  # color outside of wheel

        for y in range(diameter):
            for x in range(diameter):
                dx = x - radius
                dy = y - radius
                dist = math.sqrt(dx * dx + dy * dy)
                if dist <= radius:
                    # calculate hue (0-360) and saturation (0-1)
                    hue_deg = (math.degrees(math.atan2(-dy, dx)) + 360) % 360
                    sat = dist / radius
                    c = QtGui.QColor.fromHsvF(hue_deg / 360.0, sat, 1.0)
                    image.setPixel(x, y, c.rgb())
                else:
                    # Outside the circle, fill with background color
                    image.setPixel(x, y, bg_pixel)

        return image

    def paintEvent(self, event):
        """
        Draws the pre-generated hue-saturation wheel image (scaled),
        then draws each palette color as a white-outlined circle.
        """
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing, True)

        # Fill background with the widget's palette
        painter.fillRect(self.rect(), self.palette().window())

        # Determine the largest fitting diameter in this widget
        w = self.width()
        h = self.height()
        diameter = min(w, h)

        # Scale the wheel image to fit the current diameter
        scaled_wheel = self.wheel_image.scaled(
            diameter, diameter,
            QtCore.Qt.KeepAspectRatio,
            QtCore.Qt.SmoothTransformation
        )

        # Center the scaled wheel
        radius = diameter / 2.0
        top_left_x = (w - diameter) / 2.0
        top_left_y = (h - diameter) / 2.0
        painter.drawImage(int(top_left_x), int(top_left_y), scaled_wheel)

        # Draw the palette colors as circles
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

    def enterEvent(self, event):
        """
        Show the info table when mouse enters.
        """
        self.info_table.show()
        super().enterEvent(event)

    def leaveEvent(self, event):
        """
        Hide the info table when mouse leaves.
        """
        self.info_table.hide()
        super().leaveEvent(event)

    def resizeEvent(self, event):
        """
        Reposition the info table in the center when the widget is resized.
        """
        super().resizeEvent(event)
        tw = self.info_table.width()
        th = self.info_table.height()
        x = (self.width() - tw) // 2
        y = (self.height() - th) // 2
        self.info_table.move(x, y)

    def update_color_harmony(self):
        """
        Updates the color harmony table by analyzing the current palette colors.
        """
        color_harmony = analyze_palette_harmony(self.palette_widget.colors)
        row = 0
        for cat, val in color_harmony.items():
            if row < self.info_table.rowCount():
                percent = f"{val:.2f}"
                self.info_table.setItem(row, 0, QtWidgets.QTableWidgetItem(cat))
                self.info_table.setItem(row, 1, QtWidgets.QTableWidgetItem(percent))
            row += 1
        # If there are fewer categories than 8, the rest remain empty.


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
        self.setLayout(layout)


class ImageDropWidget(QtWidgets.QWidget):
    """
    A widget that supports drag-and-drop or file browsing to load an image.
    """
    image_selected = QtCore.Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))

        self.label = QtWidgets.QLabel("Drop Image Here\nor\nClick to Browse")
        self.label.setAlignment(QtCore.Qt.AlignCenter)

        # We leave the dashed border alone or remove it; if removing, do:
        # self.label.setFrameStyle(QtWidgets.QFrame.Box | QtWidgets.QFrame.Plain)
        # For a dashed border, you'd typically need a style sheet or custom painting.
        # If you truly want to remove the style sheet approach, you can skip the dashed look.

        self.layout.addWidget(self.label, stretch=1)

        self.browse_button = QtWidgets.QPushButton("Drop image here or Click to browse")
        self.browse_button.clicked.connect(self.browse_for_image)
        self.layout.addWidget(self.browse_button, stretch=0)
        self.setLayout(self.layout)

    def browse_for_image(self):
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Open Image", "",
            "Images (*.png *.jpg *.jpeg *.bmp)"
        )
        if file_path:
            self.load_image(file_path)

    def load_image(self, path):
        if not path:  # Ensure we have a valid path
            return

        pixmap = QtGui.QPixmap(path)
        if not pixmap.isNull():
            self.label.setPixmap(
                pixmap.scaled(self.label.size(), QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
            )

        self.image_selected.emit(path)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        """
        Handles file dropping from the OS.
        """
        urls = event.mimeData().urls()
        if urls:
            file_path = urls[0].toLocalFile()
            self.load_image(file_path)

    def mousePressEvent(self, event):
        """
        If the user clicks in this widget, trigger the file browser.
        """
        self.browse_for_image()

    def resizeEvent(self, event):
        """
        Rescale the previewed image when the widget is resized.
        """
        if self.label.pixmap() and not self.label.pixmap().isNull():
            self.label.setPixmap(self.label.pixmap().scaled(
                self.label.size(),
                QtCore.Qt.KeepAspectRatio,
                QtCore.Qt.SmoothTransformation
            ))
        super().resizeEvent(event)


class MainWindow(QtWidgets.QMainWindow):
    """
    The main window that sets up the layout: left side has the palette + control panel + color wheel;
    right side has the ImageDropWidget for loading images.
    """

    def __init__(self):
        super().__init__()
        self.setGeometry(100, 100, 1000, 600)

        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        main_layout = QtWidgets.QHBoxLayout(central)
        central.setLayout(main_layout)

        # Left side container
        left_widget = QtWidgets.QWidget()
        left_layout = QtWidgets.QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_widget.setLayout(left_layout)

        # Top widget: palette + control panel side by side
        top_widget = QtWidgets.QWidget()
        top_layout = QtWidgets.QHBoxLayout(top_widget)
        top_layout.setContentsMargins(0, 0, 0, 0)

        self.palette = ColorPalette()
        self.control_panel = ControlPanel(self.palette)

        top_layout.addWidget(self.palette, stretch=5)
        top_layout.addWidget(self.control_panel, stretch=0)
        top_widget.setLayout(top_layout)
        left_layout.addWidget(top_widget, stretch=1)

        # ColorWheel below
        self.color_wheel = ColorWheel(self.palette)
        self.palette.set_color_wheel(self.color_wheel)
        left_layout.addWidget(self.color_wheel, stretch=2)

        # ImageDropWidget on the right side
        self.image_drop = ImageDropWidget()
        self.image_drop.image_selected.connect(self.palette.set_image_path)
        main_layout.addWidget(left_widget, stretch=3)
        main_layout.addWidget(self.image_drop, stretch=2)


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    #apply_stylesheet(app, theme='dark_teal.xml')
    window.show()
    sys.exit(app.exec_())
