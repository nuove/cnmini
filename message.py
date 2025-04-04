import json
import re
from datetime import datetime
from typing import Dict, Optional
from constants import USERNAME_PATTERN, USERNAME_MIN_LENGTH, USERNAME_MAX_LENGTH

class Message:
    def __init__(self, from_user: str, to_channel: str, body: str, is_admin: bool = False):
        self.from_user = from_user
        self.to_channel = to_channel
        self.body = body
        self.timestamp = datetime.utcnow().isoformat()
        self.is_admin = is_admin

    @classmethod
    def from_dict(cls, data: Dict) -> 'Message':
        """Create a Message instance from a dictionary."""
        return cls(
            from_user=data['from'],
            to_channel=data['to'],
            body=data['body'],
            is_admin=data.get('isAdmin', False)
        )

    def to_dict(self) -> Dict:
        """Convert the message to a dictionary."""
        return {
            'from': self.from_user,
            'to': self.to_channel,
            'body': self.body,
            'timestamp': self.timestamp,
            'isAdmin': self.is_admin
        }

    def to_json(self) -> str:
        """Convert the message to a JSON string."""
        return json.dumps(self.to_dict())

    @staticmethod
    def from_json(json_str: str) -> Optional['Message']:
        """Create a Message instance from a JSON string."""
        try:
            data = json.loads(json_str)
            return Message.from_dict(data)
        except (json.JSONDecodeError, KeyError):
            return None

class MessageValidator:
    @staticmethod
    def validate_username(username: str) -> bool:
        """Validate username according to the rules."""
        if not username:
            return False
        if not USERNAME_MIN_LENGTH <= len(username) <= USERNAME_MAX_LENGTH:
            return False
        return bool(re.match(USERNAME_PATTERN, username))

    @staticmethod
    def validate_message(message: Message) -> bool:
        """Validate a message object."""
        if not MessageValidator.validate_username(message.from_user):
            return False
        if not message.to_channel or not message.body:
            return False
        return True

    @staticmethod
    def parse_command(message: str) -> tuple[str, str]:
        """Parse a command message into command and argument."""
        parts = message.split(maxsplit=1)
        command = parts[0].lower()
        argument = parts[1] if len(parts) > 1 else ''
        return command, argument 