import sys
import os
import json
import threading
import importlib.util
from datetime import datetime

# Import our config helper for proper path handling
import config_helper

# Get proper application and config paths
APP_DIR = config_helper.get_application_path()
CONFIG_DIR = config_helper.get_user_config_dir()

# Add code to ensure we can find modules when running as an executable
if getattr(sys, 'frozen', False):
    # Running as compiled executable
    os.environ['PATH'] = APP_DIR + os.pathsep + os.environ.get('PATH', '')
    sys.path.insert(0, APP_DIR)
    print(f"Running as executable from: {APP_DIR}")
    
    # Add ffmpeg to PATH if it exists
    ffmpeg_dir = os.path.join(APP_DIR, 'ffmpeg')
    if os.path.exists(ffmpeg_dir) and ffmpeg_dir not in os.environ['PATH']:
        os.environ['PATH'] = ffmpeg_dir + os.pathsep + os.environ['PATH']
        print(f"Added ffmpeg directory to PATH: {ffmpeg_dir}")

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QTabWidget, QSpinBox, QDoubleSpinBox, QComboBox, QTextEdit, QFileDialog, QMessageBox, QSplitter
)
from PyQt5.QtCore import Qt, QProcess, pyqtSignal, QObject, QProcessEnvironment, QSize
from PyQt5.QtGui import QFont, QPalette, QColor, QTextCursor, QIcon, QPixmap

# Import dotenv for environment variables - use absolute path
from dotenv import load_dotenv

# Get current directory for .env file path
env_path = config_helper.get_config_file_path('.env')

# Load .env file with explicit path
print(f"Loading environment variables from: {env_path}")
load_dotenv(dotenv_path=env_path)

# Default configuration values
DEFAULT_CONFIG = {
    'SHADOWPLAY_FOLDER': "C:/Users/YourName/Videos/Shadowplay Recordings",
    'OUTPUT_FOLDER': "C:/Users/YourName/Videos/Shadowplay Recordings/auto-clips",
    'MIN_SIZE_MB': 8.0,
    'MAX_SIZE_MB': 10.0,
    'TARGET_SIZE_MB': 9.0,
    'MAX_COMPRESSION_ATTEMPTS': 5,
    'CRF_MIN': 1,
    'CRF_MAX': 30,
    'CRF_STEP': 1,
    'EXTRACT_PRESET': "fast",
    'COMPRESSION_PRESET': "medium",
    'COMPRESSION_METHOD': "Quick",
    'QUICK_CRF': 40,
    'CLIP_DURATION': 15,
    'HIGH_QUALITY_CRF': 18,
    'CLOSE_THRESHOLD': 0.9,
    'MEDIUM_THRESHOLD': 0.75,
    'FAR_THRESHOLD': 0.5,
    'WEBHOOK_URL': ""
}

# Load configuration using config_helper
CONFIG_FILE = 'config.json'
DEFAULTS_FILE = 'defaults.json'

# Load defaults.json
# First, ensure defaults.json exists
if not os.path.exists(config_helper.get_config_file_path(DEFAULTS_FILE)):
    print(f"Creating default configuration file: {DEFAULTS_FILE}")
    config_helper.save_json_config(DEFAULT_CONFIG, DEFAULTS_FILE)

# Load defaults
DEFAULT_VALUES = config_helper.load_json_config(DEFAULTS_FILE)
# Ensure all keys exist in DEFAULT_VALUES
for key, value in DEFAULT_CONFIG.items():
    if key not in DEFAULT_VALUES:
        DEFAULT_VALUES[key] = value

# Load user configuration or create it from defaults
CONFIG = config_helper.load_json_config(CONFIG_FILE)
if not CONFIG:
    print(f"Creating user configuration file from defaults: {CONFIG_FILE}")
    CONFIG = DEFAULT_VALUES.copy()
    config_helper.save_json_config(CONFIG, CONFIG_FILE)

def remove_last_line(text_edit):
    text = text_edit.toPlainText()

    lines = text.split("\n")
    if lines:
        lines.pop()  # Remove the last line
        text_edit.setPlainText("\n".join(lines))

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
        self.processor_thread = None
        self.stop_event = threading.Event()
        
        # Look for the icon in the _internal folder first (for PyInstaller build)
        # Then fallback to root directory (for development)
        internal_icon_path = os.path.join(APP_DIR, '_internal', '128x128.ico')
        root_icon_path = os.path.join(APP_DIR, '128x128.ico')
        
        # Choose the first available icon path
        icon_path = None
        if os.path.exists(internal_icon_path):
            icon_path = internal_icon_path
            print(f"GUI: Using icon from _internal folder")
        elif os.path.exists(root_icon_path):
            icon_path = root_icon_path
            print(f"GUI: Using icon from root directory")
        
        if icon_path:
            # Set the window icon directly
            window_icon = QIcon(icon_path)
            self.setWindowIcon(window_icon)
            
            # Set app ID for Windows (helps with taskbar icon)
            if os.name == 'nt':
                try:
                    import ctypes
                    app_id = "autoClipSender.1.0"
                    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
                    print(f"GUI: Set Windows Application User Model ID")
                except Exception as e:
                    print(f"GUI: Error setting application ID: {e}")
        else:
            print(f"GUI: Icon file not found in any location")
            
        self.init_ui()
        
        # Check if the clip processor is already running when GUI starts (e.g., from another instance)
        self.check_for_running_processor()
    
    def get_config_value(self, key):
        """
        Get a configuration value with fallback to defaults
        """
        # First try to get from user config
        if key in CONFIG:
            return CONFIG[key]
        # If not in config, try to get from DEFAULT_VALUES
        elif key in DEFAULT_VALUES:
            return DEFAULT_VALUES[key]
        else:
            # Last resort, return empty string
            print(f"Warning: Config value {key} not found in config.json or defaults.json")
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
        
        # Set the central widget
        self.setCentralWidget(main_widget)
        
        # Load webhook URL from config
        if hasattr(self, 'webhook_url'):
            self.webhook_url.setText(CONFIG.get('WEBHOOK_URL', ''))
        
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
        clipping_tab = QWidget()  # New tab for clipping/processing settings
        compression_tab = QWidget()
        ffmpeg_tab = QWidget()
        discord_tab = QWidget()
        
        # Set up layouts for each tab
        folders_layout = QVBoxLayout(folders_tab)
        sizes_layout = QVBoxLayout(sizes_tab)
        clipping_layout = QVBoxLayout(clipping_tab)  # Layout for new tab
        compression_layout = QVBoxLayout(compression_tab)
        ffmpeg_layout = QVBoxLayout(ffmpeg_tab)
        discord_layout = QVBoxLayout(discord_tab)
        
        # Add tabs to the tab widget - insert new tab after folders and sizes
        self.tabs.addTab(folders_tab, "Folders")
        self.tabs.addTab(sizes_tab, "Size Limits")
        self.tabs.addTab(clipping_tab, "Clipping")  # Add new tab
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
        
        # CLIPPING TAB (NEW)
        # Move clip duration and compression method settings to this tab
        self.clip_duration = NoWheelSpinBox()
        self.clip_duration.setRange(5, 300)
        self.clip_duration.setValue(int(self.get_config_value('CLIP_DURATION')))
        
        # Compression method selector
        self.compression_method = NoWheelComboBox()
        self.compression_method.addItems(["Progressive", "Quick"])
        self.compression_method.setCurrentText(self.get_config_value('COMPRESSION_METHOD'))
        
        # Quick CRF value setting
        self.quick_crf = NoWheelSpinBox()
        self.quick_crf.setRange(1, 51)
        self.quick_crf.setValue(int(self.get_config_value('QUICK_CRF')))
        
        # Help labels
        clip_duration_help = QLabel("Duration in seconds to extract from the end of each recording.")
        clip_duration_help.setWordWrap(True)
        
        # Compression method selector
        self.compression_method = NoWheelComboBox()
        self.compression_method.addItems(["Progressive", "Quick"])
        self.compression_method.setCurrentText(self.get_config_value('COMPRESSION_METHOD'))
        
        # Quick CRF value setting
        self.quick_crf = NoWheelSpinBox()
        self.quick_crf.setRange(1, 51)
        self.quick_crf.setValue(int(self.get_config_value('QUICK_CRF')))
        
        compression_method_help = QLabel("• Quick: Single pass compression that produces smaller files quickly\n• Progressive: Multiple passes to find optimal quality-to-size ratio (slower but higher quality)")
        compression_method_help.setWordWrap(True)
        
        quick_crf_help = QLabel("CRF value for Quick compression (1-51). Lower values = better quality but larger files. Higher values = worse quality but smaller files. Values above 35 may show noticeable quality loss.")
        quick_crf_help.setWordWrap(True)
        
        # Add settings to clipping tab layout
        clipping_layout.addWidget(QLabel("Clip Duration (seconds):"))
        clipping_layout.addWidget(self.create_setting_row("Clip Duration (seconds):", self.clip_duration, 'CLIP_DURATION')[1])
        clipping_layout.addWidget(clip_duration_help)
        clipping_layout.addSpacing(20)  # Add some space between settings
        
        clipping_layout.addWidget(QLabel("Compression Method:"))
        clipping_layout.addWidget(self.create_setting_row("Compression Method:", self.compression_method, 'COMPRESSION_METHOD')[1])
        clipping_layout.addWidget(compression_method_help)
        clipping_layout.addSpacing(10)
        
        clipping_layout.addWidget(QLabel("Quick Compression CRF:"))
        clipping_layout.addWidget(self.create_setting_row("Quick CRF:", self.quick_crf, 'QUICK_CRF')[1])
        clipping_layout.addWidget(quick_crf_help)
        clipping_layout.addStretch()

        # COMPRESSION TAB
        # Create compression settings - removed clip duration and compression method
        self.crf_min = NoWheelSpinBox()
        self.crf_min.setRange(0, 51)
        self.crf_min.setValue(int(self.get_config_value('CRF_MIN')))
        
        self.crf_max = NoWheelSpinBox()
        self.crf_max.setRange(0, 51)
        self.crf_max.setValue(int(self.get_config_value('CRF_MAX')))
        
        self.crf_step = NoWheelSpinBox()
        self.crf_step.setRange(1, 10)
        self.crf_step.setValue(int(self.get_config_value('CRF_STEP')))
        
        self.high_quality_crf = NoWheelSpinBox()
        self.high_quality_crf.setRange(0, 51)
        self.high_quality_crf.setValue(int(self.get_config_value('HIGH_QUALITY_CRF')))
        
        # Add a help label explaining CRF values
        crf_help = QLabel("CRF (Constant Rate Factor) controls quality. Lower values = higher quality, larger files.")
        crf_help.setWordWrap(True)
        
        # Add compression settings to layout - removed clip duration and compression method
        compression_layout.addWidget(crf_help)
        compression_layout.addSpacing(10)
        
        compression_layout.addWidget(QLabel("Minimum CRF Value:"))
        compression_layout.addWidget(self.create_setting_row("Minimum CRF Value:", self.crf_min, 'CRF_MIN')[1])
        compression_layout.addWidget(QLabel("Maximum CRF Value:"))
        compression_layout.addWidget(self.create_setting_row("Maximum CRF Value:", self.crf_max, 'CRF_MAX')[1])
        compression_layout.addWidget(QLabel("CRF Step Size:"))
        compression_layout.addWidget(self.create_setting_row("CRF Step Size:", self.crf_step, 'CRF_STEP')[1])
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
        # Load the webhook URL from CONFIG
        self.webhook_url.setText(self.get_config_value('WEBHOOK_URL'))
        print(f"Loaded webhook URL from config: {'[SET]' if self.webhook_url.text() else '[NOT SET]'}")
        
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
        
        # Save current webhook URL before restoring defaults
        current_webhook_url = self.webhook_url.text().strip()
        
        # Load default values
        try:
            defaults = config_helper.load_json_config(DEFAULTS_FILE)
            if not defaults:
                raise ValueError("defaults.json could not be loaded")
                
            print("Restoring settings from defaults.json")
                
            # Restore folder settings
            self.shadowplay_folder.setText(defaults.get('SHADOWPLAY_FOLDER', DEFAULT_CONFIG['SHADOWPLAY_FOLDER']))
            self.output_folder.setText(defaults.get('OUTPUT_FOLDER', DEFAULT_CONFIG['OUTPUT_FOLDER']))
            
            # Restore size settings
            self.min_size.setValue(defaults.get('MIN_SIZE_MB', DEFAULT_CONFIG['MIN_SIZE_MB']))
            self.max_size.setValue(defaults.get('MAX_SIZE_MB', DEFAULT_CONFIG['MAX_SIZE_MB']))
            self.target_size.setValue(defaults.get('TARGET_SIZE_MB', DEFAULT_CONFIG['TARGET_SIZE_MB']))
            self.max_attempts.setValue(defaults.get('MAX_COMPRESSION_ATTEMPTS', DEFAULT_CONFIG['MAX_COMPRESSION_ATTEMPTS']))
            
            # Restore clip settings
            self.clip_duration.setValue(defaults.get('CLIP_DURATION', DEFAULT_CONFIG['CLIP_DURATION']))
            self.high_quality_crf.setValue(defaults.get('HIGH_QUALITY_CRF', DEFAULT_CONFIG['HIGH_QUALITY_CRF']))
            
            # Restore compression settings - fix to use values from defaults.json
            self.crf_min.setValue(defaults.get('CRF_MIN', DEFAULT_CONFIG['CRF_MIN']))
            self.crf_max.setValue(defaults.get('CRF_MAX', DEFAULT_CONFIG['CRF_MAX']))
            self.crf_step.setValue(defaults.get('CRF_STEP', DEFAULT_CONFIG['CRF_STEP']))
            self.compression_method.setCurrentText(defaults.get('COMPRESSION_METHOD', DEFAULT_CONFIG['COMPRESSION_METHOD']))
            self.quick_crf.setValue(defaults.get('QUICK_CRF', DEFAULT_CONFIG['QUICK_CRF']))
            
            # Restore FFmpeg presets
            self.extract_preset.setCurrentText(defaults.get('EXTRACT_PRESET', DEFAULT_CONFIG['EXTRACT_PRESET']))
            self.compression_preset.setCurrentText(defaults.get('COMPRESSION_PRESET', DEFAULT_CONFIG['COMPRESSION_PRESET']))
            
            print("Settings restored from defaults.json")
        except Exception as e:
            print(f"Error restoring from defaults.json: {e}")
            print("Falling back to hardcoded DEFAULT_CONFIG")
            
            # Fall back to DEFAULT_CONFIG if defaults.json has issues
            self.shadowplay_folder.setText(DEFAULT_CONFIG['SHADOWPLAY_FOLDER'])
            self.output_folder.setText(DEFAULT_CONFIG['OUTPUT_FOLDER'])
            
            # Restore size settings
            self.min_size.setValue(DEFAULT_CONFIG['MIN_SIZE_MB'])
            self.max_size.setValue(DEFAULT_CONFIG['MAX_SIZE_MB'])
            self.target_size.setValue(DEFAULT_CONFIG['TARGET_SIZE_MB'])
            self.max_attempts.setValue(DEFAULT_CONFIG['MAX_COMPRESSION_ATTEMPTS'])
            
            # Restore clip settings
            self.clip_duration.setValue(DEFAULT_CONFIG['CLIP_DURATION'])
            self.high_quality_crf.setValue(DEFAULT_CONFIG['HIGH_QUALITY_CRF'])
            
            # Restore compression settings
            self.crf_min.setValue(DEFAULT_CONFIG['CRF_MIN'])
            self.crf_max.setValue(DEFAULT_CONFIG['CRF_MAX'])
            self.crf_step.setValue(DEFAULT_CONFIG['CRF_STEP'])
            self.compression_method.setCurrentText(DEFAULT_CONFIG['COMPRESSION_METHOD'])
            self.quick_crf.setValue(DEFAULT_CONFIG['QUICK_CRF'])
            
            # Restore FFmpeg presets
            self.extract_preset.setCurrentText(DEFAULT_CONFIG['EXTRACT_PRESET'])
            self.compression_preset.setCurrentText(DEFAULT_CONFIG['COMPRESSION_PRESET'])
        
        # Keep the current webhook URL instead of resetting it
        self.webhook_url.setText(current_webhook_url)
        print("Webhook URL preserved during defaults restoration")
        
        print("All settings except webhook URL have been restored to defaults. Click 'Save Configuration' to apply these changes.")
        QMessageBox.information(self, "Defaults Restored", "All settings except webhook URL have been restored to defaults. Click 'Save Configuration' to apply these changes.")
    
    def save_configuration(self):
        # Prepare config dictionary with values from UI elements
        config = {
            'SHADOWPLAY_FOLDER': self.shadowplay_folder.text(),
            'OUTPUT_FOLDER': self.output_folder.text(),
            'MIN_SIZE_MB': self.min_size.value(),
            'MAX_SIZE_MB': self.max_size.value(),
            'TARGET_SIZE_MB': self.target_size.value(),
            'MAX_COMPRESSION_ATTEMPTS': self.max_attempts.value(),
            'CRF_MIN': self.crf_min.value(),
            'CRF_MAX': self.crf_max.value(),
            'CRF_STEP': self.crf_step.value(),
            'EXTRACT_PRESET': self.extract_preset.currentText(),
            'COMPRESSION_PRESET': self.compression_preset.currentText(),
            'CLIP_DURATION': self.clip_duration.value(),
            'HIGH_QUALITY_CRF': self.high_quality_crf.value(),
            'QUICK_CRF': self.quick_crf.value(),
            'WEBHOOK_URL': self.webhook_url.text(),
            'COMPRESSION_METHOD': self.compression_method.currentText()
        }
        
        # Add threshold values from CONFIG (these don't have UI elements)
        global CONFIG
        if 'CLOSE_THRESHOLD' in CONFIG:
            config['CLOSE_THRESHOLD'] = CONFIG['CLOSE_THRESHOLD']
        else:
            config['CLOSE_THRESHOLD'] = DEFAULT_CONFIG['CLOSE_THRESHOLD']
            
        if 'MEDIUM_THRESHOLD' in CONFIG:
            config['MEDIUM_THRESHOLD'] = CONFIG['MEDIUM_THRESHOLD']
        else:
            config['MEDIUM_THRESHOLD'] = DEFAULT_CONFIG['MEDIUM_THRESHOLD']
            
        if 'FAR_THRESHOLD' in CONFIG:
            config['FAR_THRESHOLD'] = CONFIG['FAR_THRESHOLD']
        else:
            config['FAR_THRESHOLD'] = DEFAULT_CONFIG['FAR_THRESHOLD']
        
        # Save to config.json
        try:
            # Save config to the config.json file
            if config_helper.save_json_config('config.json', config):
                print("Configuration saved successfully")
                # Update our in-memory config
                CONFIG = config
                
                # Show success message in status bar
                self.statusBar().showMessage("Configuration saved successfully", 3000)
            else:
                print("Error saving configuration")
                QMessageBox.warning(self, "Error", "Failed to save configuration.")
        except Exception as e:
            print(f"Error saving configuration: {e}")
            QMessageBox.warning(self, "Error", f"Failed to save configuration: {str(e)}")

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
        
        # Save configuration before starting
        print("Saving configuration before starting monitoring...")
        self.save_configuration()
            
        # Check if we're running in frozen mode
        if getattr(sys, 'frozen', False):
            print("Starting clip monitoring in executable mode...")
            
            # Create a stop event for the processor
            self.stop_event.clear()
            
            # Define a function to run the clip processor in a thread
            def run_clip_processor():
                try:
                    # Import clip_processor module
                    import clip_processor
                    
                    # Run the clip processor with our stop event
                    clip_processor.run(self.stop_event)
                    
                    # Reset the UI when the thread exits
                    self.start_button.setEnabled(True)
                    self.stop_button.setEnabled(False)
                except Exception as e:
                    print(f"Error in clip processor thread: {e}")
                    # Import traceback here to avoid circular import
                    import traceback
                    traceback.print_exc()
                    
                    # Show error in UI
                    self.start_button.setEnabled(True)
                    self.stop_button.setEnabled(False)
            
            # Start the thread
            self.processor_thread = threading.Thread(target=run_clip_processor)
            self.processor_thread.daemon = True  # Make thread exit when main thread exits
            self.processor_thread.start()
            
            # Update UI buttons
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(True)
        else:
            # Development mode - use subprocess approach
            processor_path = "clip_processor.py"
            if not os.path.exists(processor_path):
                QMessageBox.critical(self, "Error", "clip_processor.py not found. Please ensure the file exists.")
                return
        
            # Get Python executable path
            python_exe = sys.executable
            
            try:
                # Start the clip processor process
                self.process = QProcess()
                self.process.readyReadStandardOutput.connect(self.handle_stdout)
                self.process.readyReadStandardError.connect(self.handle_stderr)
                self.process.finished.connect(self.process_finished)
            
                # Set up correct environment 
                env = QProcessEnvironment.systemEnvironment()
                self.process.setProcessEnvironment(env)
                
                # Start the clip_processor.py script directly
                print("Starting clip monitoring in development mode...")
                self.process.start(python_exe, [processor_path])
            
                # Wait for process to start
                if not self.process.waitForStarted(3000):  # 3 second timeout
                    QMessageBox.critical(self, "Error", "Failed to start clip processor. Check if Python is installed correctly.")
                    return
            
                # Update UI buttons - disable start, enable stop
                self.start_button.setEnabled(False)
                self.stop_button.setEnabled(True)
                
            except Exception as e:
                print(f"Error starting monitoring process: {e}")
                QMessageBox.critical(self, "Error", f"Failed to start monitoring process: {e}")
    
    def validate_settings(self):
        # Validate all settings before starting the clip processor
        
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
        # Check if we're in frozen mode with a thread
        if getattr(sys, 'frozen', False) and self.processor_thread is not None:
            print("Stopping clip monitoring...")
            # Signal the thread to stop
            self.stop_event.set()
            
            # Wait for thread to complete (with timeout)
            if self.processor_thread.is_alive():
                self.processor_thread.join(timeout=1.0)
                
            # Reset thread reference
            self.processor_thread = None
            
            # Update UI buttons - enable start, disable stop
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)
        elif self.process is not None:
            # Development mode with process
            print("Stopping clip monitoring process...")
            try:
                # Try to terminate the process gracefully
                self.process.terminate()
                
                # Wait for it to terminate
                if not self.process.waitForFinished(3000):  # 3 second timeout
                    # If it doesn't terminate, kill it
                    self.process.kill()
                    print("Process killed.")
                
                # Update UI buttons - enable start, disable stop
                self.start_button.setEnabled(True)
                self.stop_button.setEnabled(False)
                
                # Reset process reference
                self.process = None
            except Exception as e:
                print(f"Error stopping process: {e}")
        else:
            print("No running clip processor to stop")
            # Update UI buttons - enable start, disable stop
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)
    
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
            print(f"Clip processor exited with code {exit_code}")
        else:
            print("Clip processor ended normally.")
    
    def closeEvent(self, event):
        # Stop the clip processor when closing the application
        self.stop_monitoring()
        event.accept()

    def check_for_running_processor(self):
        """Check if the clip processor is already running and update button states"""
        try:
            # Simplified process checking method for Windows
            if os.name == 'nt':  # Windows
                    import subprocess
                # First check if any python processes exist
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
                print(f"Error checking for running clip processor: {e}")
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