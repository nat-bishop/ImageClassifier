import sys
import random
import math

from PySide2.QtCore import (
    Qt, QTimer, QPointF
)
from PySide2.QtGui import (
    QPixmap, QDragEnterEvent, QDropEvent, QFont,
    QGuiApplication, QPainter, QImage, QColor, QPen
)
from PySide2.QtWidgets import (
    QApplication, QMainWindow, QWidget, QPushButton,
    QLabel, QHBoxLayout, QVBoxLayout, QTableWidget,
    QTableWidgetItem, QFileDialog,
    QAbstractItemView, QSizePolicy
)

from image_classifier.color.color import Color, ColorType


# helper to generate random color
def random_color() -> Color:
    r = random.randint(0, 255)
    g = random.randint(0, 255)
    b = random.randint(0, 255)
    return Color((r, g, b), ColorType.RGB)


# -------------------------------------------------------------------
# ColorBox
# -------------------------------------------------------------------
class ColorBox(QLabel):
    """
    A color box that expands within the layout and displays the hex code
    at the bottom. Clicking copies the code to the clipboard.
    """
    def __init__(self, color: Color, parent=None):
        super().__init__(parent)
        self.color = color
        self.copied_timer = QTimer(self)
        self.copied_timer.setSingleShot(True)
        self.copied_timer.timeout.connect(self.reset_label)

        self.setAutoFillBackground(False)
        self.set_alignment_and_margins()
        self.update_appearance()
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def set_alignment_and_margins(self):
        self.setAlignment(Qt.AlignBottom | Qt.AlignHCenter)
        self.setContentsMargins(0, 0, 0, 5)

    def update_appearance(self):
        hex_code = self.color.hex
        self.setStyleSheet(f"""
            QLabel {{
                background-color: {hex_code};
                color: white;
                border: none;
            }}
        """)
        if not self.copied_timer.isActive():
            self.setText(hex_code.upper())

    def mousePressEvent(self, event):
        QGuiApplication.clipboard().setText(self.color.hex.upper())
        self.setText("Copied!")
        self.copied_timer.start(1000)
        super().mousePressEvent(event)

    def reset_label(self):
        self.update_appearance()


# -------------------------------------------------------------------
# ColorPalette
# -------------------------------------------------------------------
class ColorPalette(QWidget):
    """
    A horizontal collection of ColorBoxes, with methods to
    add, remove, or randomize colors.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumWidth(200)

        self.layout = layout
        self.colors = [
            Color((252, 231, 200),  ColorType.RGB),
            Color((177, 194, 158),  ColorType.RGB),
            Color((250, 218, 122),  ColorType.RGB),
            Color((240, 160, 75), ColorType.RGB),
        ]

        self.color_wheel = None
        self.update_colors()

    def set_color_wheel(self, wheel):
        self.color_wheel = wheel

    def update_colors(self):
        while self.layout.count():
            item = self.layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for c in self.colors:
            box = ColorBox(c)
            self.layout.addWidget(box)

    def add_color(self):
        self.colors.append(random_color())
        self.update_colors()
        if self.color_wheel:
            self.color_wheel.update()

    def remove_color(self):
        if self.colors:
            self.colors.pop()
            self.update_colors()
            if self.color_wheel:
                self.color_wheel.update()

    def randomize_colors(self):
        for i in range(len(self.colors)):
            self.colors[i] = random_color()
        self.update_colors()
        if self.color_wheel:
            self.color_wheel.update()


# -------------------------------------------------------------------
# ColorWheel
# -------------------------------------------------------------------
class ColorWheel(QWidget):
    """
    A hue–saturation wheel at full brightness, plus a hover table that appears
    on mouse enter. Each palette color is shown as a white-outlined circle
    at its (hue, saturation) location.
    """
    def __init__(self, palette_widget, parent=None):
        super().__init__(parent)
        self.palette_widget = palette_widget

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.info_table = QTableWidget(self)
        self.info_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.info_table.setSelectionMode(QAbstractItemView.NoSelection)
        self.info_table.setShowGrid(False)
        self.info_table.setFrameStyle(0)
        self.info_table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.info_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.info_table.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.info_table.hide()

        font = QFont()
        font.setPointSize(8)
        self.info_table.setFont(font)
        self.info_table.verticalHeader().setDefaultSectionSize(20)
        self.info_table.horizontalHeader().setDefaultSectionSize(60)

        self.info_table.horizontalHeader().setVisible(False)
        self.info_table.verticalHeader().setVisible(False)

        self.info_table.setStyleSheet("""
            QTableWidget {
                background-color: rgba(0, 0, 0, 140);
                border: none;
                color: white;
                padding: 5px;
            }
            QTableWidget::item {
                margin: 0px;
                padding: 0px;
            }
        """)

        self.info_table.setFixedSize(300, 200)
        self.info_table.setRowCount(8)
        self.info_table.setColumnCount(2)

        data = [
            ("Triadic", "30%"),
            ("Square", "25%"),
            ("Analogous", "10%"),
            ("Complementary", "20%"),
            ("Split Compl.", "5%"),
            ("Monochromatic", "5%"),
            ("Contrast", "3%"),
            ("Saturation", "2%"),
        ]
        for row, (cat, val) in enumerate(data):
            self.info_table.setItem(row, 0, QTableWidgetItem(cat))
            self.info_table.setItem(row, 1, QTableWidgetItem(val))

        self.info_table.setColumnWidth(0, 200)
        self.info_table.setColumnWidth(1, 80)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        # Fill background to match the parent window color
        painter.fillRect(self.rect(), self.palette().window())

        w = self.width()
        h = self.height()
        diameter = min(w, h)
        radius = diameter / 2.0

        center_x = w / 2.0
        center_y = h / 2.0

        image = QImage(diameter, diameter, QImage.Format_RGB32)

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
                    c = QColor.fromHsvF(hue_deg / 360.0, sat, 1.0)
                    image.setPixel(x, y, c.rgb())
                else:
                    image.setPixel(x, y, bg_pixel)

        top_left_x = center_x - radius
        top_left_y = center_y - radius
        painter.drawImage(int(top_left_x), int(top_left_y), image)

        # Draw circles for each color
        if hasattr(self.palette_widget, 'colors'):
            for color_obj in self.palette_widget.colors:
                hue, sat, val = color_obj.hsv
                hue_rad = math.radians(hue)
                sat_f = sat / 255.0

                px = center_x + math.cos(hue_rad) * sat_f * radius
                py = center_y - math.sin(hue_rad) * sat_f * radius

                # White outline, actual color inside
                dot_radius = 18
                pen = QPen(Qt.white, 4)
                painter.setPen(pen)
                painter.setBrush(QColor(*color_obj.rgb))
                painter.drawEllipse(QPointF(px, py), dot_radius, dot_radius)

        painter.end()

    def enterEvent(self, event):
        self.info_table.show()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.info_table.hide()
        super().leaveEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        tw = self.info_table.width()
        th = self.info_table.height()
        x = (self.width() - tw) // 2
        y = (self.height() - th) // 2
        self.info_table.move(x, y)


# -------------------------------------------------------------------
# ControlPanel
# -------------------------------------------------------------------
class ControlPanel(QWidget):
    """
    Control panel with +, -, and '@' (randomize) buttons.
    """
    def __init__(self, palette_widget, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        btn_plus = QPushButton("+")
        btn_plus.setFixedSize(40, 40)
        btn_plus.clicked.connect(palette_widget.add_color)

        btn_minus = QPushButton("-")
        btn_minus.setFixedSize(40, 40)
        btn_minus.clicked.connect(palette_widget.remove_color)

        btn_rand = QPushButton("@")
        btn_rand.setFixedSize(40, 40)
        btn_rand.clicked.connect(palette_widget.randomize_colors)

        layout.addWidget(btn_plus)
        layout.addWidget(btn_minus)
        layout.addWidget(btn_rand)
        self.setLayout(layout)


# -------------------------------------------------------------------
# ImageDropWidget
# -------------------------------------------------------------------
class ImageDropWidget(QWidget):
    """
    Widget that supports drag-and-drop image loading, or clicking to browse.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.label = QLabel("Drop Image Here\nor\nClick to Browse")
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet("border: 2px dashed gray;")
        self.layout.addWidget(self.label, stretch=1)

        self.browse_button = QPushButton("Drop image here or Click to browse")
        self.browse_button.clicked.connect(self.browse_for_image)
        self.layout.addWidget(self.browse_button, stretch=0)
        self.setLayout(self.layout)

        self.browse_button.hide()

    def browse_for_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Image", "",
            "Images (*.png *.jpg *.jpeg *.bmp)"
        )
        if file_path:
            self.load_image(file_path)

    def load_image(self, path):
        pixmap = QPixmap(path)
        if not pixmap.isNull():
            self.label.setPixmap(
                pixmap.scaled(self.label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
            self.label.setStyleSheet("")
            self.label.setText("")
            self.browse_button.show()

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        if urls:
            file_path = urls[0].toLocalFile()
            self.load_image(file_path)

    def mousePressEvent(self, event):
        self.browse_for_image()

    def resizeEvent(self, event):
        if self.label.pixmap() and not self.label.pixmap().isNull():
            self.label.setPixmap(self.label.pixmap().scaled(
                self.label.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            ))
        super().resizeEvent(event)


# -------------------------------------------------------------------
# MainWindow
# -------------------------------------------------------------------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setGeometry(100, 100, 1000, 600)

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        central.setLayout(main_layout)

        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_widget.setLayout(left_layout)

        top_widget = QWidget()
        top_layout = QHBoxLayout(top_widget)
        top_layout.setContentsMargins(0, 0, 0, 0)

        self.palette = ColorPalette()
        self.control_panel = ControlPanel(self.palette)

        top_layout.addWidget(self.palette, stretch=5)
        top_layout.addWidget(self.control_panel, stretch=0)
        top_widget.setLayout(top_layout)
        left_layout.addWidget(top_widget, stretch=1)

        self.color_wheel = ColorWheel(self.palette)
        self.palette.set_color_wheel(self.color_wheel)

        left_layout.addWidget(self.color_wheel, stretch=2)

        self.image_drop = ImageDropWidget()
        main_layout.addWidget(left_widget, stretch=3)
        main_layout.addWidget(self.image_drop, stretch=2)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
