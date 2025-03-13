import os
import logging
import time
import threading
import matplotlib.pyplot as plt
import shutil
from PySide6.QtWidgets import (QMainWindow, QApplication, QWidget, QVBoxLayout,
                              QHBoxLayout, QPushButton, QLabel, QComboBox,
                              QFileDialog, QMessageBox, QProgressBar, QScrollArea,
                              QListWidget, QStackedWidget, QFrame, QSplitter,
                              QTextEdit, QToolButton, QMenu, QGraphicsDropShadowEffect)
from PySide6.QtCore import Qt, Signal, Slot, QThread, QSize
from PySide6.QtGui import QIcon, QFont, QPixmap, QColor, QPalette, QAction

# Placeholder imports (replace with your actual modules)
from encryption import *
from key_manager import generate_key
from secure_wipe import secure_wipe_drive, get_available_wipe_methods, wipe_drive
from main_content import create_main_content
from progress_visualization import ProgressTracker
from logs import LogViewer

# Configure logging
logger = logging.getLogger("SecureVault")
logging.basicConfig(filename="secure_vault.log", level=logging.INFO,
                    format="%(asctime)s - %(levelname)s - %(message)s")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

class Modern3DButton(QPushButton):
    def __init__(self, text, parent=None, icon_path=None, accent_color="#38B2AC"):
        super().__init__(text, parent)
        self.accent_color = accent_color
        self.default_color = "#333333"
        self.hover_color = self._lighten_color(self.accent_color, 0.1)
        self.pressed_color = self._darken_color(self.accent_color, 0.2)
        
        if icon_path and os.path.exists(icon_path):
            self.setIcon(QIcon(icon_path))
            self.setIconSize(QSize(22, 22))
        
        # Enhanced shadow for floating effect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(25)
        shadow.setColor(QColor(0, 0, 0, 100))
        shadow.setOffset(0, 8)
        self.setGraphicsEffect(shadow)
        
        self.setMinimumHeight(45)
        self.setCursor(Qt.PointingHandCursor)
        self.setObjectName("modern3dButton")
        self.apply_style()
        
        self.pressed.connect(self.on_press)
        self.released.connect(self.on_release)
    
    def apply_style(self):
        self.setStyleSheet(f"""
            QPushButton#modern3dButton {{
                background-color: {self.accent_color};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-weight: bold;
                text-align: left;
                border-bottom: 3px solid {self._darken_color(self.accent_color, 0.3)};
            }}
            QPushButton#modern3dButton:hover {{
                background-color: {self.hover_color};
            }}
            QPushButton#modern3dButton:pressed {{
                background-color: {self.pressed_color};
                border-bottom: 1px solid {self._darken_color(self.accent_color, 0.3)};
                padding-top: 12px;
            }}
        """)
    
    def on_press(self):
        shadow = self.graphicsEffect()
        shadow.setOffset(0, 2)
        shadow.setBlurRadius(10)
    
    def on_release(self):
        shadow = self.graphicsEffect()
        shadow.setOffset(0, 8)
        shadow.setBlurRadius(25)
    
    def _lighten_color(self, color, factor=0.1):
        r, g, b = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)
        r = min(255, int(r + (255 - r) * factor))
        g = min(255, int(g + (255 - g) * factor))
        b = min(255, int(b + (255 - b) * factor))
        return f"#{r:02x}{g:02x}{b:02x}"
    
    def _darken_color(self, color, factor=0.1):
        r, g, b = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)
        r = max(0, int(r * (1 - factor)))
        g = max(0, int(g * (1 - factor)))
        b = max(0, int(b * (1 - factor)))
        return f"#{r:02x}{g:02x}{b:02x}"

class WipeThread(QThread):
    progress_updated = Signal(int, int)
    operation_completed = Signal(bool, str)
    total_size_calculated = Signal(int, int, int)
    
    def __init__(self, drive_path, method):
        super().__init__()
        self.drive_path = drive_path
        self.method = method
        self.cancelled = False
        self.paused = False
        self.pause_condition = threading.Condition()
    
    def run(self):
        try:
            self.wipe_start_time = time.time()
            self.wipe_times = []
            self.wipe_total_size, self.file_count = self.get_directory_size(self.drive_path)
            self.total_size_calculated.emit(self.wipe_total_size, self.method.passes, self.file_count)
            total_passes = self.method.passes
            patterns = self.method.patterns
            
            for i in range(total_passes):
                if self.cancelled:
                    return
                
                with self.pause_condition:
                    while self.paused and not self.cancelled:
                        self.pause_condition.wait()
                
                start_time = time.time()
                pattern = patterns[i % len(patterns)]
                secure_wipe_drive(self.drive_path, 1, [pattern], delete_after=False)
                end_time = time.time()
                self.wipe_times.append(end_time - start_time)
                self.progress_updated.emit(i + 1, total_passes)
            
            if not self.cancelled:
                secure_wipe_drive(self.drive_path, 1, [b'\x00'], delete_after=True)
                self.progress_updated.emit(total_passes, total_passes)
                self.operation_completed.emit(True, "Wipe completed successfully")
        except Exception as e:
            self.operation_completed.emit(False, str(e))
    
    def get_directory_size(self, path):
        total_size = 0
        file_count = 0
        for dirpath, dirnames, filenames in os.walk(path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                if not os.path.islink(fp):
                    total_size += os.path.getsize(fp)
                    file_count += 1
        return total_size, file_count
    
    def pause(self):
        with self.pause_condition:
            self.paused = not self.paused
            if not self.paused:
                self.pause_condition.notify_all()
    
    def cancel(self):
        self.cancelled = True
        with self.pause_condition:
            self.paused = False
            self.pause_condition.notify_all()

class CryptoThread(QThread):
    progress_updated = Signal(int, int)
    operation_completed = Signal(bool, str, float)
    
    def __init__(self, operation, file_path, method_type, out_path, key):
        super().__init__()
        self.operation = operation
        self.file_path = file_path
        self.method_type = method_type
        self.out_path = out_path
        self.key = key
        self.progress_tracker = ProgressTracker()
        self.progress_tracker.set_callback(self.update_progress)
    
    def run(self):
        try:
            self.start_time = time.time()
            if self.operation == "encrypt":
                if self.method_type == "Fernet":
                    encrypt_file_in_chunks(
                        encrypt_data_fernet, self.key, self.file_path, 
                        self.out_path, self.progress_tracker
                    )
                else:
                    encrypt_file_in_chunks(
                        encrypt_data_aes, self.key, self.file_path, 
                        self.out_path, self.progress_tracker
                    )
                message = "File encrypted successfully"
            else:
                if self.method_type == "Fernet":
                    decrypt_file_in_chunks(
                        decrypt_data_fernet, self.key, self.file_path, 
                        self.out_path, self.progress_tracker
                    )
                else:
                    decrypt_file_in_chunks(
                        decrypt_data_aes, self.key, self.file_path, 
                        self.out_path, self.progress_tracker
                    )
                message = "File decrypted successfully"
            elapsed_time = time.time() - self.start_time
            self.operation_completed.emit(True, message, elapsed_time)
        except Exception as e:
            self.operation_completed.emit(False, str(e), 0.0)
    
    def update_progress(self, processed, total):
        self.progress_updated.emit(processed, total)

class SecureVaultApp(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("SecureVault")
        self.resize(1200, 800)
        
        self.ENCRYPTION_MAP = {
            "Fernet (default)": ("Fernet", 32),
            "AES-128": ("AES", 16),
            "AES-192": ("AES", 24),
            "AES-256": ("AES", 32)
        }
        self.current_key = None
        self.progress_tracker = ProgressTracker()
        self.wipe_times = []
        self.wipe_thread = None
        self.crypto_thread = None
        
        self.setup_ui()
    
    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        self.sidebar = self.create_sidebar()
        main_layout.addWidget(self.sidebar)
        
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        
        self.header = self.create_header()
        right_layout.addWidget(self.header)
        
        self.content_stack = QStackedWidget()
        self.content_stack.setObjectName("contentStack")
        
        self.main_content = create_main_content(self)
        self.content_stack.addWidget(self.main_content)
        right_layout.addWidget(self.content_stack)
        
        main_layout.addWidget(right_panel)
        
        self.statusBar().showMessage("Ready")
        self.statusBar().setStyleSheet(
            "QStatusBar { background-color: #21232a; color: #f0f0f0; padding: 5px; }"
        )
        
        self.log_button = QPushButton("View Logs")
        self.log_button.setStyleSheet(
            "QPushButton { background: none; color: #81E6D9; border: none; }"
            "QPushButton:hover { text-decoration: underline; }"
        )
        self.log_button.clicked.connect(self.show_logs)
        self.statusBar().addPermanentWidget(self.log_button)
        
        self.apply_stylesheet()
    
    def create_sidebar(self):
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(250)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)
        
        logo_area = QWidget()
        logo_area.setObjectName("logoArea")
        logo_area.setFixedHeight(150)
        logo_layout = QVBoxLayout(logo_area)
        
        logo_path = os.path.join(SCRIPT_DIR, "assets", "logo_main.png")
        logo_pixmap = QPixmap(logo_path)
        
        if logo_pixmap.isNull():
            logger.warning(f"Logo file not found at {logo_path}")
        
        logo_label = QLabel()
        logo_label.setPixmap(logo_pixmap)
        logo_label.setAlignment(Qt.AlignCenter)
        logo_layout.addStretch()
        logo_layout.addWidget(logo_label, alignment=Qt.AlignHCenter)
        logo_layout.addStretch()
        
        sidebar_layout.addWidget(logo_area)
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(15, 15, 15, 15)
        scroll_layout.setSpacing(15)
        
        menu_label = QLabel("MAIN MENU")
        menu_label.setObjectName("menuHeader")
        scroll_layout.addWidget(menu_label)
        
        gen_key_btn = Modern3DButton("Generate Key", scroll_content, "icons/key-icon.png", "#38B2AC")
        gen_key_btn.clicked.connect(self.generate_key_ui)
        scroll_layout.addWidget(gen_key_btn)
        
        enc_file_btn = Modern3DButton("Encrypt File", scroll_content, "icons/lock-icon.png", "#48BB78")
        enc_file_btn.clicked.connect(self.encrypt_file)
        scroll_layout.addWidget(enc_file_btn)
        
        dec_file_btn = Modern3DButton("Decrypt File", scroll_content, "icons/unlock-icon.png", "#4299E1")
        dec_file_btn.clicked.connect(self.decrypt_file)
        scroll_layout.addWidget(dec_file_btn)
        
        wipe_btn = Modern3DButton("Wipe Directory", scroll_content, "icons/trash-icon.png", "#F56565")
        wipe_btn.clicked.connect(self.wipe_drive)
        scroll_layout.addWidget(wipe_btn)
        
        scroll_layout.addSpacing(20)
        
        settings_label = QLabel("SETTINGS")
        settings_label.setObjectName("menuHeader")
        scroll_layout.addWidget(settings_label)
        
        enc_method_label = QLabel("Encryption Method:")
        enc_method_label.setObjectName("settingLabel")
        scroll_layout.addWidget(enc_method_label)
        
        self.encryption_method_combo = QComboBox()
        self.encryption_method_combo.setObjectName("settingCombo")
        for method in self.ENCRYPTION_MAP.keys():
            self.encryption_method_combo.addItem(method)
        scroll_layout.addWidget(self.encryption_method_combo)
        
        wipe_method_label = QLabel("Wipe Method:")
        wipe_method_label.setObjectName("settingLabel")
        scroll_layout.addWidget(wipe_method_label)
        
        self.wipe_method_combo = QComboBox()
        self.wipe_method_combo.setObjectName("settingCombo")
        wipe_methods = list(get_available_wipe_methods().keys())
        for method in wipe_methods:
            self.wipe_method_combo.addItem(method)
        scroll_layout.addWidget(self.wipe_method_combo)
        
        scroll_layout.addStretch()
        
        scroll_area.setWidget(scroll_content)
        sidebar_layout.addWidget(scroll_area)
        
        return sidebar

    def create_header(self):
        header = QWidget()
        header.setObjectName("header")
        header.setFixedHeight(60)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 0, 20, 0)
        
        title = QLabel("SecureVault Dashboard")
        title.setObjectName("pageTitle")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        return header

    def apply_stylesheet(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #171923;
                color: #f0f0f0;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 10pt;
            }
            #sidebar {
                background-color: #171923;
                border-right: 1px solid #333;
            }
            #logoArea {
                background-color: #171923;
                padding: 10px;
                border-bottom: 1px solid #333;
            }
            #menuHeader {
                color: #81E6D9;
                font-size: 10pt;
                font-weight: bold;
                margin-top: 15px;
                margin-bottom: 5px;
            }
            #settingLabel {
                color: #81E6D9;
                margin-top: 5px;
            }
            #settingCombo {
                background-color: #333;
                border: 1px solid #555;
                border-radius: 3px;
                color: white;
                padding: 5px;
                selection-background-color: #81E6D9;
            }
            #header {
                background-color: #21232a;
                border-bottom: 1px solid #333;
            }
            #pageTitle {
                font-size: 16pt;
                font-weight: bold;
                color: #f0f0f0;
            }
            #contentStack {
                background-color: #171923;
            }
            QProgressBar {
                border: 1px solid #555;
                border-radius: 3px;
                background-color: #333;
                text-align: center;
                color: white;
            }
            QProgressBar::chunk {
                background-color: #81E6D9;
            }
            QPushButton {
                background-color: #38B2AC;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #4AD2C6;
            }
            QPushButton:pressed {
                background-color: #2A9286;
            }
        """)

    def generate_key_ui(self):
        try:
            method_name = self.encryption_method_combo.currentText()
            method_type, key_size = self.ENCRYPTION_MAP[method_name]
            
            if method_type == "Fernet":
                key = generate_key("Fernet")
            else:
                key = os.urandom(key_size)
            
            key_path, _ = QFileDialog.getSaveFileName(
                self, "Save Encryption Key", "", "Key Files (*.key)"
            )
            
            if key_path:
                with open(key_path, "wb") as f:
                    f.write(key)
                
                self.current_key = key
                self.statusBar().showMessage(f"{method_name} key saved successfully!", 5000)
                QMessageBox.information(self, "Success", f"{method_name} key generated and saved successfully!")
                logger.info(f"Generated and saved {method_name} key")
        except Exception as e:
            self.statusBar().showMessage("Error generating key", 5000)
            QMessageBox.critical(self, "Error", f"Key generation failed: {str(e)}")
            logger.error(f"Key generation failed: {str(e)}")
    
    def encrypt_file(self):
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self, "Select File to Encrypt", "", "All Files (*)"
            )
            
            if not file_path:
                return
            
            key_path, _ = QFileDialog.getOpenFileName(
                self, "Select Encryption Key", "", "Key Files (*.key)"
            )
            
            if not key_path:
                return
            
            with open(key_path, "rb") as f:
                key = f.read()
            
            method_name = self.encryption_method_combo.currentText()
            method_type, key_size = self.ENCRYPTION_MAP[method_name]
            
            if method_type == "Fernet" and not self.validate_fernet_key(key):
                raise ValueError("Invalid Fernet key for selected method")
            elif method_type == "AES" and len(key) != key_size:
                raise ValueError(f"Key size ({len(key)*8} bits) does not match {method_name}")
            
            out_path = f"{file_path}.enc"
            self.show_progress_dialog("Encrypting File", "encrypt", file_path, method_type, out_path, key)
        except Exception as e:
            self.statusBar().showMessage("Error encrypting file", 5000)
            QMessageBox.critical(self, "Error", f"Encryption failed: {str(e)}")
            logger.error(f"Encryption failed: {str(e)}")
    
    def decrypt_file(self):
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self, "Select File to Decrypt", "", "Encrypted Files (*.enc);;All Files (*)"
            )
            
            if not file_path:
                return
            
            key_path, _ = QFileDialog.getOpenFileName(
                self, "Select Encryption Key", "", "Key Files (*.key)"
            )
            
            if not key_path:
                return
            
            with open(key_path, "rb") as f:
                key = f.read()
            
            method_name = self.encryption_method_combo.currentText()
            method_type, key_size = self.ENCRYPTION_MAP[method_name]
            
            if method_type == "Fernet" and not self.validate_fernet_key(key):
                raise ValueError("Invalid Fernet key for selected method")
            elif method_type == "AES" and len(key) != key_size:
                raise ValueError(f"Key size ({len(key)*8} bits) does not match {method_name}")
            
            out_path = file_path[:-4] if file_path.endswith('.enc') else f"{file_path}.dec"
            self.show_progress_dialog("Decrypting File", "decrypt", file_path, method_type, out_path, key)
        except Exception as e:
            self.statusBar().showMessage("Error decrypting file", 5000)
            QMessageBox.critical(self, "Error", f"Decryption failed: {str(e)}")
            logger.error(f"Decryption failed: {str(e)}")
    
    def validate_fernet_key(self, key):
        try:
            from cryptography.fernet import Fernet
            Fernet(key)
            return True
        except Exception:
            return False
    
    def wipe_drive(self):
        drive_path = QFileDialog.getExistingDirectory(
            self, "Select Directory to Wipe"
        )
        
        if not drive_path:
            return
        
        confirm = QMessageBox.question(
            self, "Confirm Wipe",
            f"Are you sure you want to wipe '{drive_path}'?\n\nThis action cannot be undone!",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if confirm != QMessageBox.Yes:
            return
        
        method_name = self.wipe_method_combo.currentText()
        method = get_available_wipe_methods()[method_name]
        self.show_wipe_progress_dialog(drive_path, method)
    
    def show_progress_dialog(self, title, operation, file_path, method_type, out_path, key):
        dialog = QWidget(self, Qt.Window)
        dialog.setWindowTitle(title)
        dialog.setFixedSize(450, 250)
        dialog.setWindowModality(Qt.ApplicationModal)
        
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        status_label = QLabel("Operation in progress...")
        status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(status_label)
        
        progress_bar = QProgressBar()
        progress_bar.setMinimum(0)
        progress_bar.setMaximum(100)
        progress_bar.setTextVisible(True)
        progress_bar.setFixedHeight(25)
        chunk_color = "#48BB78" if operation == "encrypt" else "#4299E1"
        progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid #555;
                border-radius: 5px;
                background-color: #333;
                color: white;
                text-align: center;
            }}
            QProgressBar::chunk {{
                background-color: {chunk_color};
                border-radius: 5px;
            }}
        """)
        layout.addWidget(progress_bar)
        
        progress_label = QLabel("Processed: 0.00 MB / 0.00 MB")
        layout.addWidget(progress_label)
        
        file_info = QLabel(f"File: {os.path.basename(file_path)}")
        file_info.setWordWrap(True)
        layout.addWidget(file_info)
        
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        cancel_button = Modern3DButton("Cancel", dialog, None, "#F56565")
        cancel_button.setFixedHeight(40)
        button_layout.addWidget(cancel_button)
        
        layout.addLayout(button_layout)
        
        self.crypto_thread = CryptoThread(operation, file_path, method_type, out_path, key)
        self.crypto_thread.progress_updated.connect(
            lambda processed, total: self.update_crypto_progress(progress_bar, progress_label, processed, total)
        )
        self.crypto_thread.operation_completed.connect(
            lambda success, message, elapsed_time: self.handle_crypto_completion(
                success, message, elapsed_time, dialog, operation, file_path, method_type, out_path
            )
        )
        
        cancel_button.clicked.connect(self.crypto_thread.terminate)
        self.crypto_thread.start()
        
        dialog.show()
    
    def update_crypto_progress(self, progress_bar, progress_label, processed, total):
        percent = int(processed / total * 100) if total > 0 else 0
        progress_bar.setValue(percent)
        mb_processed = processed / (1024 * 1024)
        mb_total = total / (1024 * 1024)
        progress_label.setText(f"Processed: {mb_processed:.2f} MB / {mb_total:.2f} MB")
    
    def handle_crypto_completion(self, success, message, elapsed_time, dialog, operation, file_path, method_type, out_path):
        dialog.close()
        if success:
            self.show_crypto_summary(operation, file_path, method_type, elapsed_time, out_path)
        else:
            self.statusBar().showMessage("Operation failed", 5000)
            QMessageBox.critical(self, "Error", message)
    
    def show_crypto_summary(self, operation, file_path, method_type, elapsed_time, out_path):
        summary = QWidget(self, Qt.Window)
        summary.setWindowTitle(f"{operation.capitalize()} Operation Summary")
        summary.setMinimumSize(400, 300)
        
        layout = QVBoxLayout(summary)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        title_color = "#48BB78" if operation == "encrypt" else "#4299E1"
        title_label = QLabel(f"{operation.capitalize()} Completed")
        title_label.setStyleSheet(f"font-size: 16pt; font-weight: bold; color: {title_color};")
        layout.addWidget(title_label)
        
        info_frame = QFrame()
        info_frame.setFrameShape(QFrame.StyledPanel)
        info_frame.setStyleSheet("QFrame { background-color: #333; border-radius: 5px; padding: 10px; }")
        
        info_layout = QVBoxLayout(info_frame)
        info_layout.addWidget(QLabel(f"Operation: {operation.capitalize()}"))
        info_layout.addWidget(QLabel(f"File: {os.path.basename(file_path)}"))
        file_size = os.path.getsize(file_path) / (1024 * 1024)
        info_layout.addWidget(QLabel(f"File Size: {file_size:.2f} MB"))
        info_layout.addWidget(QLabel(f"Method: {method_type}"))
        info_layout.addWidget(QLabel(f"Time Taken: {elapsed_time:.2f} seconds"))
        if elapsed_time > 0:
            speed = file_size / elapsed_time
            info_layout.addWidget(QLabel(f"{operation.capitalize()} Speed: {speed:.2f} MB/s"))
        info_layout.addWidget(QLabel(f"Output File: {os.path.basename(out_path)}"))
        
        layout.addWidget(info_frame)
        
        close_button = Modern3DButton("Close", summary, None, "#555")
        close_button.clicked.connect(summary.close)
        layout.addWidget(close_button)
        
        summary.show()
    
    def show_wipe_progress_dialog(self, drive_path, method):
        dialog = QWidget(self, Qt.Window)
        dialog.setWindowTitle("Wiping Directory")
        dialog.setFixedSize(500, 320)
        dialog.setWindowModality(Qt.ApplicationModal)
        
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        status_label = QLabel(f"Wiping directory: {drive_path}")
        status_label.setWordWrap(True)
        layout.addWidget(status_label)
        
        method_info = QLabel(f"Method: {method.name}")
        method_info.setStyleSheet("font-weight: bold; color: #F56565;")
        layout.addWidget(method_info)
        
        progress_info = QLabel("Pass: 0/0")
        layout.addWidget(progress_info)
        
        progress_bar = QProgressBar()
        progress_bar.setMinimum(0)
        progress_bar.setMaximum(100)
        progress_bar.setFixedHeight(25)
        progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #555;
                border-radius: 5px;
                background-color: #333;
                color: white;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #F56565;
                border-radius: 5px;
            }
        """)
        layout.addWidget(progress_bar)
        
        progress_label = QLabel("Processed: 0.00 MB / 0.00 MB")
        layout.addWidget(progress_label)
        
        warning = QLabel("Warning: This process cannot be undone!")
        warning.setStyleSheet("color: #ED8936; font-style: italic;")
        layout.addWidget(warning)
        
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        pause_button = Modern3DButton("Pause", dialog, None, "#ED8936")
        pause_button.setFixedHeight(40)
        
        cancel_button = Modern3DButton("Cancel", dialog, None, "#F56565")
        cancel_button.setFixedHeight(40)
        
        button_layout.addWidget(pause_button)
        button_layout.addWidget(cancel_button)
        
        layout.addLayout(button_layout)
        
        self.wipe_thread = WipeThread(drive_path, method)
        self.wipe_thread.total_size_calculated.connect(
            lambda total_size, total_passes, file_count: self.set_wipe_totals(
                dialog, total_size, total_passes, file_count, progress_label
            )
        )
        self.wipe_thread.progress_updated.connect(
            lambda current, total: self.update_wipe_progress(
                progress_bar, progress_info, progress_label, current, total, dialog
            )
        )
        self.wipe_thread.operation_completed.connect(
            lambda success, message: self.handle_wipe_completion(success, message, dialog, drive_path, method)
        )
        
        pause_button.clicked.connect(self.wipe_thread.pause)
        cancel_button.clicked.connect(self.wipe_thread.cancel)
        
        self.wipe_thread.start()
        
        dialog.show()
    
    def set_wipe_totals(self, dialog, total_size, total_passes, file_count, progress_label):
        dialog.total_size = total_size
        dialog.total_passes = total_passes
        dialog.file_count = file_count
        mb_total = (total_size * total_passes) / (1024 * 1024)
        progress_label.setText(f"Processed: 0.00 MB / {mb_total:.2f} MB")
    
    def update_wipe_progress(self, progress_bar, progress_info, progress_label, current, total, dialog):
        percent = int(current / total * 100)
        progress_bar.setValue(percent)
        progress_info.setText(f"Pass: {current}/{total}")
        if hasattr(dialog, 'total_size') and hasattr(dialog, 'total_passes'):
            mb_processed = (current * dialog.total_size) / (1024 * 1024)
            mb_total = (dialog.total_passes * dialog.total_size) / (1024 * 1024)
            progress_label.setText(f"Processed: {mb_processed:.2f} MB / {mb_total:.2f} MB")
        else:
            progress_label.setText("Calculating total size...")
    
    def handle_wipe_completion(self, success, message, dialog, drive_path, method):
        dialog.close()
        self.wipe_times = self.wipe_thread.wipe_times
        
        if success:
            total_passes = method.passes
            total_size = self.wipe_thread.wipe_total_size
            file_count = self.wipe_thread.file_count
            status_msg = f"Directory wiped using {method.name}"
            self.statusBar().showMessage(status_msg, 5000)
            self.show_wipe_summary(method.name, total_passes, total_size, file_count)
        else:
            self.statusBar().showMessage("Wipe operation failed", 5000)
            QMessageBox.critical(self, "Error", message)
    
    def show_wipe_summary(self, method_name, passes, total_size, file_count):
        summary = QWidget(self, Qt.Window)
        summary.setWindowTitle("Wipe Operation Summary")
        summary.setMinimumSize(600, 450)
        
        layout = QVBoxLayout(summary)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        title_label = QLabel("Wipe Operation Complete")
        title_label.setStyleSheet("font-size: 16pt; font-weight: bold; color: #F56565;")
        layout.addWidget(title_label)
        
        info_frame = QFrame()
        info_frame.setFrameShape(QFrame.StyledPanel)
        info_frame.setStyleSheet("QFrame { background-color: #333; border-radius: 5px; padding: 10px; }")
        
        info_layout = QVBoxLayout(info_frame)
        info_layout.addWidget(QLabel(f"Method: {method_name}"))
        info_layout.addWidget(QLabel(f"Passes: {passes}"))
        info_layout.addWidget(QLabel(f"Total Size: {total_size / (1024 * 1024):.2f} MB"))
        info_layout.addWidget(QLabel(f"Files Wiped: {file_count}"))
        
        total_time = sum(self.wipe_times)
        info_layout.addWidget(QLabel(f"Total Time: {total_time:.2f} seconds"))
        if self.wipe_times:
            avg_time = total_time / len(self.wipe_times)
            info_layout.addWidget(QLabel(f"Average Time per Pass: {avg_time:.2f} seconds"))
        total_data_processed = total_size * passes
        if total_time > 0:
            speed_mb_s = (total_data_processed / (1024 * 1024)) / total_time
            info_layout.addWidget(QLabel(f"Wipe Speed: {speed_mb_s:.2f} MB/s"))
        
        layout.addWidget(info_frame)
        
        table_label = QLabel("Pass Completion Times:")
        table_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(table_label)
        
        table = QListWidget()
        table.setAlternatingRowColors(True)
        table.setStyleSheet("""
            QListWidget {
                background-color: #333;
                border-radius: 5px;
                padding: 5px;
            }
            QListWidget::item {
                padding: 5px;
                border-bottom: 1px solid #444;
            }
            QListWidget::item:alternate {
                background-color: #2a2a2a;
            }
        """)
        
        for i, time_val in enumerate(self.wipe_times, 1):
            table.addItem(f"Pass {i}: {time_val:.2f} seconds")
        
        layout.addWidget(table)
        
        button_layout = QHBoxLayout()
        
        graph_button = Modern3DButton("Show Time Graph", summary, None, "#38B2AC")
        graph_button.clicked.connect(lambda: self.show_wipe_graph())
        
        close_button = Modern3DButton("Close", summary, None, "#555")
        close_button.clicked.connect(summary.close)
        
        button_layout.addWidget(graph_button)
        button_layout.addWidget(close_button)
        
        layout.addLayout(button_layout)
        
        summary.show()
    
    def show_wipe_graph(self):
        passes = list(range(1, len(self.wipe_times) + 1))
        plt.figure(figsize=(8, 5))
        plt.plot(passes, self.wipe_times, 'o-', color='#F56565')
        plt.title('Wipe Pass Completion Times')
        plt.xlabel('Pass Number')
        plt.ylabel('Time (seconds)')
        plt.grid(True)
        plt.tight_layout()
        plt.show()
    
    def show_logs(self):
        log_viewer = LogViewer(self)
        log_viewer.exec()

if __name__ == "__main__":
    app = QApplication([])
    window = SecureVaultApp()
    window.show()
    app.exec()