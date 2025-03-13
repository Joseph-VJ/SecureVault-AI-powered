from PySide6.QtWidgets import (
    QDialog,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
)
from PySide6.QtGui import QFont, QTextCursor
from loguru import logger
import os
import sys
from typing import Optional

# Determine if the application is packaged with PyInstaller
IS_PACKAGED = getattr(sys, 'frozen', False)

# Configure log file path dynamically
if IS_PACKAGED:
    # Use a directory next to the executable for logs
    log_dir = os.path.join(os.path.dirname(sys.executable), 'logs')
    os.makedirs(log_dir, exist_ok=True)  # Create the directory if it doesn’t exist
    LOG_FILE_PATH = os.path.join(log_dir, 'secure_vault.log')
else:
    LOG_FILE_PATH = os.getenv("LOG_FILE_PATH", "secure_vault.log")

LOG_RETENTION = os.getenv("LOG_RETENTION", "1 year")

# Remove default logger
logger.remove()

# Add file handler for logging to file
logger.add(
    LOG_FILE_PATH,
    rotation="10 MB",  # Rotate log file when it reaches 10 MB
    retention=LOG_RETENTION,  # Configurable retention period
    compression="zip",  # Compress old log files
    enqueue=True,  # Asynchronous logging
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
    level="DEBUG"  # Capture all log levels
)

# Add console handler only if not packaged and sys.stdout is available
if not IS_PACKAGED and sys.stdout is not None:
    logger.add(
        sys.stdout,
        colorize=True,  # Colorize console output
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
        level="DEBUG"
    )

# Logging functions with improved message formatting
def log_debug(action: str, details: Optional[str] = None) -> None:
    """Log a debug message."""
    message = action.upper()
    if details:
        message += f" - {details}"
    logger.debug(message)

def log_info(action: str, details: Optional[str] = None) -> None:
    """Log an info message."""
    message = action.upper()
    if details:
        message += f" - {details}"
    logger.info(message)

def log_warning(action: str, details: Optional[str] = None) -> None:
    """Log a warning message."""
    message = action.upper()
    if details:
        message += f" - {details}"
    logger.warning(message)

def log_error(action: str, details: Optional[str] = None) -> None:
    """Log an error message."""
    message = action.upper()
    if details:
        message += f" - {details}"
    logger.error(message)

def log_critical(action: str, details: Optional[str] = None) -> None:
    """Log a critical message."""
    message = action.upper()
    if details:
        message += f" - {details}"
    logger.critical(message)

def log_exception(action: str, exc_info: Optional[tuple] = None) -> None:
    """Log an exception with traceback."""
    message = f"{action.upper()} - Exception occurred"
    if exc_info:
        logger.exception(message, exc_info=exc_info)
    else:
        logger.error(message)

# Log Viewer Dialog
class LogViewer(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Application Logs")
        self.resize(800, 600)
        
        # Layout setup
        layout = QVBoxLayout(self)
        
        # Display log file path
        file_label = QLabel(f"Log file: {LOG_FILE_PATH}")
        layout.addWidget(file_label)
        
        # Text edit for logs
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setFont(QFont("Courier"))  # Monospace font for alignment
        layout.addWidget(self.text_edit)
        
        # Buttons layout
        button_layout = QHBoxLayout()
        
        # Refresh button
        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self.refresh_logs)
        button_layout.addWidget(refresh_button)
        
        # Close button
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        button_layout.addWidget(close_button)
        
        layout.addLayout(button_layout)
        
        # Load logs initially
        self.refresh_logs()
    
    def refresh_logs(self):
        """Refresh the log display."""
        try:
            with open(LOG_FILE_PATH, "r") as f:
                logs = f.read()
            self.text_edit.setText(logs)
            self.text_edit.moveCursor(QTextCursor.End)  # Scroll to bottom
        except Exception as e:
            self.text_edit.setText(f"Error reading log file: {str(e)}")