import sys
from PySide6.QtWidgets import QApplication
from ui import SimEditorUI
from core.utils import setup_logging, disable_logging




def main():
    setup_logging() 
    # disable_logging()
    app = QApplication(sys.argv)
    editor_ui = SimEditorUI()    
    editor_ui.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()

