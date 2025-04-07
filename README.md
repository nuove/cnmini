# ChudChat

A simplified IRC-like chat system implemented in Python using raw sockets.

## Requirements

- Python 3.7+
- Dependencies listed in `requirements.txt`

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd irc-chat
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

1. Start the server:
```bash
python server.py
```

2. Start one or more clients:
   - On the same machine:
   ```bash
   python client.py
   ```
   - From a different device on the same network:
   ```bash
   python client.py --server <server-ip-address>
   ```
   Replace `<server-ip-address>` with the IP address of the machine running the server.
   You can find the server's IP address using:
   - On Linux/Mac: `ifconfig` or `ip addr`
   - On Windows: `ipconfig`

3. When prompted, enter a username that follows these rules:
   - Length: 3-20 characters
   - Allowed characters: alphanumeric, hyphens (-), underscores (_)
   - No whitespace allowed
   - Must be unique per session

## Admin System

The chat system includes a hierarchical admin system:

- Default admin account: `admin`
- Only admins can promote other users to admin status
- The default admin account cannot be demoted
- Admins have access to special commands for server management

### Admin Commands

1. `/kick <username>`
   - Kicks a user from the server
   - Usage: `/kick john_doe`
   - Only admins can use this command

2. `/ban <username>`
   - Bans a user from the server
   - Banned users cannot reconnect
   - Usage: `/ban john_doe`
   - Only admins can use this command

3. `/makeadmin <username>`
   - Promotes a user to admin status
   - Usage: `/makeadmin john_doe`
   - Only admins can use this command

4. `/removeadmin <username>`
   - Demotes an admin to regular user
   - Cannot be used on the default admin account
   - Usage: `/removeadmin john_doe`
   - Only admins can use this command

5. `/listadmins`
   - Lists all current admin users
   - Usage: `/listadmins`
   - Only admins can use this command

### Regular Commands

1. `/join <channel>`
   - Joins a chat channel
   - Usage: `/join general`
   - Available to all users

2. `/exit`
   - Exits the chat
   - Usage: `/exit`
   - Available to all users

3. `/help`
   - Shows available commands
   - Usage: `/help`
   - Available to all users
   - Shows admin commands only to admin users

## Message Format

Messages are sent in JSON-like format:
```json
{
    "from": "username",
    "to": "channel",
    "body": "message content",
    "timestamp": "2025-03-12T14:30:00Z",
    "isAdmin": false
}
```

## TODO

This is a somewhat complete CLI implementation. I'm not really happy with the redundancy of the logging system, prompts/feedback messages and overall UX, so that'll need a bit of work. 