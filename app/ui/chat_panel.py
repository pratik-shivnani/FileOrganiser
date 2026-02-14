from datetime import datetime

from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
    QScrollArea, QLabel, QFrame, QSizePolicy,
)
from PyQt6.QtGui import QFont


class ChatBubble(QFrame):
    def __init__(self, text: str, is_user: bool, timestamp: str = "", parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.NoFrame)

        outer = QHBoxLayout(self)
        outer.setContentsMargins(8, 2, 8, 2)

        if is_user:
            outer.addStretch()

        bubble = QFrame()
        bubble.setMaximumWidth(500)
        bubble.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)

        if is_user:
            bubble.setStyleSheet("""
                QFrame {
                    background-color: #e3f2fd;
                    border: 1px solid #90caf9;
                    border-radius: 12px;
                    padding: 8px 12px;
                }
            """)
        else:
            bubble.setStyleSheet("""
                QFrame {
                    background-color: #f5f5f5;
                    border: 1px solid #e0e0e0;
                    border-radius: 12px;
                    padding: 8px 12px;
                }
            """)

        bubble_layout = QVBoxLayout(bubble)
        bubble_layout.setContentsMargins(0, 0, 0, 0)
        bubble_layout.setSpacing(2)

        sender_label = QLabel("You" if is_user else "Assistant")
        sender_font = QFont()
        sender_font.setPointSize(9)
        sender_font.setBold(True)
        sender_label.setFont(sender_font)
        sender_label.setStyleSheet("color: #555; border: none; background: transparent;")
        bubble_layout.addWidget(sender_label)

        text_label = QLabel(text)
        text_label.setWordWrap(True)
        text_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        text_label.setTextFormat(Qt.TextFormat.RichText)
        text_font = QFont()
        text_font.setPointSize(11)
        text_label.setFont(text_font)
        text_label.setStyleSheet("color: #1a1a1a; border: none; background: transparent;")
        bubble_layout.addWidget(text_label)

        if timestamp:
            time_label = QLabel(timestamp)
            time_font = QFont()
            time_font.setPointSize(8)
            time_label.setFont(time_font)
            time_label.setStyleSheet("color: #999; border: none; background: transparent;")
            bubble_layout.addWidget(time_label)

        outer.addWidget(bubble)

        if not is_user:
            outer.addStretch()


class ChatPanel(QWidget):
    query_submitted = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QFrame()
        header.setStyleSheet("""
            QFrame {
                background-color: #fafafa;
                border-bottom: 1px solid #e0e0e0;
            }
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 6, 12, 6)

        title = QLabel("AI Assistant")
        title_font = QFont()
        title_font.setPointSize(11)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setStyleSheet("color: #333; border: none; background: transparent;")
        header_layout.addWidget(title)

        header_layout.addStretch()

        self._clear_btn = QPushButton("Clear")
        self._clear_btn.setFixedHeight(24)
        self._clear_btn.setStyleSheet("""
            QPushButton {
                background: transparent; border: 1px solid #ccc;
                border-radius: 4px; padding: 2px 10px;
                color: #666; font-size: 11px;
            }
            QPushButton:hover { background: #eee; }
        """)
        self._clear_btn.clicked.connect(self._clear_chat)
        header_layout.addWidget(self._clear_btn)

        layout.addWidget(header)

        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll_area.setStyleSheet("""
            QScrollArea { background-color: #ffffff; border: none; }
        """)

        self._messages_widget = QWidget()
        self._messages_widget.setStyleSheet("background-color: #ffffff;")
        self._messages_layout = QVBoxLayout(self._messages_widget)
        self._messages_layout.setContentsMargins(4, 8, 4, 8)
        self._messages_layout.setSpacing(6)
        self._messages_layout.addStretch()

        self._scroll_area.setWidget(self._messages_widget)
        layout.addWidget(self._scroll_area)

        input_frame = QFrame()
        input_frame.setStyleSheet("""
            QFrame {
                background-color: #fafafa;
                border-top: 1px solid #e0e0e0;
            }
        """)
        input_layout = QHBoxLayout(input_frame)
        input_layout.setContentsMargins(8, 6, 8, 6)
        input_layout.setSpacing(6)

        self._input = QLineEdit()
        self._input.setPlaceholderText("Type a message... e.g. 'find all PDFs' or 'go to Downloads'")
        self._input.setMinimumHeight(34)
        input_font = QFont()
        input_font.setPointSize(11)
        self._input.setFont(input_font)
        self._input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #ccc;
                border-radius: 8px;
                padding: 4px 12px;
                background: #ffffff;
                color: #1a1a1a;
            }
            QLineEdit:focus {
                border-color: #2196F3;
            }
        """)
        self._input.returnPressed.connect(self._on_submit)
        input_layout.addWidget(self._input)

        self._send_btn = QPushButton("Send")
        self._send_btn.setMinimumHeight(34)
        self._send_btn.setStyleSheet("""
            QPushButton {
                background: #2196F3; color: white;
                border: none; border-radius: 8px;
                padding: 4px 18px; font-weight: bold; font-size: 12px;
            }
            QPushButton:hover { background: #1976D2; }
            QPushButton:pressed { background: #0D47A1; }
            QPushButton:disabled { background: #bbb; }
        """)
        self._send_btn.clicked.connect(self._on_submit)
        input_layout.addWidget(self._send_btn)

        layout.addWidget(input_frame)

        self.add_assistant_message(
            "Hello! I'm your file management assistant. I can help you:\n"
            "- <b>Navigate</b> — \"go to Downloads\" or \"open Documents/Projects\"\n"
            "- <b>Search</b> — \"find all PDFs larger than 10MB\"\n"
            "- <b>Move/Copy</b> — \"move screenshots from Downloads to Pictures\"\n"
            "- <b>Delete</b> — \"delete temp files older than 30 days\"\n"
            "- <b>Tag/Star</b> — \"star all Python files\" or \"tag invoices as finance\"\n"
            "- <b>Create folders</b> — \"create a folder called Archives in Documents\"\n\n"
            "Make sure to index folders first for search to work!"
        )

    def _on_submit(self):
        text = self._input.text().strip()
        if text:
            self.add_user_message(text)
            self._input.clear()
            self.query_submitted.emit(text)

    def add_user_message(self, text: str):
        ts = datetime.now().strftime("%H:%M")
        bubble = ChatBubble(text, is_user=True, timestamp=ts)
        self._messages_layout.insertWidget(self._messages_layout.count() - 1, bubble)
        self._scroll_to_bottom()

    def add_assistant_message(self, text: str):
        ts = datetime.now().strftime("%H:%M")
        bubble = ChatBubble(text, is_user=False, timestamp=ts)
        self._messages_layout.insertWidget(self._messages_layout.count() - 1, bubble)
        self._scroll_to_bottom()

    def _scroll_to_bottom(self):
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(50, lambda: self._scroll_area.verticalScrollBar().setValue(
            self._scroll_area.verticalScrollBar().maximum()
        ))

    def set_loading(self, loading: bool):
        self._input.setEnabled(not loading)
        self._send_btn.setEnabled(not loading)
        if loading:
            self._send_btn.setText("...")
        else:
            self._send_btn.setText("Send")

    def _clear_chat(self):
        while self._messages_layout.count() > 1:
            item = self._messages_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def focus_input(self):
        self._input.setFocus()
        self._input.selectAll()
