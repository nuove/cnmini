import socket
import threading
import json
import logging
import signal
import sys
import os
from datetime import datetime
from typing import Dict, Set
from constants import (
    HOST, PORT, BUFFER_SIZE, DEFAULT_ADMIN,
    CMD_JOIN, CMD_EXIT, CMD_KICK, CMD_BAN,
    CMD_MAKEADMIN, CMD_REMOVEADMIN, CMD_LISTADMINS,
    CMD_HELP, ADMIN_COMMANDS, Colors
)
from message import Message, MessageValidator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('server.log'),
        logging.StreamHandler()
    ]
)

def get_local_ip():
    """Get the local IP address of the machine."""
    try:
        # Create a socket to get local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Doesn't actually connect, just gets local IP
        s.connect(('8.8.8.8', 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        return '127.0.0.1'  # Fallback to localhost if can't determine IP

class ChatServer:
    def __init__(self):
        self.server_socket = None
        self.clients: Dict[str, socket.socket] = {}  # username -> socket
        self.channels: Dict[str, Set[str]] = {}  # channel -> set of usernames
        self.banned_users: Set[str] = set()  # Set of banned usernames
        self.admin_users: Set[str] = {DEFAULT_ADMIN}  # Set of admin users
        self.lock = threading.Lock()
        self.kicked_users: Set[str] = set()  # Set of kicked usernames
        self.running = True
        self.local_ip = get_local_ip()
        logging.info(f"Server initialized with default admin: {DEFAULT_ADMIN}")

    def initialize_socket(self):
        """Initialize the server socket."""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((HOST, PORT))
            self.server_socket.listen(5)
            logging.info(f"Server started on {self.local_ip}:{PORT}")
        except Exception as e:
            logging.error(f"Failed to initialize server socket: {e}")
            sys.exit(1)

    def cleanup(self):
        """Clean up server resources."""
        self.running = False
        logging.info("Cleaning up server resources...")
        
        # Close all client connections
        for client_socket in self.clients.values():
            try:
                client_socket.close()
            except:
                pass
        
        # Close server socket
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        
        self.clients.clear()
        self.channels.clear()
        logging.info("Server cleanup completed")

    def start(self):
        """Start the server and listen for connections."""
        try:
            self.initialize_socket()
            
            # Print server information in a clear, organized way
            print(f"\n{Colors.GREEN}Server Information:{Colors.END}")
            print(f"{Colors.GREEN}IP Address: {self.local_ip}{Colors.END}")
            print(f"{Colors.GREEN}Port: {PORT}{Colors.END}")
            print(f"{Colors.YELLOW}Default Admin: {DEFAULT_ADMIN}{Colors.END}")
            print(f"{Colors.CYAN}Logging to: server.log{Colors.END}")
            print(f"\n{Colors.YELLOW}Press Ctrl+C to stop the server{Colors.END}")

            while self.running:
                try:
                    client_socket, address = self.server_socket.accept()
                    logging.info(f"New connection from {address}")
                    print(f"{Colors.CYAN}New connection from {address}{Colors.END}")
                    threading.Thread(target=self.handle_client, args=(client_socket,)).start()
                except socket.timeout:
                    # This is expected due to the socket timeout
                    continue
                
                except Exception as e:
                    logging.error(f"Error accepting connection: {e}")
                    break
        

        except Exception as e:
            logging.error(f"Server error: {e}")
            print(f"{Colors.RED}Server error: {e}{Colors.END}")
        finally:
            self.cleanup()

    def handle_client(self, client_socket: socket.socket):
        """Handle a new client connection."""
        try:
            # Get username
            username = self.get_username(client_socket)
            if not username:
                logging.warning(f"Failed to get valid username from {client_socket.getpeername()}")
                client_socket.close()
                return

            # Check if user is banned
            if username in self.banned_users:
                logging.warning(f"Banned user {username} attempted to connect")
                ban_msg = Message(
                    from_user='server',
                    to_channel=username,
                    body="You are banned from the server.",
                    is_admin=True
                )
                self.send_message(client_socket, ban_msg)
                client_socket.close()
                return

            with self.lock:
                self.clients[username] = client_socket
                self.channels['general'] = self.channels.get('general', set()) | {username}

            logging.info(f"User {username} connected successfully")
            if username in self.admin_users:
                logging.info(f"Admin user {username} connected")

            # Send welcome message
            welcome_msg = Message(
                from_user='server',
                to_channel=username,
                body=f"Welcome to the chat server, {username}!",
                is_admin=True
            )
            self.send_message(client_socket, welcome_msg)

            # If user is admin, send admin commands list
            if username in self.admin_users:
                admin_welcome = Message(
                    from_user='server',
                    to_channel=username,
                    body="You have admin privileges. Use /help to see available commands.",
                    is_admin=True
                )
                self.send_message(client_socket, admin_welcome)

            # Handle client messages
            while True:
                try:
                    data = client_socket.recv(BUFFER_SIZE).decode('utf-8')
                    if not data:
                        break

                    message = Message.from_json(data)
                    if not message:
                        continue

                    if message.body.startswith('/'):
                        self.handle_command(username, message)
                    else:
                        self.broadcast_message(message)
                        logging.info(f"Message from {username} in {message.to_channel}: {message.body}")

                except Exception as e:
                    logging.error(f"Error handling message from {username}: {e}")
                    break

        except Exception as e:
            logging.error(f"Error in client handler for {username}: {e}")
        finally:
            self.handle_client_disconnect(username)

    def handle_command(self, username: str, message: Message):
        """Handle client commands."""
        command, argument = MessageValidator.parse_command(message.body)
        is_admin = username in self.admin_users

        if command == CMD_JOIN:
            self.handle_join(username, argument)
            logging.info(f"User {username} joined channel {argument}")
        elif command == CMD_EXIT:
            self.handle_exit(username)
            logging.info(f"User {username} exited")
        elif command == CMD_HELP:
            self.handle_help(username, is_admin)
            logging.info(f"User {username} requested help")
        elif is_admin:
            if command == CMD_KICK:
                self.handle_kick(username, argument)
                logging.info(f"Admin {username} kicked user {argument}")
            elif command == CMD_BAN:
                self.handle_ban(username, argument)
                logging.info(f"Admin {username} banned user {argument}")
            elif command == CMD_MAKEADMIN:
                self.handle_make_admin(username, argument)
                logging.info(f"Admin {username} promoted {argument} to admin")
            elif command == CMD_REMOVEADMIN:
                self.handle_remove_admin(username, argument)
                logging.info(f"Admin {username} demoted {argument} from admin")
            elif command == CMD_LISTADMINS:
                self.handle_list_admins(username)
                logging.info(f"Admin {username} requested admin list")

    def handle_make_admin(self, admin: str, target: str):
        """Handle makeadmin command."""
        if target in self.clients and target not in self.admin_users:
            self.admin_users.add(target)
            notify_msg = Message(
                from_user='server',
                to_channel='general',
                body=f"{target} has been promoted to admin by {admin}",
                is_admin=True
            )
            self.broadcast_message(notify_msg)
            
            # Notify the new admin
            admin_msg = Message(
                from_user='server',
                to_channel=target,
                body="You have been promoted to admin. Use /help to see available commands.",
                is_admin=True
            )
            self.send_message(self.clients[target], admin_msg)
            logging.info(f"User {target} promoted to admin by {admin}")

    def handle_remove_admin(self, admin: str, target: str):
        """Handle removeadmin command."""
        if target in self.clients and target in self.admin_users and target != DEFAULT_ADMIN:
            self.admin_users.remove(target)
            notify_msg = Message(
                from_user='server',
                to_channel='general',
                body=f"{target} has been demoted from admin by {admin}",
                is_admin=True
            )
            self.broadcast_message(notify_msg)
            
            # Notify the demoted user
            demote_msg = Message(
                from_user='server',
                to_channel=target,
                body="You have been demoted from admin.",
                is_admin=True
            )
            self.send_message(self.clients[target], demote_msg)
            logging.info(f"User {target} demoted from admin by {admin}")

    def handle_list_admins(self, username: str):
        """Handle listadmins command."""
        admin_list = ", ".join(sorted(self.admin_users))
        list_msg = Message(
            from_user='server',
            to_channel=username,
            body=f"Current admins: {admin_list}",
            is_admin=True
        )
        self.send_message(self.clients[username], list_msg)
        logging.info(f"Admin list requested by {username}")

    def handle_help(self, username: str, is_admin: bool):
        """Handle help command."""
        help_text = "Available commands:\n"
        help_text += f"{CMD_JOIN} <channel> - Join a channel\n"
        help_text += f"{CMD_EXIT} - Exit the chat\n"
        
        if is_admin:
            help_text += "\nAdmin commands:\n"
            for cmd, desc in ADMIN_COMMANDS.items():
                help_text += f"{desc}\n"
        
        help_msg = Message(
            from_user='server',
            to_channel=username,
            body=help_text,
            is_admin=True
        )
        self.send_message(self.clients[username], help_msg)

    def handle_kick(self, admin: str, target: str):
        """Handle kick command from admin."""
        if target in self.clients and target != admin:
            self.kicked_users.add(target)
            kick_msg = Message(
                from_user='server',
                to_channel=target,
                body=f"You have been kicked by {admin}",
                is_admin=True
            )
            self.send_message(self.clients[target], kick_msg)
            self.handle_client_disconnect(target)
            
            # Notify others
            notify_msg = Message(
                from_user='server',
                to_channel='general',
                body=f"{target} has been kicked by {admin}",
                is_admin=True
            )
            self.broadcast_message(notify_msg)
            logging.info(f"User {target} kicked by admin {admin}")

    def handle_ban(self, admin: str, target: str):
        """Handle ban command from admin."""
        if target in self.clients and target != admin:
            self.banned_users.add(target)
            ban_msg = Message(
                from_user='server',
                to_channel=target,
                body=f"You have been banned by {admin}",
                is_admin=True
            )
            self.send_message(self.clients[target], ban_msg)
            self.handle_client_disconnect(target)
            
            # Notify others
            notify_msg = Message(
                from_user='server',
                to_channel='general',
                body=f"{target} has been banned by {admin}",
                is_admin=True
            )
            self.broadcast_message(notify_msg)
            logging.info(f"User {target} banned by admin {admin}")

    def handle_client_disconnect(self, username: str):
        """Handle client disconnection."""
        with self.lock:
            if username in self.clients:
                self.clients[username].close()
                del self.clients[username]
            
            # Remove user from all channels
            for channel in self.channels:
                if username in self.channels[channel]:
                    self.channels[channel].remove(username)
            
            # Remove empty channels
            self.channels = {k: v for k, v in self.channels.items() if v}

            # Notify others only if it wasn't a kick/ban
            if username not in self.kicked_users and username not in self.banned_users:
                disconnect_msg = Message(
                    from_user='server',
                    to_channel='general',
                    body=f"{username} has left the chat",
                    is_admin=True
                )
                self.broadcast_message(disconnect_msg)
                logging.info(f"User {username} disconnected normally")

            # Clean up kicked users set
            if username in self.kicked_users:
                self.kicked_users.remove(username)

    def broadcast_message(self, message: Message):
        """Broadcast message to appropriate channel."""
        with self.lock:
            if message.to_channel in self.channels:
                for username in self.channels[message.to_channel]:
                    if username in self.clients:
                        self.send_message(self.clients[username], message)

    def send_message(self, client_socket: socket.socket, message: Message):
        """Send message to a client."""
        try:
            client_socket.send(message.to_json().encode('utf-8'))
        except Exception as e:
            logging.error(f"Error sending message: {e}")

    def get_username(self, client_socket: socket.socket) -> str:
        """Get and validate username from client."""
        try:
            data = client_socket.recv(BUFFER_SIZE).decode('utf-8')
            message = Message.from_json(data)
            
            if not message or not MessageValidator.validate_username(message.from_user):
                return None
                
            with self.lock:
                if message.from_user in self.clients:
                    return None
                    
            return message.from_user
        except Exception as e:
            logging.error(f"Error getting username: {e}")
            return None

    def handle_join(self, username: str, channel: str):
        """Handle join command."""
        if not channel:
            return

        with self.lock:
            # Leave current channel
            for ch in self.channels:
                if username in self.channels[ch]:
                    self.channels[ch].remove(username)

            # Join new channel
            if channel not in self.channels:
                self.channels[channel] = set()
            self.channels[channel].add(username)

            # Notify client
            self.send_message(self.clients[username], Message(
                from_user='server',
                to_channel=username,
                body=f"Joined channel: {channel}",
                is_admin=True
            ))

    def handle_exit(self, username: str):
        """Handle exit command."""
        self.handle_client_disconnect(username)

if __name__ == "__main__":
    server = ChatServer()
    
    def signal_handler(sig, frame):
        print(f"\n{Colors.YELLOW}Shutting down server...{Colors.END}")
        server.cleanup()
        sys.exit(0)
    
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        server.start()
    except Exception as e:
        logging.error(f"Server error: {e}")
        print(f"{Colors.RED}Server error: {e}{Colors.END}")
    finally:
        server.cleanup() 