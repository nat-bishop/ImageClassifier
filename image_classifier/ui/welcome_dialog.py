from PySide6 import QtWidgets, QtCore, QtGui
from image_classifier.preferences import load_preferences, store_preferences

class WelcomeDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Welcome to Themes!")
        self.setWindowFlags(QtCore.Qt.Window | QtCore.Qt.WindowTitleHint)
        self.setModal(True)
        
        # Load preferences
        self.preferences = load_preferences()
        
        # Create layout
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Title
        title = QtWidgets.QLabel("Welcome to Themes!")
        title.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(title)
        
        # Message
        message = QtWidgets.QLabel(
            "Would you like a quick tour of the app's features?\n"
            "The tour will guide you through the main functions of the application."
        )
        message.setAlignment(QtCore.Qt.AlignCenter)
        message.setWordWrap(True)
        layout.addWidget(message)
        
        # Never show again checkbox
        self.never_show_checkbox = QtWidgets.QCheckBox("Never show this again")
        layout.addWidget(self.never_show_checkbox)
        
        # Button container
        button_container = QtWidgets.QWidget()
        button_layout = QtWidgets.QHBoxLayout(button_container)
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(10)
        
        # Start Tour button
        self.start_button = QtWidgets.QPushButton("Start Tour")
        self.start_button.clicked.connect(self.start_tour)
        button_layout.addWidget(self.start_button)
        
        # Skip button
        self.skip_button = QtWidgets.QPushButton("Skip for Now")
        self.skip_button.clicked.connect(self.skip_tour)
        button_layout.addWidget(self.skip_button)
        
        layout.addWidget(button_container)
        
        # Set fixed size
        self.setFixedSize(400, 250)
        
        # Center the dialog on the parent window
        if parent:
            parent_rect = parent.geometry()
            self.move(
                parent_rect.center().x() - self.width() // 2,
                parent_rect.center().y() - self.height() // 2
            )
    
    def start_tour(self):
        """Start the tour and save preferences"""
        self.save_preferences()
        self.accept()  # Close the dialog
        # TODO: Start the actual tour
    
    def skip_tour(self):
        """Skip the tour and save preferences"""
        self.save_preferences()
        self.reject()  # Close the dialog
    
    def save_preferences(self):
        """Save the user's preferences"""
        self.preferences["show_welcome_tour"] = not self.never_show_checkbox.isChecked()
        store_preferences(self.preferences)
    
    def closeEvent(self, event):
        """Handle the close button (X)"""
        self.skip_tour()
        event.accept() 