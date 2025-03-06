import sys
import os
import io
import traceback
import logging
import importlib
from datetime import datetime

# Add code to ensure we can find config.py when running as an executable
if getattr(sys, 'frozen', False):
    # Running as compiled executable
    application_path = os.path.dirname(sys.executable)
    os.environ['PATH'] = application_path + os.pathsep + os.environ.get('PATH', '')
    sys.path.insert(0, application_path)
    print(f"Running as executable from: {application_path}")
    print(f"Files in directory: {os.listdir(application_path)}")

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QLineEdit, QPushButton, QTabWidget, QSpinBox, QDoubleSpinBox,
                             QComboBox, QGroupBox, QTextEdit, QFileDialog, QFormLayout, QMessageBox,
                             QScrollArea, QFrame, QSplitter, QSizePolicy)
from PyQt5.QtCore import Qt, QProcess, pyqtSignal, QObject, QTimer
from PyQt5.QtGui import QFont, QPalette, QColor, QTextCursor

# Import our configuration to use as defaults
try:
    # Try to import user config first
    import config
    from dotenv import load_dotenv
    load_dotenv()  # Load environment variables from .env file
    
    # Check if we need to create defaults file
    try:
        import defaults
    except ImportError:
        # Create the defaults file if it doesn't exist
        with open('defaults.py', 'w') as f:
            f.write('"""\nDefault configuration settings for the auto-clip-sender application.\n')
            f.write('Do not modify this file directly. Changes to settings should be made in config.py.\n"""\n\n')
            
            # Folder configuration
            f.write("# Folder configuration \n")
            f.write(f'SHADOWPLAY_FOLDER = "{config.SHADOWPLAY_FOLDER}"\n')
            f.write(f'OUTPUT_FOLDER = "{config.OUTPUT_FOLDER}"\n\n')
            
            # Size limits
            f.write("# Size limits (MB)\n")
            f.write(f'MIN_SIZE_MB = {config.MIN_SIZE_MB}      # Minimum target size (we want files to be at least this large)\n')
            f.write(f'MAX_SIZE_MB = {config.MAX_SIZE_MB}     # Maximum size allowed by Discord\n')
            f.write(f'TARGET_SIZE_MB = {config.TARGET_SIZE_MB}   # Target size in the middle of our range\n')
            f.write(f'MAX_COMPRESSION_ATTEMPTS = {config.MAX_COMPRESSION_ATTEMPTS}  # Maximum number of compression iterations\n\n')
            
            # Compression settings
            f.write("# Compression settings\n")
            f.write(f'CRF_MIN = {config.CRF_MIN}          # Minimum CRF value (highest quality)\n')
            f.write(f'CRF_MAX = {config.CRF_MAX}         # Maximum CRF value (lowest quality)\n')
            f.write(f'CRF_STEP = {config.CRF_STEP}         # Step size for CRF adjustments\n\n')
            
            # FFmpeg presets
            f.write("# FFmpeg presets\n")
            f.write("# Options: ultrafast, superfast, veryfast, faster, fast, medium, slow, slower, veryslow\n")
            f.write(f'EXTRACT_PRESET = "{config.EXTRACT_PRESET}"\n')
            f.write(f'COMPRESSION_PRESET = "{config.COMPRESSION_PRESET}"\n\n')
            
            # File processing settings
            f.write("# File processing settings\n")
            f.write(f'CLIP_DURATION = {config.CLIP_DURATION}       # Duration in seconds to extract from the end of videos\n')
            f.write(f'HIGH_QUALITY_CRF = {config.HIGH_QUALITY_CRF}    # CRF value for initial high-quality extraction\n\n')
            
            # Thresholds for adjustment
            f.write("# Thresholds for adjustment size logic\n")
            f.write(f'CLOSE_THRESHOLD = {config.CLOSE_THRESHOLD}    # {int(config.CLOSE_THRESHOLD*100)}% of target\n')
            f.write(f'MEDIUM_THRESHOLD = {config.MEDIUM_THRESHOLD}  # {int(config.MEDIUM_THRESHOLD*100)}% of target\n')
            f.write(f'FAR_THRESHOLD = {config.FAR_THRESHOLD}      # {int(config.FAR_THRESHOLD*100)}% of target \n')
        
        # Now import the defaults
        import defaults

except ImportError:
    # If config.py doesn't exist yet, try to use defaults
    try:
        import defaults
        print("GUI: No config.py found, using defaults.py instead")
        # Import the module into the config namespace
        import sys
        sys.modules['config'] = defaults
        config = defaults
    except ImportError:
        print("GUI: No config.py or defaults.py found, creating basic defaults")
        # If no defaults file, create basic default values
        class ConfigDefaults:
            pass
        config = ConfigDefaults()
        config.SHADOWPLAY_FOLDER = "C:/Users/YourName/Videos/Shadowplay Recordings"
        config.OUTPUT_FOLDER = "C:/Users/YourName/Videos/Shadowplay Recordings/auto-clips"
        config.MIN_SIZE_MB = 8
        config.MAX_SIZE_MB = 10
        config.TARGET_SIZE_MB = 9
        config.MAX_COMPRESSION_ATTEMPTS = 5
        config.CRF_MIN = 1
        config.CRF_MAX = 30
        config.CRF_STEP = 1
        config.EXTRACT_PRESET = "fast"
        config.COMPRESSION_PRESET = "medium"
        config.CLIP_DURATION = 15
        config.HIGH_QUALITY_CRF = 18
        config.CLOSE_THRESHOLD = 0.9
        config.MEDIUM_THRESHOLD = 0.75
        config.FAR_THRESHOLD = 0.5
        
        # Create the defaults file
        with open('defaults.py', 'w') as f:
            f.write('"""\nDefault configuration settings for the auto-clip-sender application.\n')
            f.write('Do not modify this file directly. Changes to settings should be made in config.py.\n"""\n\n')
            
            # Folder configuration
            f.write("# Folder configuration \n")
            f.write(f'SHADOWPLAY_FOLDER = "{config.SHADOWPLAY_FOLDER}"\n')
            f.write(f'OUTPUT_FOLDER = "{config.OUTPUT_FOLDER}"\n\n')
            
            # Size limits
            f.write("# Size limits (MB)\n")
            f.write(f'MIN_SIZE_MB = {config.MIN_SIZE_MB}      # Minimum target size (we want files to be at least this large)\n')
            f.write(f'MAX_SIZE_MB = {config.MAX_SIZE_MB}     # Maximum size allowed by Discord\n')
            f.write(f'TARGET_SIZE_MB = {config.TARGET_SIZE_MB}   # Target size in the middle of our range\n')
            f.write(f'MAX_COMPRESSION_ATTEMPTS = {config.MAX_COMPRESSION_ATTEMPTS}  # Maximum number of compression iterations\n\n')
            
            # Compression settings
            f.write("# Compression settings\n")
            f.write(f'CRF_MIN = {config.CRF_MIN}          # Minimum CRF value (highest quality)\n')
            f.write(f'CRF_MAX = {config.CRF_MAX}         # Maximum CRF value (lowest quality)\n')
            f.write(f'CRF_STEP = {config.CRF_STEP}         # Step size for CRF adjustments\n\n')
            
            # FFmpeg presets
            f.write("# FFmpeg presets\n")
            f.write("# Options: ultrafast, superfast, veryfast, faster, fast, medium, slow, slower, veryslow\n")
            f.write(f'EXTRACT_PRESET = "{config.EXTRACT_PRESET}"\n')
            f.write(f'COMPRESSION_PRESET = "{config.COMPRESSION_PRESET}"\n\n')
            
            # File processing settings
            f.write("# File processing settings\n")
            f.write(f'CLIP_DURATION = {config.CLIP_DURATION}       # Duration in seconds to extract from the end of videos\n')
            f.write(f'HIGH_QUALITY_CRF = {config.HIGH_QUALITY_CRF}    # CRF value for initial high-quality extraction\n\n')
            
            # Thresholds for adjustment
            f.write("# Thresholds for adjustment size logic\n")
            f.write(f'CLOSE_THRESHOLD = {config.CLOSE_THRESHOLD}    # {int(config.CLOSE_THRESHOLD*100)}% of target\n')
            f.write(f'MEDIUM_THRESHOLD = {config.MEDIUM_THRESHOLD}  # {int(config.MEDIUM_THRESHOLD*100)}% of target\n')
            f.write(f'FAR_THRESHOLD = {config.FAR_THRESHOLD}      # {int(config.FAR_THRESHOLD*100)}% of target \n')

        # Create a minimal config.py to ensure bot.py will work
        with open('config.py', 'w') as f:
            f.write('"""\nConfiguration settings for the auto-clip-sender application.\n')
            f.write('This file can be committed to version control.\n"""\n\n')
            
            # Folder configuration
            f.write("# Folder configuration \n")
            f.write(f'SHADOWPLAY_FOLDER = "{config.SHADOWPLAY_FOLDER}"\n')
            f.write(f'OUTPUT_FOLDER = "{config.OUTPUT_FOLDER}"\n\n')
            
            # Size limits
            f.write("# Size limits (MB)\n")
            f.write(f'MIN_SIZE_MB = {config.MIN_SIZE_MB}      # Minimum target size (we want files to be at least this large)\n')
            f.write(f'MAX_SIZE_MB = {config.MAX_SIZE_MB}     # Maximum size allowed by Discord\n')
            f.write(f'TARGET_SIZE_MB = {config.TARGET_SIZE_MB}   # Target size in the middle of our range\n')
            f.write(f'MAX_COMPRESSION_ATTEMPTS = {config.MAX_COMPRESSION_ATTEMPTS}  # Maximum number of compression iterations\n\n')
            
            # Compression settings
            f.write("# Compression settings\n")
            f.write(f'CRF_MIN = {config.CRF_MIN}          # Minimum CRF value (highest quality)\n')
            f.write(f'CRF_MAX = {config.CRF_MAX}         # Maximum CRF value (lowest quality)\n')
            f.write(f'CRF_STEP = {config.CRF_STEP}         # Step size for CRF adjustments\n\n')
            
            # FFmpeg presets
            f.write("# FFmpeg presets\n")
            f.write("# Options: ultrafast, superfast, veryfast, faster, fast, medium, slow, slower, veryslow\n")
            f.write(f'EXTRACT_PRESET = "{config.EXTRACT_PRESET}"\n')
            f.write(f'COMPRESSION_PRESET = "{config.COMPRESSION_PRESET}"\n\n')
            
            # File processing settings
            f.write("# File processing settings\n")
            f.write(f'CLIP_DURATION = {config.CLIP_DURATION}       # Duration in seconds to extract from the end of videos\n')
            f.write(f'HIGH_QUALITY_CRF = {config.HIGH_QUALITY_CRF}    # CRF value for initial high-quality extraction\n\n')
            
            # Thresholds for adjustment
            f.write("# Thresholds for adjustment size logic\n")
            f.write(f'CLOSE_THRESHOLD = {config.CLOSE_THRESHOLD}    # {int(config.CLOSE_THRESHOLD*100)}% of target\n')
            f.write(f'MEDIUM_THRESHOLD = {config.MEDIUM_THRESHOLD}  # {int(config.MEDIUM_THRESHOLD*100)}% of target\n')
            f.write(f'FAR_THRESHOLD = {config.FAR_THRESHOLD}      # {int(config.FAR_THRESHOLD*100)}% of target \n')

# Try to load from defaults if it exists, otherwise use the hard-coded values
try:
    import defaults
    # Store default values for reset functionality
    # Update to use defaults.py instead of config.py for default values
    DEFAULT_VALUES = {
        'SHADOWPLAY_FOLDER': defaults.SHADOWPLAY_FOLDER,
        'OUTPUT_FOLDER': defaults.OUTPUT_FOLDER,
        'MIN_SIZE_MB': defaults.MIN_SIZE_MB,
        'MAX_SIZE_MB': defaults.MAX_SIZE_MB,
        'TARGET_SIZE_MB': defaults.TARGET_SIZE_MB,
        'MAX_COMPRESSION_ATTEMPTS': defaults.MAX_COMPRESSION_ATTEMPTS,
        'CRF_MIN': defaults.CRF_MIN,
        'CRF_MAX': defaults.CRF_MAX,
        'CRF_STEP': defaults.CRF_STEP,
        'EXTRACT_PRESET': defaults.EXTRACT_PRESET,
        'COMPRESSION_PRESET': defaults.COMPRESSION_PRESET,
        'CLIP_DURATION': defaults.CLIP_DURATION,
        'HIGH_QUALITY_CRF': defaults.HIGH_QUALITY_CRF,
        'CLOSE_THRESHOLD': defaults.CLOSE_THRESHOLD,
        'MEDIUM_THRESHOLD': defaults.MEDIUM_THRESHOLD,
        'FAR_THRESHOLD': defaults.FAR_THRESHOLD,
        # Discord webhook URL (stored in .env, not config.py)
        'WEBHOOK_URL': os.getenv("WEBHOOK_URL", ""),
    }

except ImportError:
    # Store default values for reset functionality using config as fallback
    DEFAULT_VALUES = {
        'SHADOWPLAY_FOLDER': config.SHADOWPLAY_FOLDER,
        'OUTPUT_FOLDER': config.OUTPUT_FOLDER,
        'MIN_SIZE_MB': config.MIN_SIZE_MB,
        'MAX_SIZE_MB': config.MAX_SIZE_MB,
        'TARGET_SIZE_MB': config.TARGET_SIZE_MB,
        'MAX_COMPRESSION_ATTEMPTS': config.MAX_COMPRESSION_ATTEMPTS,
        'CRF_MIN': config.CRF_MIN,
        'CRF_MAX': config.CRF_MAX,
        'CRF_STEP': config.CRF_STEP,
        'EXTRACT_PRESET': config.EXTRACT_PRESET,
        'COMPRESSION_PRESET': config.COMPRESSION_PRESET,
        'CLIP_DURATION': config.CLIP_DURATION,
        'HIGH_QUALITY_CRF': config.HIGH_QUALITY_CRF,
        'CLOSE_THRESHOLD': config.CLOSE_THRESHOLD,
        'MEDIUM_THRESHOLD': config.MEDIUM_THRESHOLD,
        'FAR_THRESHOLD': config.FAR_THRESHOLD,
        # Discord webhook URL (stored in .env, not config.py)
        'WEBHOOK_URL': os.getenv("WEBHOOK_URL", ""),
    }

# Custom SpinBox classes that ignore wheel events
class NoWheelSpinBox(QSpinBox):
    def wheelEvent(self, event):
        event.ignore()

class NoWheelDoubleSpinBox(QDoubleSpinBox):
    def wheelEvent(self, event):
        event.ignore()

# Custom ComboBox that ignores wheel events
class NoWheelComboBox(QComboBox):
    def wheelEvent(self, event):
        event.ignore()

# Stream to redirect stdout/stderr to our QTextEdit
class QTextEditLogger(QObject):
    log_signal = pyqtSignal(str)

    def __init__(self, text_edit):
        super().__init__()
        self.text_edit = text_edit
        self.log_signal.connect(self.write_to_text_edit)
        self.buffer = ""
        
    def write(self, text):
        if text:  # Avoid empty strings
            # Add timestamp prefix to each line (only for complete lines)
            timestamp = datetime.now().strftime('[%H:%M:%S] ')
            
            # Append to buffer and process line by line
            self.buffer += text
            
            # Process complete lines
            if '\n' in self.buffer:
                lines = self.buffer.split('\n')
                # Keep the last incomplete line in the buffer
                self.buffer = lines[-1]
                
                # Process complete lines (all except the last one)
                for line in lines[:-1]:
                    if line.strip():  # Skip empty lines
                        self.log_signal.emit(f"{timestamp}{line}\n")
            
            # If we have a complete message with no newline, emit it with timestamp
            elif text.endswith('\r') or len(text) > 50:
                self.log_signal.emit(f"{timestamp}{self.buffer}\n")
                self.buffer = ""
            
    def write_to_text_edit(self, text):
        cursor = self.text_edit.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(text)
        self.text_edit.setTextCursor(cursor)
        self.text_edit.ensureCursorVisible()
        
    def flush(self):
        if self.buffer:
            timestamp = datetime.now().strftime('[%H:%M:%S] ')
            self.log_signal.emit(f"{timestamp}{self.buffer}\n")
            self.buffer = ""

class AutoClipSenderGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.process = None
        self.init_ui()
        
        # Check if the bot is already running when GUI starts (e.g., from another instance)
        self.check_for_running_bot()
    
    def get_config_value(self, key):
        """
        Get a configuration value with fallback to defaults
        """
        # First try to get from config.py
        import config
        try:
            return getattr(config, key)
        except AttributeError:
            # If not in config, try to get from DEFAULT_VALUES
            if key in DEFAULT_VALUES:
                return DEFAULT_VALUES[key]
            else:
                # Last resort, return empty string
                print(f"Warning: Config value {key} not found in config.py or defaults")
                return ""

    def init_ui(self):
        # Set window properties
        self.setWindowTitle('Auto Clip Sender')
        self.setGeometry(100, 100, 1000, 800)
        self.setup_dark_palette()
        
        # Add status bar
        self.statusBar().showMessage("Ready")
        
        # Main widget and layout
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        
        # Create a splitter for resizable sections
        splitter = QSplitter(Qt.Vertical)
        
        # Configuration section
        config_widget = QWidget()
        config_layout = QVBoxLayout(config_widget)
        
        # Create the tabs widget directly without a scroll area
        tabs_widget = self.create_config_tabs()
        config_layout.addWidget(tabs_widget)
        
        # Control buttons
        control_layout = QHBoxLayout()
        
        self.start_button = QPushButton("Start Monitoring")
        self.start_button.clicked.connect(self.start_monitoring)
        self.start_button.setStyleSheet("""
            QPushButton {
                background-color: #2ecc71;
                color: black;
                font-weight: bold;
            }
            QPushButton:disabled {
                background-color: #7f8c8d;
                color: #2d3436;
            }
        """)
        self.start_button.setEnabled(True)  # Explicitly set to enabled at startup
        
        self.stop_button = QPushButton("Stop Monitoring")
        self.stop_button.clicked.connect(self.stop_monitoring)
        self.stop_button.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: black;
                font-weight: bold;
            }
            QPushButton:disabled {
                background-color: #7f8c8d;
                color: #2d3436;
            }
        """)
        self.stop_button.setEnabled(False)  # Explicitly set to disabled at startup
        
        self.save_button = QPushButton("Save Configuration")
        self.save_button.clicked.connect(self.save_configuration)
        self.save_button.setStyleSheet("background-color: #3498db; color: black; font-weight: bold;")
        
        self.reset_all_button = QPushButton("Restore All Defaults")
        self.reset_all_button.clicked.connect(self.restore_all_defaults)
        self.reset_all_button.setStyleSheet("background-color: #f39c12; color: black; font-weight: bold;")
        
        control_layout.addWidget(self.start_button)
        control_layout.addWidget(self.stop_button)
        control_layout.addWidget(self.save_button)
        control_layout.addWidget(self.reset_all_button)
        
        config_layout.addLayout(control_layout)
        
        # Terminal output section
        terminal_widget = QWidget()
        terminal_layout = QVBoxLayout(terminal_widget)
        
        terminal_header = QLabel("Terminal Output")
        terminal_header.setFont(QFont("Arial", 12, QFont.Bold))
        terminal_layout.addWidget(terminal_header)
        
        self.terminal_output = QTextEdit()
        self.terminal_output.setReadOnly(True)
        self.terminal_output.setFont(QFont("Consolas", 10))  # Use monospace font for better alignment with timestamps
        self.terminal_output.setStyleSheet("background-color: #232629; color: #ffffff;")
        terminal_layout.addWidget(self.terminal_output)
        
        # Redirect stdout and stderr to our terminal output
        self.logger = QTextEditLogger(self.terminal_output)
        sys.stdout = self.logger
        sys.stderr = self.logger
        
        # Add widgets to splitter
        splitter.addWidget(config_widget)
        splitter.addWidget(terminal_widget)
        
        # Set initial sizes to allocate more space to the terminal and less to config
        # This will make the settings area smaller by default
        splitter.setSizes([400, 600])
        
        main_layout.addWidget(splitter)
        
        self.setCentralWidget(main_widget)
        
        # Log startup
        print(f"Auto Clip Sender GUI initialized at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("Ready to start monitoring. Configure your settings and click 'Start Monitoring'.")
    
    def setup_dark_palette(self):
        # Set up the dark mode palette
        palette = QPalette()
        
        # Base colors
        palette.setColor(QPalette.Window, QColor(53, 53, 53))
        palette.setColor(QPalette.WindowText, Qt.white)
        palette.setColor(QPalette.Base, QColor(25, 25, 25))
        palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
        palette.setColor(QPalette.ToolTipBase, Qt.white)
        palette.setColor(QPalette.ToolTipText, Qt.white)
        palette.setColor(QPalette.Text, Qt.white)
        palette.setColor(QPalette.Button, QColor(53, 53, 53))
        palette.setColor(QPalette.ButtonText, Qt.white)
        palette.setColor(QPalette.BrightText, Qt.red)
        palette.setColor(QPalette.Link, QColor(42, 130, 218))
        palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
        palette.setColor(QPalette.HighlightedText, Qt.black)
        
        # Apply the palette
        QApplication.setPalette(palette)
        
        # Set global stylesheet
        QApplication.setStyle("Fusion")
        
        # Additional stylesheet for better visibility of elements
        stylesheet = """
        QWidget {
            background-color: #2d2d2d;
            color: #ffffff;
        }
        QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
            background-color: #373737;
            border: 1px solid #555555;
            padding: 5px;
            border-radius: 3px;
            color: #ffffff;
        }
        QTabWidget::pane {
            border: 1px solid #555555;
            background-color: #2d2d2d;
        }
        QTabBar::tab {
            background-color: #353535;
            color: #ffffff;
            padding: 8px 15px;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
        }
        QTabBar::tab:selected {
            background-color: #4a4a4a;
        }
        QPushButton {
            background-color: #454545;
            color: #ffffff;
            border-radius: 3px;
            padding: 5px 15px;
            border: 1px solid #555555;
        }
        QPushButton:hover {
            background-color: #505050;
        }
        QPushButton:pressed {
            background-color: #353535;
        }
        QPushButton:disabled {
            background-color: #2d2d2d;
            color: #777777;
            border: 1px solid #444444;
        }
        QGroupBox {
            border: 1px solid #555555;
            border-radius: 5px;
            margin-top: 1ex;
            font-weight: bold;
            padding-top: 20px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top center;
            padding: 0 3px;
        }
        """
        self.setStyleSheet(stylesheet)
    
    def create_reset_button(self, setting_name, control):
        """Create a reset button for a specific setting"""
        button = QPushButton("Reset")
        button.setFixedWidth(60)
        button.setToolTip(f"Reset to default value: {DEFAULT_VALUES[setting_name]}")
        
        # Add specific reset functionality based on control type
        if isinstance(control, QLineEdit):
            button.clicked.connect(lambda: self.reset_control(control, DEFAULT_VALUES[setting_name], setting_name))
        elif isinstance(control, (QSpinBox, QDoubleSpinBox)):
            button.clicked.connect(lambda: self.reset_control(control, DEFAULT_VALUES[setting_name], setting_name))
        elif isinstance(control, QComboBox):
            button.clicked.connect(lambda: self.reset_control(control, DEFAULT_VALUES[setting_name], setting_name))
            
        return button
    
    def reset_control(self, control, default_value, setting_name):
        """Reset a control to its default value and notify the user"""
        if isinstance(control, QLineEdit):
            control.setText(default_value)
        elif isinstance(control, (QSpinBox, QDoubleSpinBox)):
            control.setValue(default_value)
        elif isinstance(control, QComboBox):
            control.setCurrentText(default_value)
        
        print(f"Reset {setting_name} to default value: {default_value}")
        # Update tooltip in case DEFAULT_VALUES changes
        self.statusBar().showMessage(f"Reset {setting_name} to default value: {default_value}", 3000)
    
    def create_setting_row(self, label_text, control, setting_name):
        """Create a row with label, control, and reset button"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(control)
        
        # Add reset button
        reset_button = self.create_reset_button(setting_name, control)
        layout.addWidget(reset_button)
        
        return (label_text, widget)
        
    def create_config_tabs(self):
        # Main configuration tab widget
        self.tabs = QTabWidget()
        
        # Create tabs for different settings categories
        folders_tab = QWidget()
        sizes_tab = QWidget()
        compression_tab = QWidget()
        ffmpeg_tab = QWidget()
        discord_tab = QWidget()
        
        # Set up layouts for each tab
        folders_layout = QVBoxLayout(folders_tab)
        sizes_layout = QVBoxLayout(sizes_tab)
        compression_layout = QVBoxLayout(compression_tab)
        ffmpeg_layout = QVBoxLayout(ffmpeg_tab)
        discord_layout = QVBoxLayout(discord_tab)
        
        # Add tabs to the tab widget
        self.tabs.addTab(folders_tab, "Folders")
        self.tabs.addTab(sizes_tab, "Size Limits")
        self.tabs.addTab(compression_tab, "Compression")
        self.tabs.addTab(ffmpeg_tab, "FFmpeg")
        self.tabs.addTab(discord_tab, "Discord")

        # FOLDERS TAB
        # Create folder path settings
        self.shadowplay_folder = QLineEdit(self.get_config_value('SHADOWPLAY_FOLDER'))
        shadowplay_browse = QPushButton("Browse...")
        shadowplay_browse.clicked.connect(lambda: self.browse_folder(self.shadowplay_folder))
        self.output_folder = QLineEdit(self.get_config_value('OUTPUT_FOLDER'))
        output_browse = QPushButton("Browse...")
        output_browse.clicked.connect(lambda: self.browse_folder(self.output_folder))
        
        # Add folder settings to layout
        folders_layout.addWidget(QLabel("Shadowplay Recordings Folder:"))
        folders_layout.addWidget(self.create_browse_row(self.shadowplay_folder, shadowplay_browse, 'SHADOWPLAY_FOLDER'))
        folders_layout.addWidget(QLabel("Output Folder for Processed Clips:"))
        folders_layout.addWidget(self.create_browse_row(self.output_folder, output_browse, 'OUTPUT_FOLDER'))
        folders_layout.addStretch()

        # SIZE LIMITS TAB
        # Create size limit settings
        self.min_size = NoWheelDoubleSpinBox()
        self.min_size.setRange(1, 50)
        self.min_size.setSingleStep(0.5)
        self.min_size.setValue(float(self.get_config_value('MIN_SIZE_MB')))
        
        self.max_size = NoWheelDoubleSpinBox()
        self.max_size.setRange(1, 50)
        self.max_size.setSingleStep(0.5)
        self.max_size.setValue(float(self.get_config_value('MAX_SIZE_MB')))
        
        self.target_size = NoWheelDoubleSpinBox()
        self.target_size.setRange(1, 50)
        self.target_size.setSingleStep(0.5)
        self.target_size.setValue(float(self.get_config_value('TARGET_SIZE_MB')))
        
        self.max_attempts = NoWheelSpinBox()
        self.max_attempts.setRange(1, 20)
        self.max_attempts.setValue(int(self.get_config_value('MAX_COMPRESSION_ATTEMPTS')))
        
        # Add size settings to layout
        sizes_layout.addWidget(QLabel("Minimum Size (MB):"))
        sizes_layout.addWidget(self.create_setting_row("Minimum Size (MB):", self.min_size, 'MIN_SIZE_MB')[1])
        sizes_layout.addWidget(QLabel("Maximum Size (MB):"))
        sizes_layout.addWidget(self.create_setting_row("Maximum Size (MB):", self.max_size, 'MAX_SIZE_MB')[1])
        sizes_layout.addWidget(QLabel("Target Size (MB):"))
        sizes_layout.addWidget(self.create_setting_row("Target Size (MB):", self.target_size, 'TARGET_SIZE_MB')[1])
        sizes_layout.addWidget(QLabel("Max Compression Attempts:"))
        sizes_layout.addWidget(self.create_setting_row("Max Compression Attempts:", self.max_attempts, 'MAX_COMPRESSION_ATTEMPTS')[1])
        sizes_layout.addStretch()

        # COMPRESSION TAB
        # Create compression settings
        self.crf_min = NoWheelSpinBox()
        self.crf_min.setRange(0, 51)
        self.crf_min.setValue(int(self.get_config_value('CRF_MIN')))
        
        self.crf_max = NoWheelSpinBox()
        self.crf_max.setRange(0, 51)
        self.crf_max.setValue(int(self.get_config_value('CRF_MAX')))
        
        self.crf_step = NoWheelSpinBox()
        self.crf_step.setRange(1, 10)
        self.crf_step.setValue(int(self.get_config_value('CRF_STEP')))
        
        self.clip_duration = NoWheelSpinBox()
        self.clip_duration.setRange(5, 300)
        self.clip_duration.setValue(int(self.get_config_value('CLIP_DURATION')))
        
        self.high_quality_crf = NoWheelSpinBox()
        self.high_quality_crf.setRange(0, 51)
        self.high_quality_crf.setValue(int(self.get_config_value('HIGH_QUALITY_CRF')))
        
        # Add compression settings to layout
        compression_layout.addWidget(QLabel("Minimum CRF Value:"))
        compression_layout.addWidget(self.create_setting_row("Minimum CRF Value:", self.crf_min, 'CRF_MIN')[1])
        compression_layout.addWidget(QLabel("Maximum CRF Value:"))
        compression_layout.addWidget(self.create_setting_row("Maximum CRF Value:", self.crf_max, 'CRF_MAX')[1])
        compression_layout.addWidget(QLabel("CRF Step Size:"))
        compression_layout.addWidget(self.create_setting_row("CRF Step Size:", self.crf_step, 'CRF_STEP')[1])
        compression_layout.addWidget(QLabel("Clip Duration (seconds):"))
        compression_layout.addWidget(self.create_setting_row("Clip Duration (seconds):", self.clip_duration, 'CLIP_DURATION')[1])
        compression_layout.addWidget(QLabel("High Quality CRF:"))
        compression_layout.addWidget(self.create_setting_row("High Quality CRF:", self.high_quality_crf, 'HIGH_QUALITY_CRF')[1])
        compression_layout.addStretch()

        # FFMPEG TAB
        # Create FFmpeg settings
        self.extract_preset = NoWheelComboBox()
        self.extract_preset.addItems(["ultrafast", "superfast", "veryfast", "faster", 
                                     "fast", "medium", "slow", "slower", "veryslow"])
        self.extract_preset.setCurrentText(self.get_config_value('EXTRACT_PRESET'))
        
        self.compression_preset = NoWheelComboBox()
        self.compression_preset.addItems(["ultrafast", "superfast", "veryfast", "faster", 
                                         "fast", "medium", "slow", "slower", "veryslow"])
        self.compression_preset.setCurrentText(self.get_config_value('COMPRESSION_PRESET'))
        
        # Add FFmpeg settings to layout
        ffmpeg_layout.addWidget(QLabel("Extract Preset:"))
        ffmpeg_layout.addWidget(self.create_setting_row("Extract Preset:", self.extract_preset, 'EXTRACT_PRESET')[1])
        ffmpeg_layout.addWidget(QLabel("Compression Preset:"))
        ffmpeg_layout.addWidget(self.create_setting_row("Compression Preset:", self.compression_preset, 'COMPRESSION_PRESET')[1])
        ffmpeg_layout.addStretch()

        # DISCORD TAB
        # Create Discord credential settings
        self.webhook_url = QLineEdit()
        # Load the webhook URL from environment variables
        webhook_url = os.getenv("WEBHOOK_URL", "")
        self.webhook_url.setText(webhook_url)
        
        # Add Discord settings to layout with a different approach (no reset button)
        webhook_layout = QHBoxLayout()
        webhook_layout.addWidget(self.webhook_url)
        webhook_layout.setContentsMargins(0, 0, 0, 0)
        
        webhook_widget = QWidget()
        webhook_widget.setLayout(webhook_layout)
        
        discord_layout.addWidget(QLabel("Discord Webhook URL:"))
        discord_layout.addWidget(webhook_widget)
        
        # Add a note about webhook usage
        webhook_note = QLabel("Create a webhook in your Discord server settings and paste the URL here.\nThe URL should look like: https://discord.com/api/webhooks/...")
        webhook_note.setWordWrap(True)
        discord_layout.addWidget(webhook_note)
        
        # Add a spacer to push everything to the top
        discord_layout.addStretch()
        
        # Add a "Test Webhook" button
        test_webhook_button = QPushButton("Test Webhook")
        test_webhook_button.clicked.connect(self.test_webhook)
        discord_layout.addWidget(test_webhook_button)
        
        return self.tabs
    
    def create_browse_row(self, line_edit, button, setting_name):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(line_edit)
        layout.addWidget(button)
        
        # Add reset button
        reset_button = self.create_reset_button(setting_name, line_edit)
        layout.addWidget(reset_button)
        
        return widget
    
    def browse_folder(self, line_edit):
        folder_path = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder_path:
            line_edit.setText(folder_path)
    
    def restore_all_defaults(self):
        """Restore all settings to their default values"""
        # Ask for confirmation first
        reply = QMessageBox.question(
            self, 
            "Restore Defaults", 
            "Are you sure you want to restore all settings to defaults?\nThis will not affect your current configuration until you save.",
            QMessageBox.Yes | QMessageBox.No, 
            QMessageBox.No
        )
        
        if reply == QMessageBox.No:
            return
        
        # Import defaults to ensure we're using the latest values
        try:
            import defaults
            import importlib
            importlib.reload(defaults)
            
            # Restore folder settings
            self.shadowplay_folder.setText(defaults.SHADOWPLAY_FOLDER)
            self.output_folder.setText(defaults.OUTPUT_FOLDER)
            
            # Restore size settings
            self.min_size.setValue(defaults.MIN_SIZE_MB)
            self.max_size.setValue(defaults.MAX_SIZE_MB)
            self.target_size.setValue(defaults.TARGET_SIZE_MB)
            self.max_attempts.setValue(defaults.MAX_COMPRESSION_ATTEMPTS)
            
            # Restore clip settings
            self.clip_duration.setValue(defaults.CLIP_DURATION)
            self.high_quality_crf.setValue(defaults.HIGH_QUALITY_CRF)
            
            # Restore compression settings
            self.crf_min.setValue(defaults.CRF_MIN)
            self.crf_max.setValue(defaults.CRF_MAX)
            self.crf_step.setValue(defaults.CRF_STEP)
            
            # Restore FFmpeg presets
            self.extract_preset.setCurrentText(defaults.EXTRACT_PRESET)
            self.compression_preset.setCurrentText(defaults.COMPRESSION_PRESET)
            
            # Restore threshold settings (if they exist in this form)
            if hasattr(self, 'close_threshold'):
                self.close_threshold.setValue(defaults.CLOSE_THRESHOLD)
            if hasattr(self, 'medium_threshold'):
                self.medium_threshold.setValue(defaults.MEDIUM_THRESHOLD)
            if hasattr(self, 'far_threshold'):
                self.far_threshold.setValue(defaults.FAR_THRESHOLD)
            
            print("Values restored from defaults.py")
        except ImportError:
            print("Warning: defaults.py not found, using hard-coded defaults")
            # Fall back to DEFAULT_VALUES if defaults.py can't be imported
            self.shadowplay_folder.setText(DEFAULT_VALUES['SHADOWPLAY_FOLDER'])
            self.output_folder.setText(DEFAULT_VALUES['OUTPUT_FOLDER'])
            
            # Restore size settings
            self.min_size.setValue(DEFAULT_VALUES['MIN_SIZE_MB'])
            self.max_size.setValue(DEFAULT_VALUES['MAX_SIZE_MB'])
            self.target_size.setValue(DEFAULT_VALUES['TARGET_SIZE_MB'])
            self.max_attempts.setValue(DEFAULT_VALUES['MAX_COMPRESSION_ATTEMPTS'])
            
            # Restore clip settings
            self.clip_duration.setValue(DEFAULT_VALUES['CLIP_DURATION'])
            self.high_quality_crf.setValue(DEFAULT_VALUES['HIGH_QUALITY_CRF'])
            
            # Restore compression settings
            self.crf_min.setValue(DEFAULT_VALUES['CRF_MIN'])
            self.crf_max.setValue(DEFAULT_VALUES['CRF_MAX'])
            self.crf_step.setValue(DEFAULT_VALUES['CRF_STEP'])
            
            # Restore FFmpeg presets
            self.extract_preset.setCurrentText(DEFAULT_VALUES['EXTRACT_PRESET'])
            self.compression_preset.setCurrentText(DEFAULT_VALUES['COMPRESSION_PRESET'])
            
            # Restore threshold settings (if they exist in this form)
            if hasattr(self, 'close_threshold'):
                self.close_threshold.setValue(DEFAULT_VALUES['CLOSE_THRESHOLD'])
            if hasattr(self, 'medium_threshold'):
                self.medium_threshold.setValue(DEFAULT_VALUES['MEDIUM_THRESHOLD'])
            if hasattr(self, 'far_threshold'):
                self.far_threshold.setValue(DEFAULT_VALUES['FAR_THRESHOLD'])
            
        # For webhook URL, keep the existing value by default
        # The webhook URL is sensitive info and doesn't have a default that makes sense to restore
        
        print("All settings have been restored to defaults. Click 'Save Configuration' to apply these changes.")
        QMessageBox.information(self, "Defaults Restored", "All settings have been restored to defaults. Click 'Save Configuration' to apply these changes.")
    
    def save_configuration(self):
        # Save settings to config.py
        try:
            with open('config.py', 'w') as f:
                f.write('"""\n')
                f.write('Configuration settings for the auto-clip-sender application.\n')
                f.write('This file can be committed to version control.\n')
                f.write('"""\n\n')
                
                # Folder configuration 
                f.write('# Folder configuration \n')
                f.write(f'SHADOWPLAY_FOLDER = "{self.shadowplay_folder.text()}"\n')
                f.write(f'OUTPUT_FOLDER = "{self.output_folder.text()}"\n\n')
                
                # Size limits
                f.write('# Size limits (MB)\n')
                f.write(f'MIN_SIZE_MB = {self.min_size.value()}      # Minimum target size (we want files to be at least this large)\n')
                f.write(f'MAX_SIZE_MB = {self.max_size.value()}     # Maximum size allowed by Discord\n')
                f.write(f'TARGET_SIZE_MB = {self.target_size.value()}   # Target size in the middle of our range\n')
                f.write(f'MAX_COMPRESSION_ATTEMPTS = {self.max_attempts.value()}  # Maximum number of compression iterations\n\n')
                
                # Compression settings
                f.write('# Compression settings\n')
                f.write(f'CRF_MIN = {self.crf_min.value()}          # Minimum CRF value (highest quality)\n')
                f.write(f'CRF_MAX = {self.crf_max.value()}         # Maximum CRF value (lowest quality)\n')
                f.write(f'CRF_STEP = {self.crf_step.value()}         # Step size for CRF adjustments\n\n')
                
                # FFmpeg presets
                f.write('# FFmpeg presets\n')
                f.write('# Options: ultrafast, superfast, veryfast, faster, fast, medium, slow, slower, veryslow\n')
                f.write(f'EXTRACT_PRESET = "{self.extract_preset.currentText()}"\n')
                f.write(f'COMPRESSION_PRESET = "{self.compression_preset.currentText()}"\n\n')
                
                # File processing settings
                f.write('# File processing settings\n')
                f.write(f'CLIP_DURATION = {self.clip_duration.value()}       # Duration in seconds to extract from the end of videos\n')
                f.write(f'HIGH_QUALITY_CRF = {self.high_quality_crf.value()}    # CRF value for initial high-quality extraction\n\n')
                
                # Threshold settings
                f.write('# Thresholds for adjustment size logic\n')
                f.write('CLOSE_THRESHOLD = 0.9    # 90% of target\n')
                f.write('MEDIUM_THRESHOLD = 0.75  # 75% of target\n')
                f.write('FAR_THRESHOLD = 0.5      # 50% of target \n')
                
            # Save Discord webhook URL to .env file
            self.save_env_file()
                
            print("Configuration saved successfully")
            if self.statusBar():
                self.statusBar().showMessage("Configuration saved successfully", 3000)
            return True
        except Exception as e:
            print(f"Error saving configuration: {e}")
            QMessageBox.critical(self, "Error", f"Failed to save configuration: {e}")
            return False

    def save_env_file(self):
        """
        Save sensitive information to the .env file
        """
        try:
            # Check if .env file exists and read its contents
            env_contents = {}
            if os.path.exists('.env'):
                with open('.env', 'r') as env_file:
                    for line in env_file:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            env_contents[key] = value
            
            # Update Discord webhook URL
            webhook_url = self.webhook_url.text().strip()
            if webhook_url:
                env_contents["WEBHOOK_URL"] = webhook_url
            
            # Write the updated .env file
            with open('.env', 'w') as env_file:
                for key, value in env_contents.items():
                    env_file.write(f"{key}={value}\n")
            
            print("Environment variables saved to .env file")
        except Exception as e:
            print(f"Error saving .env file: {e}")
            QMessageBox.critical(self, "Error", f"Failed to save .env file: {e}")

    def test_webhook(self):
        """
        Test the Discord webhook URL by sending a test message
        """
        webhook_url = self.webhook_url.text().strip()
        if not webhook_url:
            QMessageBox.warning(self, "Warning", "Please enter a webhook URL first")
            return
            
        try:
            import requests
            
            # Show that we're testing
            if self.statusBar():
                self.statusBar().showMessage("Testing webhook...", 3000)
                
            # Send a test message to the webhook
            data = {
                "content": "Test message from Auto-Clip-Sender! If you see this, your webhook is working correctly."
            }
            
            response = requests.post(webhook_url, json=data)
            
            if response.status_code == 204 or response.status_code == 200:
                QMessageBox.information(self, "Success", "Webhook test successful! Check your Discord channel for the test message.")
                print("Webhook test successful")
            else:
                QMessageBox.warning(self, "Warning", f"Webhook test failed with status code {response.status_code}: {response.text}")
                print(f"Webhook test failed: HTTP {response.status_code} - {response.text}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to test webhook: {e}")
            print(f"Error testing webhook: {e}")
    
    def start_monitoring(self):
        # Validate settings before starting
        if not self.validate_settings():
            return
        
        # Save the configuration
        self.save_configuration()
        
        # Check if clip_processor.py exists
        if not os.path.exists("clip_processor.py"):
            QMessageBox.critical(self, "Error", "clip_processor.py not found in the current directory. Please ensure the file exists.")
            return
        
        # Get Python executable path
        python_exe = sys.executable
        print(f"Using Python executable: {python_exe}")
        print(f"Current working directory: {os.getcwd()}")
        
        try:
            # Start the bot process
            self.process = QProcess()
            self.process.readyReadStandardOutput.connect(self.handle_stdout)
            self.process.readyReadStandardError.connect(self.handle_stderr)
            self.process.finished.connect(self.process_finished)
            
            # Start the bot.py script
            print("Starting clip_processor.py...")
            self.process.start(python_exe, ["clip_processor.py"])
            
            # Wait for process to start
            if not self.process.waitForStarted(3000):  # 3 second timeout
                QMessageBox.critical(self, "Error", "Failed to start clip_processor.py process. Check if Python is installed correctly.")
                return
            
            # Update UI buttons - disable start, enable stop
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(True)
            print("Process started successfully.")
        except Exception as e:
            print(f"Error starting monitoring process: {e}")
            QMessageBox.critical(self, "Error", f"Failed to start monitoring process: {e}")
    
    def validate_settings(self):
        # Validate all settings before starting the bot
        
        # Check if folders exist
        if not os.path.isdir(self.shadowplay_folder.text()):
            QMessageBox.warning(self, "Invalid Setting", "Shadowplay folder doesn't exist.")
            return False
            
        # Create output folder if it doesn't exist
        if not os.path.isdir(self.output_folder.text()):
            try:
                os.makedirs(self.output_folder.text())
                print(f"Created output folder: {self.output_folder.text()}")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Could not create output folder: {str(e)}")
                return False
                
        # Validate value relationships
        if self.min_size.value() >= self.max_size.value():
            QMessageBox.warning(self, "Invalid Setting", "Min size must be less than max size.")
            return False
            
        if self.target_size.value() < self.min_size.value() or self.target_size.value() > self.max_size.value():
            QMessageBox.warning(self, "Invalid Setting", "Target size must be between min and max sizes.")
            return False
            
        if self.crf_min.value() >= self.crf_max.value():
            QMessageBox.warning(self, "Invalid Setting", "CRF min must be less than CRF max.")
            return False
            
        return True
    
    def stop_monitoring(self):
        if self.process and self.process.state() == QProcess.Running:
            print("Stopping monitoring...")
            
            # Update UI to show we're in the process of stopping
            self.statusBar().showMessage("Stopping the monitoring process... Please wait.")
            self.terminal_output.append("[" + datetime.now().strftime('%H:%M:%S') + "] Stopping monitoring process... Please wait.")
            self.stop_button.setText("Stopping...")
            self.stop_button.setEnabled(False)  # Disable to prevent multiple clicks
            QApplication.setOverrideCursor(Qt.WaitCursor)  # Show wait cursor
            
            # Use a timer to allow the UI to update before blocking on process termination
            QApplication.processEvents()
            
            # Terminate the process
            self.process.terminate()
            
            # Give it 3 seconds to terminate gracefully
            if not self.process.waitForFinished(3000):
                print("Force killing process...")
                self.terminal_output.append("[" + datetime.now().strftime('%H:%M:%S') + "] Force killing unresponsive process...")
                self.process.kill()
            
            # Restore UI
            QApplication.restoreOverrideCursor()  # Restore normal cursor
            self.stop_button.setText("Stop Monitoring")
            
            # Update UI buttons - enable start, disable stop
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            self.statusBar().showMessage("Monitoring stopped", 3000)
            print("Monitoring stopped.")
        else:
            # Process not running
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            self.statusBar().showMessage("No monitoring process to stop", 3000)
    
    def handle_stdout(self):
        data = self.process.readAllStandardOutput().data().decode('utf-8')
        print(data, end='')
    
    def handle_stderr(self):
        try:
            data = self.process.readAllStandardError().data().decode('utf-8')
            # Check if this is a fatal error message
            if "Traceback" in data or "Error:" in data:
                print(f"ERROR: {data}", end='')
            else:
                print(data, end='')
        except Exception as e:
            print(f"Error handling stderr: {e}")
    
    def process_finished(self, exit_code, exit_status):
        # Update UI buttons - enable start, disable stop
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        
        if exit_code != 0:
            print(f"Bot process exited with code {exit_code}")
        else:
            print("Bot process ended normally.")
    
    def closeEvent(self, event):
        # Stop the bot process when closing the application
        self.stop_monitoring()
        event.accept()

    def reload_env_credentials(self):
        """
        Reload the Discord credentials from the .env file
        """
        try:
            # Reload dotenv in case the .env file was modified
            from dotenv import load_dotenv
            load_dotenv(override=True)
            
            # Update the webhook URL field
            webhook_url = os.getenv("WEBHOOK_URL", "")
            self.webhook_url.setText(webhook_url)
            
            print("Reloaded Discord webhook URL from .env file")
        except Exception as e:
            print(f"Error reloading environment variables: {e}")

    def check_for_running_bot(self):
        """Check if the bot process is already running and update button states"""
        try:
            # Different process checking methods for different operating systems
            if os.name == 'nt':  # Windows
                try:
                    import wmi
                    f = wmi.WMI()
                    # Look for clip_processor.py in process list
                    for process in f.Win32_Process():
                        if 'clip_processor.py' in process.CommandLine or 'clip_processor' in process.CommandLine:
                            # Only show message if debug logging is enabled
                            if os.getenv("DEBUG_LOGGING") == "1":
                                print("Found running clip_processor.py process")
                            # Update buttons to reflect the running state
                            self.start_button.setEnabled(False)
                            self.stop_button.setEnabled(True)
                            return True
                except ImportError:
                    # WMI not installed, use alternative method - only log in debug mode
                    if os.getenv("DEBUG_LOGGING") == "1":
                        print("WMI module not available. Using alternative process detection method.")
                    import subprocess
                    result = subprocess.run(['tasklist', '/fo', 'csv', '/nh'], capture_output=True, text=True)
                    if 'python' in result.stdout.lower():
                        # Check if any python process is running our script
                        processes = subprocess.run(['wmic', 'process', 'where', 'name like "%python%"', 'get', 'commandline'], 
                                                  capture_output=True, text=True)
                        if 'clip_processor.py' in processes.stdout:
                            if os.getenv("DEBUG_LOGGING") == "1":
                                print("Found running clip_processor.py process")
                            # Update buttons to reflect the running state
                            self.start_button.setEnabled(False)
                            self.stop_button.setEnabled(True)
                            return True
            else:  # Unix-like
                import subprocess
                # Use ps command to find clip_processor.py processes
                result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
                if 'clip_processor.py' in result.stdout:
                    if os.getenv("DEBUG_LOGGING") == "1":
                        print("Found running clip_processor.py process")
                    # Update buttons to reflect the running state
                    self.start_button.setEnabled(False)
                    self.stop_button.setEnabled(True)
                    return True
        except Exception as e:
            if os.getenv("DEBUG_LOGGING") == "1":
                print(f"Error checking for running bot: {e}")
            # Don't change button states if we couldn't check
            return False
        
        # If we reach here, no process was found - only log in debug mode
        if os.getenv("DEBUG_LOGGING") == "1":
            print("No running clip_processor.py process found")
        
        # Set button states
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        return False


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = AutoClipSenderGUI()
    window.show()
    sys.exit(app.exec_()) 