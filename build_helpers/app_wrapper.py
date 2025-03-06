
import os
import sys

# Add the current directory to sys.path to ensure modules can be found
if getattr(sys, 'frozen', False):
    # Running as compiled executable
    application_path = os.path.dirname(sys.executable)
    os.environ['PATH'] = application_path + os.pathsep + os.environ.get('PATH', '')
    sys.path.insert(0, application_path)
    print(f"Running as executable from: {application_path}")
    print(f"Files in directory: {os.listdir(application_path)}")

try:
    import traceback
    from PyQt5.QtWidgets import QApplication, QMessageBox

    # Set up exception hook to show errors in message boxes
    def excepthook(exc_type, exc_value, exc_tb):
        tb = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        print(f"ERROR: {tb}")
        QMessageBox.critical(None, "Unhandled Exception", 
                            f"An unhandled exception occurred:\n\n{tb}\n\nPlease report this error.")

    sys.excepthook = excepthook

    # Make sure we're in the right directory
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
    if 'QApplication' in globals() and QApplication.instance():
        QMessageBox.critical(None, "Startup Error", 
                            f"Error starting application:\n\n{e}\n\n{trace}")
    else:
        # If PyQt5 failed to load, try to show a basic error dialog
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, 
                                         f"Error starting application: {e}\n{trace}", 
                                         "Startup Error", 0)
    sys.exit(1)
