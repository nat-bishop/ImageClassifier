import sys
from image_classifier.ui.app import MainWindow
import PySide2.QtWidgets as QtWidgets
import qt_themes

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    qt_themes.set_theme('one_dark_two')
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
