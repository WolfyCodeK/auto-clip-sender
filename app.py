import sys
import os
import traceback
from PyQt5.QtWidgets import QApplication, QMessageBox

# Set up exception hook to show errors in message boxes
def excepthook(exc_type, exc_value, exc_tb):
    tb = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    print(f"ERROR: {tb}")
    QMessageBox.critical(None, "Unhandled Exception", 
                        f"An unhandled exception occurred:\n\n{tb}\n\nPlease report this error.")

sys.excepthook = excepthook

if __name__ == '__main__':
    try:
        # Make sure we're in the right directory to find clip_processor.py
        app_dir = os.path.dirname(os.path.abspath(__file__))
        os.chdir(app_dir)

        from gui import AutoClipSenderGUI
        app = QApplication(sys.argv)
        window = AutoClipSenderGUI()
        window.show()
        sys.exit(app.exec_())
    except Exception as e:
        trace = traceback.format_exc()
        print(f"Error starting application: {e}\n{trace}")
        if QApplication.instance():
            QMessageBox.critical(None, "Startup Error", 
                                f"Error starting application:\n\n{e}\n\n{trace}")
        sys.exit(1) 