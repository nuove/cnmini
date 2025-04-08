import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QTextEdit, QLineEdit, QLabel, QScrollArea, QListWidget, QListWidgetItem,
                             QPushButton, QInputDialog, QDialog, QRadioButton, QToolTip)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor, QTextCharFormat, QIcon

class IRCClient(QMainWindow):
    def __init__(self):
        super().__init__()
        self.user_colors = {}  # Dictionary to store username-to-color mapping
        self.available_colors = [
            "#ff7b7b", "#58a6ff", "#faa356", "#bd93f9", "#43b581", "#f04747", "#7289da"
        ]  # Predefined list of colors

        # Add a default admin user
        default_admin = "Admin"
        self.user_colors[default_admin] = "#ff0000"  # Red for admin
        self.current_user = default_admin  # Start as the default admin

        # Set up the UI
        self.setWindowTitle("ChudChat")
        self.setGeometry(100, 100, 1000, 700)
        self.setWindowIcon(QIcon("./chud.png"))  # Set your icon path here

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

        self.channel_list = QListWidget()
        self.channel_list.setStyleSheet("""
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
            QListWidget::item:selected {
                background-color: #4f545c;
            }
        """)
        left_layout.addWidget(self.channel_list, stretch=1)

        # Add sample channels
        self.channel_list.addItems(["#general"])
        self.channel_list.setCurrentRow(0)

        main_layout.addWidget(left_sidebar)

        # Chat area
        chat_area = QWidget()
        chat_layout = QVBoxLayout(chat_area)
        chat_layout.setContentsMargins(0, 0, 0, 0)
        chat_layout.setSpacing(0)

        # Channel header
        self.channel_header = QLabel("General")
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

        # Add user button
        add_user_btn = QPushButton("Add User")
        add_user_btn.setStyleSheet("""
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
        add_user_btn.clicked.connect(self.add_user_dialog)
        right_layout.addWidget(add_user_btn)

        # Add switch user button
        switch_user_btn = QPushButton("Switch User")
        switch_user_btn.setStyleSheet("""
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
        switch_user_btn.clicked.connect(self.switch_user_dialog)
        right_layout.addWidget(switch_user_btn)

        main_layout.addWidget(right_sidebar)

    def add_channel(self):
        channel_name, ok = QInputDialog.getText(self, "Add Channel", "Enter channel name:")
        if ok and channel_name:
            # Ensure channel name starts with '#' 
            if not channel_name.startswith("#"):
                channel_name = "#" + channel_name
            # Add the channel to the list if it doesn't exist already
            existing_channels = [self.channel_list.item(i).text() for i in range(self.channel_list.count())]
            if channel_name not in existing_channels:
                self.channel_list.addItem(channel_name)

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
        message = self.message_input.text()
        if message:
            self.add_message(self.current_user, message, self.user_colors.get(self.current_user, "#ffffff"))
            self.message_input.clear()

    def adjust_admin_list_height(self):
        total_height = 0
        for i in range(self.admin_list.count()):
            total_height += self.admin_list.sizeHintForRow(i)
        total_height += 2 * self.admin_list.frameWidth()  # Add frame width
        self.admin_list.setFixedHeight(total_height)

    def add_user_dialog(self):
        """Open a dialog to add a user with a role."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Add User")
        dialog.setFixedSize(300, 200)

        layout = QVBoxLayout(dialog)

        # Username input
        username_label = QLabel("Enter username:")
        layout.addWidget(username_label)

        username_input = QLineEdit()
        layout.addWidget(username_input)

        # Role selection
        role_label = QLabel("Select role:")
        layout.addWidget(role_label)

        role_admin = QRadioButton("Admin")
        role_user = QRadioButton("User")
        role_user.setChecked(True)  # Default to "User"

        role_layout = QHBoxLayout()
        role_layout.addWidget(role_admin)
        role_layout.addWidget(role_user)
        layout.addLayout(role_layout)

        # Buttons
        button_layout = QHBoxLayout()
        add_button = QPushButton("Add")
        cancel_button = QPushButton("Cancel")
        button_layout.addWidget(add_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)

        # Button actions
        def add_user():
            username = username_input.text().strip()
            if username:
                if role_admin.isChecked():
                    # Assign red color to admins
                    self.user_colors[username] = "#ff0000"  # Red
                    admin_item = QListWidgetItem(username)
                    admin_item.setToolTip("Role: Admin")
                    self.admin_list.addItem(admin_item)
                    self.adjust_admin_list_height()
                elif role_user.isChecked():
                    # Assign green color to users
                    self.user_colors[username] = "#00ff00"  # Green
                    user_item = QListWidgetItem(username)
                    user_item.setToolTip("Role: User")
                    self.user_list.addItem(user_item)
                dialog.accept()

        add_button.clicked.connect(add_user)
        cancel_button.clicked.connect(dialog.reject)

        dialog.exec_()

    def switch_user_dialog(self):
        """Open a dialog to switch the active user."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Switch User")
        dialog.setFixedSize(300, 200)

        layout = QVBoxLayout(dialog)

        # User selection label
        user_label = QLabel("Select a user:")
        layout.addWidget(user_label)

        # User list
        user_list_widget = QListWidget()
        for i in range(self.user_list.count()):
            user_list_widget.addItem(self.user_list.item(i).text())
        for i in range(self.admin_list.count()):
            user_list_widget.addItem(self.admin_list.item(i).text())
        layout.addWidget(user_list_widget)

        # Buttons
        button_layout = QHBoxLayout()
        switch_button = QPushButton("Switch")
        cancel_button = QPushButton("Cancel")
        button_layout.addWidget(switch_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)

        # Button actions
        def switch_user():
            selected_user = user_list_widget.currentItem()
            if selected_user:
                self.current_user = selected_user.text()
                self.message_input.setPlaceholderText(f"Message as {self.current_user}")
                self.message_input.setStyleSheet(f"""
                    QLineEdit {{
                        background-color: #484b52;
                        color: {self.user_colors.get(self.current_user, "#ffffff")};
                        border: 2px solid #484b52;
                        border-radius: 8px;
                        padding: 12px 16px;
                        margin: 16px;
                        font-size: 14px;
                    }}
                    QLineEdit:focus {{
                        border: 2px solid #5865f2;
                    }}
                """)
                dialog.accept()

        switch_button.clicked.connect(switch_user)
        cancel_button.clicked.connect(dialog.reject)

        dialog.exec_()

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

    window = IRCClient()
    window.show()
    sys.exit(app.exec_())