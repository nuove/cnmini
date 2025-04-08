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

# Configure logging with more detailed format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(threadName)s] - %(message)s',
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
        self.channels: Dict[str, Set[str]] = {'general': set()}  # Initialize with general channel
        self.banned_users: Set[str] = set()  # Set of banned usernames
        self.admin_users: Set[str] = {DEFAULT_ADMIN}  # Set of admin users
        self.lock = threading.Lock()
        self.kicked_users: Set[str] = set()  # Set of kicked usernames
        self.running = True
        self.local_ip = get_local_ip()
        self.client_threads = []  # Track client threads for proper cleanup
        logging.info(f"Server initialized with default admin: {DEFAULT_ADMIN}")

    def initialize_socket(self):
        """Initialize the server socket."""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.settimeout(1.0)  # 1 second timeout for accept()
            self.server_socket.bind((HOST, PORT))
            self.server_socket.listen(5)
            logging.info(f"Server started on {self.local_ip}:{PORT}")
        except Exception as e:
            logging.error(f"Failed to initialize server socket: {e}")
            sys.exit(1)

    def cleanup(self):
        """Clean up server resources."""
        if not hasattr(self, '_cleanup_done'):
            self._cleanup_done = True
            self.running = False
            logging.info("Cleaning up server resources...")
            
            # Close all client connections
            with self.lock:
                for client_socket in list(self.clients.values()):
                    try:
                        client_socket.close()
                    except Exception as e:
                        logging.error(f"Error closing client socket: {e}")
            
            # Close server socket
            if self.server_socket:
                try:
                    self.server_socket.close()
                except Exception as e:
                    logging.error(f"Error closing server socket: {e}")
            
            # Clear data structures
            self.clients.clear()
            self.kicked_users.clear()
            
            # Keep channels and admin_users for persistence
            # Clear client threads list
            self.client_threads.clear()
            
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
                    client_thread = threading.Thread(target=self.handle_client, args=(client_socket,))
                    client_thread.daemon = True  # Make thread daemon so it exits when main thread exits
                    self.client_threads.append(client_thread)
                    client_thread.start()
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
        username = None
        try:
            # Set timeout for initial communication
            client_socket.settimeout(10.0)
            
            # Get username
            username = self.get_username(client_socket)
            if not username:
                client_addr = client_socket.getpeername()
                logging.warning(f"Failed to get valid username from {client_addr}")
                client_socket.close()
                return

            # Check if user is banned
            if username in self.banned_users:
                logging.warning(f"Banned user {username} attempted to connect from {client_socket.getpeername()}")
                ban_msg = Message(
                    from_user='server',
                    to_channel=username,
                    body="You are banned from the server.",
                    is_admin=True
                )
                self.send_message(client_socket, ban_msg)
                client_socket.close()
                return

            # Set a longer timeout for regular operation
            client_socket.settimeout(60.0)

            with self.lock:
                self.clients[username] = client_socket
                self.channels['general'].add(username)

            logging.info(f"User {username} connected successfully from {client_socket.getpeername()}")
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

            # Notify others about new user
            notify_msg = Message(
                from_user='server',
                to_channel='general',
                body=f"User joined: {username}",
                is_admin=True
            )
            self.broadcast_message(notify_msg)

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
            while self.running:
                try:
                    data = client_socket.recv(BUFFER_SIZE)
                    if not data:
                        logging.info(f"User {username} disconnected")
                        break

                    message = Message.from_json(data.decode('utf-8'))
                    if not message:
                        logging.warning(f"Received invalid message from {username}")
                        continue

                    if message.body.startswith('/'):
                        logging.info(f"Command from {username}: {message.body}")
                        self.handle_command(username, message, client_socket)
                    else:
                        logging.info(f"Message from {username} in {message.to_channel}: {message.body}")
                        self.broadcast_message(message)

                except socket.timeout:
                    # Just a timeout, check if server is still running
                    continue
                except ConnectionResetError:
                    logging.warning(f"Connection reset by {username}")
                    break
                except Exception as e:
                    logging.error(f"Error handling message from {username}: {e}")
                    break

        except Exception as e:
            client_addr = client_socket.getpeername() if hasattr(client_socket, 'getpeername') else "unknown"
            logging.error(f"Error in client handler for {username or client_addr}: {e}")
        finally:
            if username:
                self.handle_client_disconnect(username)
            else:
                try:
                    client_socket.close()
                except:
                    pass

    def handle_command(self, username: str, message: Message, client_socket: socket.socket):
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
                self.handle_make_admin(message, client_socket)
                logging.info(f"Admin {username} promoted {argument} to admin")
            elif command == CMD_REMOVEADMIN:
                self.handle_remove_admin(message, client_socket)
                logging.info(f"Admin {username} demoted {argument} from admin")
            elif command == CMD_LISTADMINS:
                self.handle_list_admins(username)
                logging.info(f"Admin {username} requested admin list")
        else:
            # Send permission denied message for admin commands
            self.send_message(client_socket, Message(
                from_user='server',
                to_channel=username,
                body="You don't have permission to use this command.",
                is_admin=True
            ))

    def handle_make_admin(self, message: Message, client_socket: socket.socket):
        """Handle make admin command."""
        if not self.is_admin(message.from_user):
            self.send_message(client_socket, Message(
                from_user='server',
                to_channel='',
                body='You do not have permission to make users admin.'
            ))
            return

        target_username = message.body.split(' ', 1)[1].strip()
        if target_username in self.clients:
            target_socket = self.clients[target_username]
            self.admin_users.add(target_username)
            self.send_message(target_socket, Message(
                from_user='server',
                to_channel='',
                body='You have been promoted to admin.'
            ))
            self.send_message(client_socket, Message(
                from_user='server',
                to_channel='',
                body=f'User {target_username} has been promoted to admin.'
            ))
            # Broadcast to all users
            self.broadcast_message(Message(
                from_user='server',
                to_channel='',
                body=f'User promoted: {target_username}'
            ))
        else:
            self.send_message(client_socket, Message(
                from_user='server',
                to_channel='',
                body=f'User {target_username} not found.'
            ))

    def handle_remove_admin(self, message: Message, client_socket: socket.socket):
        """Handle remove admin command."""
        if not self.is_admin(message.from_user):
            self.send_message(client_socket, Message(
                from_user='server',
                to_channel='',
                body='You do not have permission to remove admin status.'
            ))
            return

        target_username = message.body.split(' ', 1)[1].strip()
        if target_username in self.admin_users:
            target_socket = self.clients[target_username]
            self.admin_users.discard(target_username)
            self.send_message(target_socket, Message(
                from_user='server',
                to_channel='',
                body='You have been demoted from admin.'
            ))
            self.send_message(client_socket, Message(
                from_user='server',
                to_channel='',
                body=f'User {target_username} has been demoted from admin.'
            ))
            # Broadcast to all users
            self.broadcast_message(Message(
                from_user='server',
                to_channel='',
                body=f'User demoted: {target_username}'
            ))
        else:
            self.send_message(client_socket, Message(
                from_user='server',
                to_channel='',
                body=f'User {target_username} not found.'
            ))

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
        help_lines = ["Available commands:"]
        help_lines.append(f"{CMD_JOIN} <channel> - Join a channel")
        help_lines.append(f"{CMD_EXIT} - Exit the chat")
        
        if is_admin:
            help_lines.append("\nAdmin commands:")
            for cmd, desc in ADMIN_COMMANDS.items():
                help_lines.append(f"{desc}")
        
        help_text = "\n".join(help_lines)
        help_msg = Message(
            from_user='server',
            to_channel=username,
            body=help_text,
            is_admin=True
        )
        self.send_message(self.clients[username], help_msg)

    def handle_kick(self, admin: str, target: str):
        """Handle kick command."""
        if target in self.clients and target not in self.admin_users:
            kick_msg = Message(
                from_user='server',
                to_channel=target,
                body=f"You have been kicked by admin {admin}",
                is_admin=True
            )
            self.send_message(self.clients[target], kick_msg)
            self.kicked_users.add(target)
            self.clients[target].close()
            del self.clients[target]
            
            # Notify others about kick
            notify_msg = Message(
                from_user='server',
                to_channel='general',
                body=f"User kicked: {target}",
                is_admin=True
            )
            self.broadcast_message(notify_msg)
            
            logging.info(f"User {target} kicked by admin {admin}")

    def handle_ban(self, admin: str, target: str):
        """Handle ban command."""
        if target in self.clients and target not in self.admin_users:
            ban_msg = Message(
                from_user='server',
                to_channel=target,
                body=f"You have been banned by admin {admin}",
                is_admin=True
            )
            self.send_message(self.clients[target], ban_msg)
            self.banned_users.add(target)
            self.clients[target].close()
            del self.clients[target]
            
            # Notify others about ban
            notify_msg = Message(
                from_user='server',
                to_channel='general',
                body=f"User banned: {target}",
                is_admin=True
            )
            self.broadcast_message(notify_msg)
            
            logging.info(f"User {target} banned by admin {admin}")

    def handle_client_disconnect(self, username: str):
        """Handle client disconnection."""
        try:
            with self.lock:
                if username in self.clients:
                    self.clients[username].close()
                    del self.clients[username]
                    # Remove from all channels
                    for channel in self.channels:
                        if username in self.channels[channel]:
                            self.channels[channel].remove(username)
                    
                    # Notify others about user leaving
                    if username not in self.kicked_users and username not in self.banned_users:
                        notify_msg = Message(
                            from_user='server',
                            to_channel='general',
                            body=f"User left: {username}",
                            is_admin=True
                        )
                        self.broadcast_message(notify_msg)
                    
                    logging.info(f"User {username} disconnected and removed from all channels")
        except Exception as e:
            logging.error(f"Error during client disconnect for {username}: {e}")

    def broadcast_message(self, message: Message):
        """Broadcast message to appropriate channel."""
        # Pre-encode the message to JSON once
        encoded_message = message.to_json().encode('utf-8')
        
        with self.lock:
            if message.to_channel in self.channels:
                recipients = self.channels[message.to_channel].intersection(self.clients.keys())
                for username in recipients:
                    try:
                        self.clients[username].send(encoded_message)
                    except Exception as e:
                        logging.error(f"Error broadcasting to {username}: {e}")

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
            # Remove user from all current channels
            current_channels = []
            for ch in list(self.channels.keys()):
                if username in self.channels[ch]:
                    self.channels[ch].remove(username)
                    current_channels.append(ch)
                    # Clean up empty channels (except 'general')
                    if not self.channels[ch] and ch != 'general':
                        del self.channels[ch]

            # Join new channel
            if channel not in self.channels:
                self.channels[channel] = set([username])
            else:
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

    def is_admin(self, username: str) -> bool:
        """Check if a user is an admin."""
        return username in self.admin_users

# Create server instance
server = ChatServer()

def signal_handler(sig, frame):
    print(f"\n{Colors.YELLOW}Shutting down server...{Colors.END}")
    server.cleanup()
    # Use os._exit instead of sys.exit to force immediate termination
    os._exit(0)

# Register signal handlers for graceful shutdown
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

if __name__ == '__main__':
    try:
        server.start()
    except Exception as e:
        logging.error(f"Server error: {e}")
        print(f"{Colors.RED}Server error: {e}{Colors.END}")
    finally:
        server.cleanup() 