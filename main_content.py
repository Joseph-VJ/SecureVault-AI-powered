import os
import threading
import time
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QTextEdit, QLineEdit,
                             QComboBox, QFrame, QScrollArea, QDialog, QListWidget, QListWidgetItem, QFileDialog)
from PySide6.QtCore import Qt, Signal, Slot, QThread
from PySide6.QtGui import QFont, QTextCursor, QColor
import bcrypt
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.fernet import Fernet
import base64
import json
import logging

try:
    import markdown
    MARKDOWN_AVAILABLE = True
except ImportError:
    MARKDOWN_AVAILABLE = False

logger = logging.getLogger("SecureVault")

try:
    from openai import OpenAI
    OPENAI_INSTALLED = True
except ImportError:
    OPENAI_INSTALLED = False

# API Key (replace with your OpenRouter API key)
API_KEY = "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"
MODEL_NAME = "deepseek/deepseek-chat:free"

# Available AI models with metadata
AVAILABLE_MODELS = [
    {"id": "deepseek/deepseek-chat:free", "name": "DeepSeek Chat (Default)", "description": "DeepSeek's conversational model with balanced speed and power.", "speed": 7, "power": 7, "pros": "Balanced performance, suitable for most tasks.", "cons": "May not excel in highly specialized areas."},
    {"id": "undi95/toppy-m-7b", "name": "Toppy-M-7B", "description": "Faster 7B model optimized for quick responses.", "speed": 9, "power": 5, "pros": "Very fast, great for quick queries.", "cons": "Less powerful for complex tasks."},
    {"id": "huggingfaceh4/zephyr-7b-beta", "name": "Zephyr 7B", "description": "Fast and accurate 7B model for general tasks.", "speed": 8, "power": 6, "pros": "Reliable speed with decent accuracy.", "cons": "Limited depth for advanced queries."},
    {"id": "mistralai/mistral-7b-instruct", "name": "Mistral 7B", "description": "Good balance of speed and quality for instruction-following.", "speed": 7, "power": 7, "pros": "Strong instruction adherence.", "cons": "Moderate speed for large tasks."},
    {"id": "mistralai/mistral-7b-instruct:floor", "name": "Mistral 7B (Fastest)", "description": "Uses fastest available provider for quick responses.", "speed": 10, "power": 5, "pros": "Extremely fast responses.", "cons": "Sacrifices power for speed."},
    {"id": "deepseek/deepseek-r1:free", "name": "DeepSeek R1", "description": "Powerful DeepSeek's R1 model for complex queries.", "speed": 5, "power": 8, "pros": "Excellent for detailed answers.", "cons": "Slower response time."},
    {"id": "cognitivecomputations/dolphin3.0-r1-mistral-24b:free", "name": "Dolphin 3.0 R1 Mistral 24B", "description": "Experimental 24B model with high capacity for detailed answers.", "speed": 4, "power": 8, "pros": "High capacity for complex tasks.", "cons": "Slower due to size."},
    {"id": "google/gemma-3-27b-it:free", "name": "Gemma 3 27B IT", "description": "Google's 27B model tailored for IT-related tasks with enhanced capabilities.", "speed": 3, "power": 9, "pros": "Highly powerful for complex IT queries.", "cons": "Very slow due to size."},
    {"id": "gryphe/mythomax-l2-13b:free", "name": "Mythomax L2 13B", "description": "13B model with enhanced capabilities for diverse queries.", "speed": 6, "power": 7, "pros": "Versatile across topics.", "cons": "Moderate speed."},
    {"id": "google/gemini-2.0-flash-thinking-exp-1219:free", "name": "Gemini 2.0 Flash Exp 1219", "description": "Experimental fast-thinking model for rapid responses.", "speed": 9, "power": 6, "pros": "Quick and efficient.", "cons": "Experimental stability."},
    {"id": "google/gemini-2.0-flash-thinking-exp:free", "name": "Gemini 2.0 Flash Exp", "description": "Fast-thinking model designed for quick and efficient answers.", "speed": 9, "power": 6, "pros": "Rapid responses.", "cons": "Limited depth."},
    {"id": "moonshotai/moonlight-16b-a3b-instruct:free", "name": "Moonlight 16B A3B Instruct", "description": "16B model with strong instruction-following abilities.", "speed": 5, "power": 8, "pros": "Great for instructions.", "cons": "Slower processing."},
    {"id": "nvidia/llama-3.1-nemotron-70b-instruct:free", "name": "LLaMA 3.1 Nemotron 70B", "description": "Powerful 70B model for handling complex and detailed tasks.", "speed": 2, "power": 10, "pros": "Top-tier power for complexity.", "cons": "Very slow."},
    {"id": "openchat/openchat-7b:free", "name": "OpenChat 7B", "description": "7B model optimized for open-ended conversations.", "speed": 8, "power": 5, "pros": "Good for casual chats.", "cons": "Less analytical depth."},
]

# Thread for handling AI responses asynchronously
class AIResponseThread(QThread):
    response_ready = Signal(str)
    error_occurred = Signal(str)
    finished = Signal()

    def __init__(self, messages, model):
        super().__init__()
        self.messages = messages
        self.model = model

    def run(self):
        try:
            client = OpenAI(api_key=API_KEY, base_url="https://openrouter.ai/api/v1")
            completion = client.chat.completions.create(
                model=self.model,
                messages=self.messages
            )
            response = completion.choices[0].message.content
            self.response_ready.emit(response)
        except Exception as e:
            self.error_occurred.emit(f"Oops, something went wrong: {str(e)}")
        finally:
            self.finished.emit()

# Custom dialog for model selection with colors matching ui.py
class ModelSelectionDialog(QDialog):
    def __init__(self, parent=None, current_model=None):
        super().__init__(parent)
        self.setWindowTitle("Select AI Model")
        self.resize(900, 700)
        self.current_model = current_model
        self.selected_model = None
        self.sort_criterion = "None"
        self.search_text = ""
        self.displayed_models = []
        self.setup_ui()
        self.populate_models()

    def setup_ui(self):
        self.setStyleSheet("background-color: #171923;")
        self.setContentsMargins(20, 20, 20, 20)
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(20)

        sort_layout = QHBoxLayout()
        self.sort_buttons = {}
        for criterion in ["None", "Speed", "Power"]:
            btn = QPushButton(criterion)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #21232a;
                    color: #f0f0f0;
                    border: 1px solid #555;
                    padding: 5px 10px;
                    font-size: 14pt;
                }
                QPushButton:hover {
                    background-color: #4AD2C6;
                }
            """)
            btn.clicked.connect(lambda checked, c=criterion: self.set_sort(c))
            sort_layout.addWidget(btn)
            self.sort_buttons[criterion] = btn
        main_layout.addLayout(sort_layout)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search models...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                background-color: #21232a;
                color: #f0f0f0;
                border: 1px solid #555;
                padding: 5px;
                font-size: 14pt;
            }
            QLineEdit:focus {
                border: 1px solid #38B2AC;
            }
        """)
        self.search_input.textChanged.connect(self.update_search)
        main_layout.addWidget(self.search_input)

        content_layout = QHBoxLayout()
        content_layout.setSpacing(20)

        self.model_list = QListWidget()
        self.model_list.setStyleSheet("""
            QListWidget {
                background-color: #171923;
                border: none;
            }
            QListWidget::item:selected {
                background-color: transparent;
            }
        """)
        self.model_list.setSpacing(5)
        self.model_list.itemSelectionChanged.connect(self.update_details)
        self.model_list.itemSelectionChanged.connect(self.update_ok_button)
        content_layout.addWidget(self.model_list, stretch=1)

        self.details_frame = QFrame()
        self.details_frame.setStyleSheet("background-color: #21232a; padding: 10px;")
        details_layout = QVBoxLayout(self.details_frame)
        self.details_name = QLabel("Select a model to see details")
        self.details_name.setStyleSheet("color: #f0f0f0; font-size: 24pt; font-weight: bold;")
        self.details_description = QLabel()
        self.details_description.setStyleSheet("color: #f0f0f0; font-size: 16pt;")
        self.details_description.setWordWrap(True)
        self.details_speed = QLabel()
        self.details_speed.setStyleSheet("color: #81E6D9; font-size: 16pt;")
        self.details_power = QLabel()
        self.details_power.setStyleSheet("color: #81E6D9; font-size: 16pt;")
        self.details_pros = QLabel()
        self.details_pros.setStyleSheet("color: #f0f0f0; font-size: 16pt;")
        self.details_pros.setWordWrap(True)
        self.details_cons = QLabel()
        self.details_cons.setStyleSheet("color: #f0f0f0; font-size: 16pt;")
        self.details_cons.setWordWrap(True)
        details_layout.addWidget(self.details_name)
        details_layout.addWidget(self.details_description)
        details_layout.addWidget(self.details_speed)
        details_layout.addWidget(self.details_power)
        details_layout.addWidget(self.details_pros)
        details_layout.addWidget(self.details_cons)
        content_layout.addWidget(self.details_frame, stretch=1)

        main_layout.addLayout(content_layout)

        button_layout = QHBoxLayout()
        self.ok_button = QPushButton("OK")
        self.ok_button.setStyleSheet("""
            QPushButton {
                background-color: #38B2AC;
                color: #f0f0f0;
                border: none;
                padding: 5px 10px;
                font-size: 14pt;
            }
            QPushButton:disabled {
                background-color: #555;
                color: #888888;
            }
            QPushButton:hover:!disabled {
                background-color: #4AD2C6;
            }
        """)
        self.ok_button.clicked.connect(self.confirm_selection)
        self.ok_button.setEnabled(False)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #555;
                color: #f0f0f0;
                border: none;
                padding: 5px 10px;
                font-size: 14pt;
            }
            QPushButton:hover {
                background-color: #4AD2C6;
            }
        """)
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addStretch()
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)
        main_layout.addLayout(button_layout)

    def set_sort(self, criterion):
        self.sort_criterion = criterion
        self.populate_models()
        for btn in self.sort_buttons.values():
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #21232a;
                    color: #f0f0f0;
                    border: 1px solid #555;
                    padding: 5px 10px;
                    font-size: 14pt;
                }
                QPushButton:hover {
                    background-color: #4AD2C6;
                }
            """)
        self.sort_buttons[criterion].setStyleSheet("""
            QPushButton {
                background-color: #38B2AC;
                color: #f0f0f0;
                border: 1px solid #38B2AC;
                padding: 5px 10px;
                font-size: 14pt;
            }
            QPushButton:hover {
                background-color: #4AD2C6;
            }
        """)

    def update_search(self, text):
        self.search_text = text.lower()
        self.populate_models()

    def populate_models(self):
        self.model_list.clear()
        self.displayed_models = []
        if self.sort_criterion == "None":
            sorted_models = AVAILABLE_MODELS
        elif self.sort_criterion == "Speed":
            sorted_models = sorted(AVAILABLE_MODELS, key=lambda x: x['speed'], reverse=True)
        elif self.sort_criterion == "Power":
            sorted_models = sorted(AVAILABLE_MODELS, key=lambda x: x['power'], reverse=True)

        if self.search_text:
            sorted_models = [m for m in sorted_models if self.search_text in m['name'].lower() or self.search_text in m['description'].lower()]

        for model in sorted_models:
            item = QListWidgetItem()
            widget = self.create_model_widget(model)
            item.setSizeHint(widget.sizeHint())
            self.model_list.addItem(item)
            self.model_list.setItemWidget(item, widget)
            self.displayed_models.append(model)
            if model['id'] == self.current_model:
                item.setSelected(True)

    def create_model_widget(self, model):
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: #21232a;
                border: 1px solid #555;
                padding: 10px;
            }
            QFrame:hover {
                background-color: #4AD2C6;
            }
        """)
        layout = QVBoxLayout(frame)
        name_label = QLabel(model['name'])
        name_label.setStyleSheet("color: #f0f0f0; font-size: 18pt; font-weight: bold;")
        desc_label = QLabel(model['description'])
        desc_label.setStyleSheet("color: #f0f0f0; font-size: 14pt;")
        desc_label.setWordWrap(True)
        speed_label = QLabel(f"Speed: {model['speed']}/10")
        speed_label.setStyleSheet("color: #81E6D9; font-size: 14pt;")
        power_label = QLabel(f"Power: {model['power']}/10")
        power_label.setStyleSheet("color: #81E6D9; font-size: 14pt;")
        layout.addWidget(name_label)
        layout.addWidget(desc_label)
        layout.addWidget(speed_label)
        layout.addWidget(power_label)
        return frame

    def update_details(self):
        for i in range(self.model_list.count()):
            item = self.model_list.item(i)
            widget = self.model_list.itemWidget(item)
            if item.isSelected():
                widget.setStyleSheet("""
                    QFrame {
                        background-color: #38B2AC;
                        border: 1px solid #38B2AC;
                        padding: 10px;
                    }
                """)
            else:
                widget.setStyleSheet("""
                    QFrame {
                        background-color: #21232a;
                        border: 1px solid #555;
                        padding: 10px;
                    }
                    QFrame:hover {
                        background-color: #4AD2C6;
                    }
                """)
        selected_items = self.model_list.selectedItems()
        if selected_items:
            index = self.model_list.row(selected_items[0])
            model = self.displayed_models[index]
            self.details_name.setText(model['name'])
            self.details_description.setText(model['description'])
            self.details_speed.setText(f"Speed: {model['speed']}/10")
            self.details_power.setText(f"Power: {model['power']}/10")
            self.details_pros.setText(f"Pros: {model.get('pros', 'N/A')}")
            self.details_cons.setText(f"Cons: {model.get('cons', 'N/A')}")
        else:
            self.details_name.setText("Select a model to see details")
            self.details_description.setText("")
            self.details_speed.setText("")
            self.details_power.setText("")
            self.details_pros.setText("")
            self.details_cons.setText("")

    def update_ok_button(self):
        self.ok_button.setEnabled(len(self.model_list.selectedItems()) > 0)

    def confirm_selection(self):
        selected_items = self.model_list.selectedItems()
        if selected_items:
            index = self.model_list.row(selected_items[0])
            model = self.displayed_models[index]
            self.selected_model = model['id']
            self.accept()

# Main chat widget
class ChatWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_model = MODEL_NAME
        self.current_key = None
        self.chat_history_file = "chat_history.enc"
        self.username = "user"
        self.salt = bcrypt.gensalt()
        self.password_hash = bcrypt.hashpw(b"password", self.salt)
        
        # Load prompts and creator details
        data = self.load_system_prompts()
        self.system_prompts = data["system_prompts"]
        self.creator_details = data["creator_details"]
        
        # Append creator info to each system prompt
        creator_info = f" I was created by {self.creator_details['name'].capitalize()}, a {self.creator_details['status']}."
        for mode in self.system_prompts:
            self.system_prompts[mode] += creator_info
        
        self.current_mode = "casual"  # Default mode
        self.chat_history = []  # Initialize chat history
        self.uploaded_file_content = None  # For file upload
        self.setup_ui()
        
    def load_system_prompts(self):
        """Load system prompts and creator details from prompt.json."""
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            prompt_path = os.path.join(script_dir, "assets", "prompt.json")
            with open(prompt_path, "r") as f:
                data = json.load(f)
                return data
        except Exception as e:
            logger.error(f"Failed to load system prompts: {str(e)}")
            return {
                "system_prompts": {
                    "casual": "Hey! I'm Neurix, your chill AI buddy for cybersecurity and hacking.",
                    "admin": "I am Neurix, a general-purpose AI ready to assist with any topic.",
                    "code": "Hey! I'm Neurix, your coding assistant for various programming languages."
                },
                "creator_details": {
                    "name": "joseph",
                    "status": "he is living in chennai and he made me for a collage project"
                }
            }
        
    def setup_ui(self):
        """Set up the UI for the chat widget."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Current model display and change button
        model_layout = QHBoxLayout()
        self.current_model_label = QLabel(f"Current Model: {self.get_model_name(self.selected_model)}")
        self.current_model_label.setFont(QFont("Arial", 20))
        change_model_btn = QPushButton("Change Model")
        change_model_btn.setFont(QFont("Arial", 20))
        change_model_btn.clicked.connect(self.open_model_selection)
        model_layout.addWidget(self.current_model_label)
        model_layout.addWidget(change_model_btn)
        layout.addLayout(model_layout)
        
        # Chat display
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setFont(QFont("Arial", 18))
        self.chat_display.setStyleSheet("QTextEdit { font-size: 18pt; line-height: 1.5; padding: 10px; background-color: #1A1A1A; }")
        layout.addWidget(self.chat_display)
        
        # Upload status label
        self.upload_status_label = QLabel()
        self.upload_status_label.setFont(QFont("Arial", 16))
        layout.addWidget(self.upload_status_label)
        
        # Message input and buttons
        self.message_input = QLineEdit()
        self.message_input.setPlaceholderText("Type your message here...")
        self.message_input.setMinimumHeight(40)
        self.message_input.setFont(QFont("Arial", 24))
        self.message_input.returnPressed.connect(self.send_message)
        self.upload_button = QPushButton("Upload File")
        self.upload_button.setFont(QFont("Arial", 20))
        self.upload_button.clicked.connect(self.upload_file)
        self.send_button = QPushButton("Send")
        self.send_button.setFixedWidth(80)
        self.send_button.setMinimumHeight(40)
        self.send_button.setFont(QFont("Arial", 20))
        self.clear_button = QPushButton("Clear")
        self.clear_button.setFixedWidth(80)
        self.clear_button.setMinimumHeight(40)
        self.clear_button.setFont(QFont("Arial", 20))
        self.clear_button.clicked.connect(self.clear_chat)
        input_layout = QHBoxLayout()
        input_layout.addWidget(self.message_input)
        input_layout.addWidget(self.upload_button)
        input_layout.addWidget(self.send_button)
        input_layout.addWidget(self.clear_button)
        layout.addLayout(input_layout)
        
        # Initial message
        self.add_message("Neurix", "Hey there! I’m Neurix, your cybersecurity buddy. Ask me anything about cybersecurity or ethical hacking!")
        
        self.message_input.setFocus()
        
    def get_model_name(self, model_id):
        """Get the display name of a model based on its ID."""
        for model in AVAILABLE_MODELS:
            if model['id'] == model_id:
                return model['name']
        return "Unknown"
        
    def open_model_selection(self):
        """Open the model selection dialog."""
        dialog = ModelSelectionDialog(self, self.selected_model)
        if dialog.exec_() == QDialog.Accepted:
            new_model_id = dialog.selected_model
            if new_model_id and new_model_id != self.selected_model:
                self.selected_model = new_model_id
                model_name = self.get_model_name(new_model_id)
                self.current_model_label.setText(f"Current Model: {model_name}")
                self.add_message("System", f"Switched to {model_name}")
        
    def parse_message(self, text):
        """Parse sender and message from text."""
        if ": " in text:
            sender, message = text.split(": ", 1)
            if sender in ["You", "Neurix", "System"]:
                return sender, message
        return "", text
        
    def add_message(self, sender, message):
        """Add a message to the chat display."""
        if sender == "You":
            self.chat_display.setTextColor(QColor("light blue"))
            self.chat_display.append("You:")
            message_html = f'<span style="color:white;">{message}</span>'
            self.chat_display.insertHtml(message_html)
        elif sender == "Neurix":
            self.chat_display.setTextColor(QColor("green"))
            self.chat_display.append("Neurix:")
            message_html = f'<span style="color:white;">{message}</span>'
            self.chat_display.insertHtml(message_html)
        elif sender == "System":
            self.chat_display.setTextColor(QColor("purple"))
            self.chat_display.append("System:")
            message_html = f'<span style="color:purple;">{message}</span>'
            self.chat_display.insertHtml(message_html)
        else:
            self.chat_display.insertHtml(message)
        self.chat_display.append("")
        self.chat_display.ensureCursorVisible()
        
    def upload_file(self):
        """Handle file upload."""
        file_path, _ = QFileDialog.getOpenFileName(self, "Select File", "", "Text Files (*.txt *.log *.md);;All Files (*)")
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if len(content) > 10000:
                        self.upload_status_label.setText("File too large (max 10,000 characters)")
                        return
                    self.uploaded_file_content = content
                    file_name = os.path.basename(file_path)
                    self.upload_status_label.setText(f"File uploaded: {file_name} (will be sent with next message)")
            except Exception as e:
                self.upload_status_label.setText(f"Error reading file: {str(e)}")
        
    def send_message(self):
        """Handle sending a message and mode switching."""
        user_message = self.message_input.text().strip()
        if not user_message:
            return
        self.message_input.clear()
        
        if user_message.lower() == "/show":
            mode_message = f"Currently in {self.current_mode} mode."
            if self.current_mode == "casual":
                mode_message += " Type /admin to switch to general-purpose AI mode or /code to switch to coding mode."
            elif self.current_mode == "admin":
                mode_message += " Type /casual to switch to cybersecurity mode or /code to switch to coding mode."
            elif self.current_mode == "code":
                mode_message += " Type /casual to switch to cybersecurity mode or /admin to switch to general-purpose AI mode."
            self.add_message("System", mode_message)
            return
        elif user_message.lower() == "/admin":
            self.current_mode = "admin"
            self.add_message("System", "Switched to admin mode. I am now a general-purpose AI ready to assist with any topic.")
            return
        elif user_message.lower() == "/casual":
            self.current_mode = "casual"
            self.add_message("System", "Switched back to casual mode, buddy! Cybersecurity’s my jam again.")
            return
        elif user_message.lower() == "/code":
            self.current_mode = "code"
            self.add_message("System", "Switched to coding mode. Ready to help with your programming questions!")
            return
        elif user_message.startswith("/"):
            self.add_message("System", "Unknown command, buddy!")
        else:
            if self.uploaded_file_content:
                display_message = f"{user_message} (with uploaded file)"
                full_message = f"I have uploaded a file with the following content:\n{self.uploaded_file_content}\n\n{user_message}"
                self.add_message("You", display_message)
                self.chat_history.append({"role": "user", "content": full_message})
                self.uploaded_file_content = None
                self.upload_status_label.clear()
            else:
                self.add_message("You", user_message)
                self.chat_history.append({"role": "user", "content": user_message})
            self.add_message("Neurix", "Thinking...")
            self.message_input.setEnabled(False)
            self.send_button.setEnabled(False)
            messages = [{"role": "system", "content": self.system_prompts[self.current_mode]}] + self.chat_history
            self.response_thread = AIResponseThread(messages, self.selected_model)
            self.response_thread.response_ready.connect(self.handle_response)
            self.response_thread.error_occurred.connect(self.handle_error)
            self.response_thread.finished.connect(self.enable_input)
            self.response_thread.start()
        
    def clean_response(self, response):
        """Format the AI response with markdown if available, otherwise clean up markdown symbols including headers."""
        if MARKDOWN_AVAILABLE:
            html = markdown.markdown(response)
        else:
            import re
            # Remove markdown headers: lines starting with one or more '#' followed by a space
            response = re.sub(r'^#+\s+', '', response, flags=re.MULTILINE)
            # Remove **bold**
            response = re.sub(r'\*\*(.*?)\*\*', r'\1', response)
            # Remove *italics*
            response = re.sub(r'\*(.*?)\*', r'\1', response)
            # Remove _italics_
            response = re.sub(r'_(.*?)_', r'\1', response)
            # Remove `inline code`
            response = re.sub(r'`(.*?)`', r'\1', response)
            # Replace newlines with <br> for proper line breaks
            html = response.replace('\n', '<br>')
        return f'<div style="font-size: 18pt; margin-bottom: 5px; text-align: left;">{html}</div>'
    
    def handle_response(self, response):
        """Handle the AI's response."""
        self.remove_last_block()
        formatted_response = self.clean_response(response)
        self.chat_history.append({"role": "assistant", "content": response})
        self.chat_display.setTextColor(QColor("green"))
        self.chat_display.append("Neurix:")
        message_html = f'<span style="color:white;">{formatted_response}</span>'
        self.chat_display.insertHtml(message_html)
        self.chat_display.append("")
        self.chat_display.ensureCursorVisible()

    def handle_error(self, error_message):
        """Handle errors from the AI thread."""
        self.remove_last_block()
        self.add_message("Neurix", error_message)
        
    def enable_input(self):
        """Re-enable input after AI response."""
        self.message_input.setEnabled(True)
        self.send_button.setEnabled(True)
        self.message_input.setFocus()
        
    def clear_chat(self):
        """Clear the chat and reset initial messages."""
        self.chat_display.clear()
        self.chat_history = []
        self.add_message("Neurix", "Hey there! I’m Neurix, your cybersecurity buddy. Ask me anything about cybersecurity or ethical hacking!")

    def remove_last_block(self):
        """Remove the last block of text (e.g., 'Thinking...')."""
        doc = self.chat_display.document()
        if doc.blockCount() > 0:
            cursor = QTextCursor(doc.findBlockByNumber(doc.blockCount() - 1))
            cursor.select(QTextCursor.BlockUnderCursor)
            cursor.removeSelectedText()

def create_main_content(parent):
    """Create the main content container."""
    container = QWidget(parent)
    layout = QVBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    
    if not OPENAI_INSTALLED:
        error_frame = QWidget()
        error_layout = QVBoxLayout(error_frame)
        error_msg = QLabel("Error: OpenAI package not installed. Run 'pip install openai' and restart.")
        error_msg.setWordWrap(True)
        error_msg.setFont(QFont("Arial", 20))
        error_msg.setStyleSheet("color: red;")
        error_layout.addWidget(error_msg)
        layout.addWidget(error_frame)
        return container
    
    chat_widget = ChatWidget(container)
    layout.addWidget(chat_widget)
    return container