import sys
import asyncio
import os
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
import qasync
from src.ui.main_window import MainWindow
from src.core.database import db

def main():
    # Initialize Database
    db.init_db()

    # Create Application
    # Set organization and app name BEFORE creating QApplication
    QApplication.setOrganizationName("QuickChat")
    QApplication.setApplicationName("QuickChat")

    app = QApplication(sys.argv)

    # Set application-wide icon (important for Linux taskbar)
    icon_path = os.path.join(os.path.dirname(__file__), "icon.png")
    if os.path.exists(icon_path):
        icon = QIcon(icon_path)
        app.setWindowIcon(icon)

        # For Linux: Also set as default icon for all windows
        QApplication.setWindowIcon(icon)

    # Set desktop file name for Linux window managers
    app.setDesktopFileName("quickchat")

    # Setup Async Loop
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)

    # Create Main Window
    window = MainWindow()

    # Set icon on window instance as well
    if os.path.exists(icon_path):
        window.setWindowIcon(QIcon(icon_path))

    window.show()

    # Run Event Loop
    with loop:
        loop.run_forever()

if __name__ == "__main__":
    main()
