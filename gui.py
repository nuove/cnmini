import sys
import threading
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QLineEdit, QLabel, QScrollArea, QListWidget, QListWidgetItem,
    QPushButton, QInputDialog, QMenuBar, QAction
    )
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QColor, QTextCharFormat, QIcon

from client import ChatClient
from message import Message, MessageValidator

class IRCClient(QMainWindow):
    def __init__(self, server_ip):
        super().__init__()
        self.server_ip = server_ip
        self.client = None
        self.username = None
        self.running = False

        # Initialize user state BEFORE UI
        self.user_colors = {}
        self.available_colors = [
            "#ff7b7b", "#58a6ff", "#faa356", "#bd93f9", "#43b581", "#f04747", "#7289da"
        ]
        default_admin = "Admin"
        self.user_colors[default_admin] = "#ff0000"
        self.current_user = default_admin

        self.setWindowTitle("ChudChat")
        self.setGeometry(100, 100, 1000, 700)
        self.setWindowIcon(QIcon("./chud.png"))  # Set your icon path here

        # Add menu bar with Settings
        menu_bar = QMenuBar(self)
        settings_menu = menu_bar.addMenu("Settings")
        change_ip_action = QAction("Change Server IP", self)
        change_ip_action.triggered.connect(self.change_server_ip)
        settings_menu.addAction(change_ip_action)
        self.setMenuBar(menu_bar)

        # Main layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Left sidebar - Channel list
        left_sidebar = QWidget()
        left_sidebar.setFixedWidth(220)
        left_sidebar.setStyleSheet("background-color: #2f3136;")
        left_layout = QVBoxLayout(left_sidebar)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)

        # Channel header with add button
        header_container = QWidget()
        header_layout = QHBoxLayout(header_container)
        header_layout.setContentsMargins(14, 14, 14, 8)
        header_layout.setSpacing(8)

        channel_header = QLabel("CHANNELS")
        channel_header.setStyleSheet("""
            QLabel {
                color: #8e9297;
                font-weight: bold;
                font-size: 12px;
                text-transform: uppercase;
            }
        """)
        header_layout.addWidget(channel_header)

        add_channel_btn = QPushButton("+")
        add_channel_btn.setStyleSheet("""
            QPushButton {
                background-color: #2f3136;
                color: #ffffff;
                border: none;
                border-radius: 8px;
                padding: 8px;
                font-weight: bold;
                text-align: center;
            }

            QPushButton:hover {
                background-color: #7289da;
            }

            QPushButton:pressed {
                background-color: #4752c4;
            }
        """)
        add_channel_btn.clicked.connect(self.add_channel)
        header_layout.addWidget(add_channel_btn)
        header_layout.addStretch()
        left_layout.addWidget(header_container)

        # Add a widget and layout to hold channel buttons
        self.channel_buttons_widget = QWidget()
        self.channel_buttons_layout = QVBoxLayout(self.channel_buttons_widget)
        self.channel_buttons_layout.setContentsMargins(4, 4, 4, 4)  # Reduced margins
        self.channel_buttons_layout.setSpacing(0)  # No extra spacing between buttons
        self.channel_buttons_layout.setAlignment(Qt.AlignTop)  # <-- Add this line
        left_layout.addWidget(self.channel_buttons_widget, stretch=1)

        # Store channel buttons for easy access
        self.channel_buttons = {}

        # Add default #general channel button
        self.add_channel_button("#general")
        main_layout.addWidget(left_sidebar)

        # Chat area
        chat_area = QWidget()
        chat_layout = QVBoxLayout(chat_area)
        chat_layout.setContentsMargins(0, 0, 0, 0)
        chat_layout.setSpacing(0)

        # Channel header
        self.channel_header = QLabel("#general")
        self.channel_header.setStyleSheet("""
            QLabel {
                background-color: #36393f;
                color: #ff9955;
                padding: 16px;
                border-bottom: 1px solid #292b2f;
                font-weight: bold;
                font-size: 16px;
            }
        """)
        chat_layout.addWidget(self.channel_header)

        # Messages area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("background-color: #36393f; border: none;")

        self.messages_container = QWidget()
        self.messages_container.setStyleSheet("background-color: #36393f;")
        self.messages_layout = QVBoxLayout(self.messages_container)
        self.messages_layout.setContentsMargins(16, 16, 16, 16)
        self.messages_layout.setSpacing(8)
        self.messages_layout.addStretch()

        scroll_area.setWidget(self.messages_container)
        chat_layout.addWidget(scroll_area, stretch=1)

        # Message input
        self.message_input = QLineEdit()
        self.message_input.setPlaceholderText(f"Message as {self.current_user}")
        self.message_input.setStyleSheet("""
            QLineEdit {
                background-color: #484b52;
                color: #dcddde;
                border: 2px solid #484b52;
                border-radius: 8px;
                padding: 12px 16px;
                margin: 16px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 2px solid #5865f2;
            }
        """)
        self.message_input.returnPressed.connect(self.send_message)
        chat_layout.addWidget(self.message_input)

        main_layout.addWidget(chat_area, stretch=1)

        # Right sidebar - User lists divided by role
        right_sidebar = QWidget()
        right_sidebar.setFixedWidth(220)
        right_sidebar.setStyleSheet("background-color: #2f3136;")
        right_layout = QVBoxLayout(right_sidebar)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        # Admin section header
        admin_header = QLabel("ADMINS")
        admin_header.setStyleSheet("""
            QLabel {
                color: #8e9297;
                font-weight: bold;
                padding: 14px 16px 8px;
                font-size: 12px;
                text-transform: uppercase;
            }
        """)
        right_layout.addWidget(admin_header)

        self.admin_list = QListWidget()
        self.admin_list.setStyleSheet("""
            QListWidget {
                background-color: transparent;
                color: #dcddde;
                border: none;
                font-size: 14px;
                padding: 2px 0;
                margin-left: 8px;
                margin-right: 8px;
            }
            QListWidget::item {
                padding: 8px 16px;
            }
            QListWidget::item:hover {
                background-color: #3a3d44;
            }
        """)
        self.admin_list.setSelectionMode(QListWidget.NoSelection)
        admin_item = QListWidgetItem(default_admin)
        admin_item.setToolTip("Role: Admin")
        self.admin_list.addItem(admin_item)
        right_layout.addWidget(self.admin_list, stretch=0)

        # Regular users section header
        user_header = QLabel("USERS")
        user_header.setStyleSheet("""
            QLabel {
                color: #8e9297;
                font-weight: bold;
                padding: 14px 16px 8px;
                font-size: 12px;
                text-transform: uppercase;
            }
        """)
        right_layout.addWidget(user_header)

        self.user_list = QListWidget()
        self.user_list.setStyleSheet("""
            QListWidget {
                background-color: transparent;
                color: #dcddde;
                border: none;
                font-size: 14px;
                padding: 2px 0;
                margin-left: 8px;
                margin-right: 8px;
            }
            QListWidget::item {
                padding: 8px 16px;
            }
            QListWidget::item:hover {
                background-color: #3a3d44;
            }
        """)
        self.user_list.setSelectionMode(QListWidget.NoSelection)
        right_layout.addWidget(self.user_list, stretch=1)

        self.setStyleSheet("""
            QToolTip {
                background-color : black;
                color : white;
                border black solid 1px;
                }
        """)

        self.adjust_admin_list_height()  # Adjust height after adding the item
        main_layout.addWidget(right_sidebar)

        # Now call init_connection AFTER widgets are created
        self.init_connection()

    def init_connection(self):
        # Connect to server
        self.client = ChatClient(server_host=self.server_ip)
        try:
            self.client.socket.connect((self.server_ip, self.client.server_port))
        except Exception as e:
            QInputDialog.getText(self, "Connection Error", f"Failed to connect: {e}")
            sys.exit(1)
        
        # Prompt for username with validation
        while True:
            username, ok = QInputDialog.getText(self, "Username", "Enter your username (3-20 chars, alphanumeric, -_):")
            if not ok:
                sys.exit(0)
            if MessageValidator.validate_username(username):
                self.username = username
                # Add the user to the user list widget
                self.add_user(username=username)
                break            

        # Send username to server
        self.running = True
        self.client.running = True
        self.client.username = self.username
        self.client.send_message(Message(
            from_user=self.username,
            to_channel='',
            body=self.username
        ))

        # Automatically join "general" channel
        self.client.current_channel = "general"
        self.client.send_message(Message(
            from_user=self.username,
            to_channel="general",
            body="/join general"
        ))

        # Start background thread to receive messages
        self.receiver_thread = threading.Thread(target=self.receive_messages, daemon=True)
        self.receiver_thread.start()

    def receive_messages(self):
        while self.running:
            try:
                data = self.client.socket.recv(4096)
                if not data:
                    break
                message = Message.from_json(data.decode('utf-8'))
                if message:
                    if message.body.startswith('USERLIST:'):
                        users = message.body[len('USERLIST:'):].split(',')
                        QTimer.singleShot(0, lambda: self.update_user_list(users))
                    else:
                        QTimer.singleShot(0, lambda: self.add_message(message.from_user, message.body))
            except Exception:
                break

    def update_user_list(self, users):
        self.user_list.clear()
        for username in users:
            if username:
                user_item = QListWidgetItem(username)
                user_item.setToolTip("Role: User")
                self.user_list.addItem(user_item)

    def display_message(self, message):
        # Ensure GUI update happens in the main thread
        QTimer.singleShot(0, lambda: self.add_message(message.from_user, message.body))

    def add_channel_button(self, channel_name):
        """Add a channel as a button in the channel buttons layout."""
        if channel_name in self.channel_buttons:
            return
        btn = QPushButton(channel_name)
        btn.setCheckable(True)
        btn.setStyleSheet("""
            QPushButton {
                background-color: #36393f;
                color: #ff9955;
                border: none;
                border-radius: 8px;
                padding: 6px 14px;
                font-weight: bold;
                text-align: left;
            }
            QPushButton:checked {
                background-color: #5865f2;
                color: #fff;
            }
        """)
        btn.clicked.connect(lambda checked, name=channel_name: self.switch_channel(name))
        self.channel_buttons_layout.addWidget(btn)
        self.channel_buttons[channel_name] = btn
        # Set #general as checked by default
        if channel_name == "#general":
            btn.setChecked(True)

    def add_channel(self):
        channel_name, ok = QInputDialog.getText(self, "Add Channel", "Enter channel name:")
        if ok and channel_name:
            if not channel_name.startswith("#"):
                channel_name = "#" + channel_name
            if channel_name not in self.channel_buttons:
                self.add_channel_button(channel_name)
            # Switch to the new channel
            self.switch_channel(channel_name)

    def switch_channel(self, channel_name):
        """Switch to the selected channel and update the header label."""
        # Uncheck all buttons except the selected one
        for name, btn in self.channel_buttons.items():
            btn.setChecked(name == channel_name)
        # Update the channel header label
        self.channel_header.setText(channel_name)
        # Switch channel in client if needed
        if self.client.current_channel != channel_name:
            self.client.current_channel = channel_name
            self.client.send_message(Message(
                from_user=self.username,
                to_channel=channel_name,
                body=f"/join {channel_name}"
            ))

    def add_message(self, username, message, color=None):
        """Add a message to the chat area with color attributes."""
        if not color:
            color = self.user_colors.get(username, "#ffffff")  # Default to white if no color is assigned

        message_widget = QTextEdit()
        message_widget.setReadOnly(True)
        message_widget.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        message_widget.setStyleSheet("""
            QTextEdit {
                background-color: transparent;
                border: none;
                color: #dcddde;
                font-size: 14px;
                padding: 0;
            }
        """)

        cursor = message_widget.textCursor()

        # Timestamp
        timestamp_format = QTextCharFormat()
        timestamp_format.setForeground(QColor("#72767d"))
        cursor.insertText("[10:30] ", timestamp_format)

        # Username
        username_format = QTextCharFormat()
        username_format.setForeground(QColor(color))
        username_format.setFontWeight(QFont.Bold)
        cursor.insertText(username, username_format)

        # Message
        message_format = QTextCharFormat()
        message_format.setForeground(QColor("#dcddde"))
        cursor.insertText(": " + message, message_format)

        message_widget.setFixedHeight(int(message_widget.document().size().height() + 5))
        self.messages_layout.insertWidget(self.messages_layout.count() - 1, message_widget)

    def send_message(self):
        message_text = self.message_input.text()
        if message_text:
            msg = Message(
                from_user=self.username,  # Always use the logged-in username
                to_channel=self.client.current_channel,  # Always use the current channel
                body=message_text
            )
            self.client.send_message(msg)  # This sends the message to the server in the correct format
            self.add_message(self.username, message_text)
            self.message_input.clear()

    def adjust_admin_list_height(self):
        total_height = 0
        for i in range(self.admin_list.count()):
            total_height += self.admin_list.sizeHintForRow(i)
        total_height += 2 * self.admin_list.frameWidth()  # Add frame width
        self.admin_list.setFixedHeight(total_height)

    def add_user(self, username=None):
        """Add a user to the user list (default role: User, green color)."""
        if username is None:
            username, ok = QInputDialog.getText(self, "Add User", "Enter username:")
            if not ok or not username:
                return
        self.user_colors[username] = "#00ff00"  # Green
        user_item = QListWidgetItem(username)
        user_item.setToolTip("Role: User")
        self.user_list.addItem(user_item)

    def assign_colors_to_existing_users(self):
        """Assign red to admins and green to users."""
        # Assign red to admin users
        for i in range(self.admin_list.count()):
            username = self.admin_list.item(i).text()
            self.user_colors[username] = "#ff0000"  # Red
            self.admin_list.item(i).setToolTip("Role: Admin")

        # Assign green to regular users
        for i in range(self.user_list.count()):
            username = self.user_list.item(i).text()
            self.user_colors[username] = "#00ff00"  # Green
            self.user_list.item(i).setToolTip("Role: User")

    def change_server_ip(self):
        new_ip, ok = QInputDialog.getText(self, "Change Server IP", "Enter new server IP:")
        if ok and new_ip:
            self.server_ip = new_ip
            # Here you should add logic to reconnect to the new server IP
            # For now, just show a message or print
            print(f"Changed server IP to: {self.server_ip}")

# --- Startup dialog logic ---
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Set dark palette
    palette = app.palette()
    palette.setColor(palette.Window, QColor(54, 57, 63))
    palette.setColor(palette.WindowText, Qt.white)
    palette.setColor(palette.Base, QColor(72, 75, 82))
    palette.setColor(palette.Text, Qt.white)
    app.setPalette(palette)

    # Startup dialog for server IP
    server_ip, ok = QInputDialog.getText(None, "Server IP", "Enter the server IP address:")
    if not ok or not server_ip:
        sys.exit(0)

    window = IRCClient(server_ip)
    window.show()
    sys.exit(app.exec_())