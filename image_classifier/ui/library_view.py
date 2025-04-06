from PySide6 import QtCore, QtWidgets, QtGui
from image_classifier.storage import Palette, PaletteStorage
from image_classifier.color import Color
from qt_material_icons import MaterialIcon
import os

class PaletteListItem(QtWidgets.QWidget):
    """A widget that displays a single palette in the list"""
    
    def __init__(self, palette: Palette, parent: QtWidgets.QWidget = None):
        super().__init__(parent)
        self.palette = palette
        
        # Set fixed width for the entire palette
        self.setFixedWidth(250)
        
        # Main layout
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        # Color preview
        colors_widget = QtWidgets.QWidget()
        colors_widget.setFixedHeight(50)  # Set consistent height for color boxes
        colors_layout = QtWidgets.QHBoxLayout(colors_widget)
        colors_layout.setContentsMargins(0, 0, 0, 0)
        colors_layout.setSpacing(0)
        
        # Calculate box size based on number of colors
        num_colors = len(palette.colors)
        box_width = 250 // num_colors
        
        for color in palette.colors:
            color_box = QtWidgets.QLabel()
            color_box.setFixedSize(box_width, 50)  # Fixed height of 50, width scales
            # Convert RGB tuple to string for the stylesheet
            rgb_str = f"rgb({color.rgb[0]}, {color.rgb[1]}, {color.rgb[2]})"
            color_box.setStyleSheet(f"background-color: {rgb_str}; border: 1px solid #3d3d3d;")
            colors_layout.addWidget(color_box)
        
        # Name
        name_label = QtWidgets.QLabel(palette.name)
        name_label.setStyleSheet("color: white; font-weight: bold; background-color: transparent;")
        name_label.setAlignment(QtCore.Qt.AlignCenter)
        
        # Add widgets to main layout
        layout.addWidget(colors_widget)
        layout.addWidget(name_label)
        
        # Create delete button
        self.delete_button = QtWidgets.QPushButton()
        self.delete_button.setIcon(MaterialIcon('close'))
        self.delete_button.setFixedSize(24, 24)
        self.delete_button.setToolTip("Delete Theme")
        self.delete_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(45, 45, 45, 0.8);
                border: none;
                padding: 0;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: rgba(65, 65, 65, 0.9);
            }
            QPushButton::icon {
                color: white;
            }
            QToolTip {
                background-color: #2d2d2d;
                color: white;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 4px;
            }
        """)
        self.delete_button.hide()  # Initially hidden
        
        # Create export button
        self.export_button = QtWidgets.QPushButton()
        self.export_button.setIcon(MaterialIcon('save'))
        self.export_button.setFixedSize(24, 24)
        self.export_button.setToolTip("Export to JPEG")
        self.export_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(45, 45, 45, 0.8);
                border: none;
                padding: 0;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: rgba(65, 65, 65, 0.9);
            }
            QPushButton::icon {
                color: white;
            }
            QToolTip {
                background-color: #2d2d2d;
                color: white;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 4px;
            }
        """)
        self.export_button.hide()  # Initially hidden
        
        # Create containers for the buttons
        self.left_button_container = QtWidgets.QWidget(self)
        self.left_button_container.setFixedSize(24, 24)
        self.left_button_container.setStyleSheet("background-color: transparent;")
        
        self.right_button_container = QtWidgets.QWidget(self)
        self.right_button_container.setFixedSize(24, 24)
        self.right_button_container.setStyleSheet("background-color: transparent;")
        
        # Position the buttons in their containers
        left_layout = QtWidgets.QHBoxLayout(self.left_button_container)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(self.export_button)
        
        right_layout = QtWidgets.QHBoxLayout(self.right_button_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addWidget(self.delete_button)
        
        # Set background color for hover effect only on the main widget
        self.setStyleSheet("""
            QWidget {
                background-color: #2d2d2d;
                border-radius: 4px;
            }
            QWidget:hover {
                background-color: #3d3d3d;
            }
            QLabel {
                background-color: transparent;
            }
        """)
        
        # Enable mouse tracking for hover events
        self.setMouseTracking(True)
        
        # Connect buttons
        self.delete_button.clicked.connect(self.delete_palette)
        self.export_button.clicked.connect(self.export_palette)
    
    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        """Position the buttons in their respective corners"""
        super().resizeEvent(event)
        self.left_button_container.move(12, 12)  # Left side
        self.right_button_container.move(self.width() - 36, 12)  # Right side
    
    def enterEvent(self, event: QtCore.QEvent) -> None:
        """Show buttons on hover"""
        self.delete_button.show()
        self.export_button.show()
        super().enterEvent(event)
    
    def leaveEvent(self, event: QtCore.QEvent) -> None:
        """Hide buttons when mouse leaves"""
        self.delete_button.hide()
        self.export_button.hide()
        super().leaveEvent(event)
    
    def delete_palette(self) -> None:
        """Delete this palette from storage"""
        # Get the parent LibraryView
        parent = self.parent()
        while parent and not isinstance(parent, LibraryView):
            parent = parent.parent()
        
        if parent:
            # Delete the palette from storage
            parent.palette_storage.delete_palette(self.palette.name)
            # Reload the library view
            parent.load_palettes()
    
    def export_palette(self) -> None:
        """Export the palette as a JPEG image"""
        try:
            # Get the user's downloads folder
            downloads_path = os.path.expanduser("~/Downloads")
            
            # Create a filename from the palette name
            filename = f"{self.palette.name.replace(' ', '_')}_Theme.jpg"
            filepath = os.path.join(downloads_path, filename)
            
            # Image dimensions (scaled up for higher resolution)
            color_width = 400  # Increased from 200
            color_height = 400  # Increased from 200
            border_width = 8  # Increased from 4
            outer_border = 80  # Increased from 40
            text_height = 160  # Increased from 80
            copyright_height = 40  # Increased from 30
            
            # Calculate total image dimensions
            num_colors = len(self.palette.colors)
            total_width = (color_width * num_colors) + (border_width * (num_colors - 1)) + (outer_border * 2)
            total_height = color_height + text_height + outer_border * 2 + copyright_height
            
            # Create the image
            image = QtGui.QImage(total_width, total_height, QtGui.QImage.Format_RGB32)
            image.fill(QtCore.Qt.white)
            
            # Create a painter
            painter = QtGui.QPainter(image)
            painter.setRenderHint(QtGui.QPainter.Antialiasing)
            
            # Draw colors
            for i, color in enumerate(self.palette.colors):
                x = outer_border + (i * (color_width + border_width))
                y = outer_border
                
                # Draw color box
                painter.setPen(QtGui.QPen(QtCore.Qt.white, border_width))
                painter.setBrush(QtGui.QColor(*color.rgb))
                painter.drawRect(x, y, color_width, color_height)
                
                # Draw text below color
                painter.setPen(QtCore.Qt.black)
                font = painter.font()
                font.setPointSize(32)  # Increased from 16
                painter.setFont(font)
                
                # Convert RGB to hex
                hex_color = f"#{color.rgb[0]:02x}{color.rgb[1]:02x}{color.rgb[2]:02x}"
                rgb_text = f"RGB: {color.rgb[0]}, {color.rgb[1]}, {color.rgb[2]}"
                
                # Center text below color
                text_rect = QtCore.QRect(x, y + color_height + 20, color_width, text_height)
                painter.drawText(text_rect, QtCore.Qt.AlignHCenter | QtCore.Qt.AlignTop, hex_color)
                painter.drawText(text_rect, QtCore.Qt.AlignHCenter | QtCore.Qt.AlignBottom, rgb_text)
            
            # Draw copyright text
            font.setPointSize(12)  # Increased from 8 but still relatively small
            painter.setFont(font)
            # Calculate text width for left alignment
            copyright_text = "Themes by Nat Bishop"
            text_width = painter.fontMetrics().horizontalAdvance(copyright_text)
            text_height = painter.fontMetrics().height()
            # Position with 20px from left and 10px from bottom
            painter.drawText(20,  # 20px from left
                           total_height - text_height - 10,  # 10px from bottom
                           text_width, text_height,
                           QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter,
                           copyright_text)
            
            # End painting
            painter.end()
            
            # Save the image
            image.save(filepath, "JPEG", 100)
            
            # Show success message
            QtWidgets.QMessageBox.information(
                self,
                "Export Successful",
                f"Palette exported to:\n{filepath}"
            )
            
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self,
                "Export Failed",
                f"Failed to export palette: {str(e)}"
            )

class LibraryView(QtWidgets.QWidget):
    """The main library view that displays all saved palettes"""
    
    def __init__(self, parent: QtWidgets.QWidget = None):
        super().__init__(parent)
        self.palette_storage = PaletteStorage()
        
        # Main layout
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)
        
        # Scroll area for the list
        scroll_area = QtWidgets.QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #1d1d1d;
            }
            QScrollBar:vertical {
                border: none;
                background: #1d1d1d;
                width: 8px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #3d3d3d;
                min-height: 20px;
                border-radius: 4px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        
        # Container widget for the grid
        self.grid_container = QtWidgets.QWidget()
        self.grid_layout = QtWidgets.QGridLayout(self.grid_container)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.grid_layout.setSpacing(16)  # Space between items
        self.grid_layout.setVerticalSpacing(16)  # Space between rows
        self.grid_layout.setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignHCenter)  # Align content to the top and center horizontally
        
        scroll_area.setWidget(self.grid_container)
        layout.addWidget(scroll_area)
        
        # Load palettes
        self.load_palettes()
    
    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        """Handle window resize events to update the grid layout"""
        super().resizeEvent(event)
        self.load_palettes()  # Reload palettes to update the grid layout
    
    def load_palettes(self) -> None:
        """Load and display all saved palettes in a grid"""
        # Clear existing items
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Add palettes to the grid
        palettes = self.palette_storage.load_all_palettes()
        
        # Calculate number of columns based on available width
        # Each palette is 250px wide
        available_width = self.width() - 32  # Account for margins
        num_columns = max(1, available_width // 250)
        
        # Calculate equal spacing between palettes
        if num_columns > 1:
            total_palette_width = num_columns * 250
            remaining_space = available_width - total_palette_width
            spacing = remaining_space // (num_columns - 1)
            self.grid_layout.setHorizontalSpacing(spacing)
        else:
            self.grid_layout.setHorizontalSpacing(16)  # Default spacing for single column
        
        # Add palettes to the grid
        for i, palette in enumerate(palettes):
            row = i // num_columns
            col = i % num_columns
            item = PaletteListItem(palette)
            self.grid_layout.addWidget(item, row, col)
        
        # Add stretch to the last row only if there are palettes
        if palettes:
            self.grid_layout.setRowStretch(self.grid_layout.rowCount(), 1) 