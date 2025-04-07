import socket
from datetime import datetime, timezone

# Network Configuration
HOST = '0.0.0.0'  # Listen on all available network interfaces
PORT = 1738  # Fixed port for the server
BUFFER_SIZE = 4096

# Admin Configuration
DEFAULT_ADMIN = 'admin'
ADMIN_COMMANDS = {
    'kick': '/kick <username>',
    'ban': '/ban <username>',
    'makeadmin': '/makeadmin <username>',
    'removeadmin': '/removeadmin <username>',
    'listadmins': '/listadmins'
}

# Commands
CMD_JOIN = '/join'
CMD_EXIT = '/exit'
CMD_KICK = '/kick'
CMD_BAN = '/ban'
CMD_MAKEADMIN = '/makeadmin'
CMD_REMOVEADMIN = '/removeadmin'
CMD_LISTADMINS = '/listadmins'
CMD_HELP = '/help'

# Validation
USERNAME_MIN_LENGTH = 3
USERNAME_MAX_LENGTH = 20
USERNAME_PATTERN = r'^[a-zA-Z0-9_-]+$'

# Colors for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'

def get_timestamp():
    """Generate ISO format timestamp in UTC."""
    return datetime.now(timezone.utc).isoformat()

def format_message(from_user: str, to_channel: str, body: str, is_admin: bool = False) -> dict:
    """Format a message according to the protocol."""
    return {
        "from": from_user,
        "to": to_channel,
        "body": body,
        "timestamp": get_timestamp(),
        "isAdmin": is_admin
    } 