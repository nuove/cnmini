import socket
import threading
import argparse
from typing import Optional
from datetime import datetime
from constants import (
    HOST, PORT, BUFFER_SIZE, Colors,
    CMD_JOIN, CMD_EXIT, CMD_KICK, CMD_BAN,
    CMD_MAKEADMIN, CMD_REMOVEADMIN, CMD_LISTADMINS,
    CMD_HELP, CMD_LISTUSERS
)
from message import Message, MessageValidator

class ChatClient:
    def __init__(self, server_host=HOST):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.settimeout(10)  # Set a 10-second timeout for connection
        self.server_host = server_host
        self.server_port = PORT
        self.username: Optional[str] = None
        self.current_channel = 'general'
        self.running = False
        self.is_admin = False

    def start(self):
        """Start the client and connect to the server."""
        try:
            print(f"{Colors.CYAN}Connecting to server at {self.server_host}:{self.server_port}...{Colors.END}")
            self.socket.connect((self.server_host, self.server_port))
            self.running = True

            # Get username
            while not self.username:
                username = input(f"{Colors.CYAN}Enter your username (3-20 chars, alphanumeric, -_): {Colors.END}")
                if MessageValidator.validate_username(username):
                    self.username = username
                    self.send_message(Message(
                        from_user=username,
                        to_channel='',
                        body=username
                    ))
                else:
                    print(f"{Colors.RED}Invalid username. Please try again.{Colors.END}")

            # Start message receiver thread
            receiver_thread = threading.Thread(target=self.receive_messages)
            receiver_thread.daemon = True
            receiver_thread.start()

            # Main message sending loop
            print(f"\n{Colors.GREEN}Connected to server!{Colors.END}")
            print(f"{Colors.CYAN}User commands:{Colors.END}")
            print(f"  {CMD_JOIN} <channel> - Join a channel")
            print(f"  {CMD_EXIT} - Exit the chat")
            print(f"  {CMD_HELP} - Show all commands")
            print(f"  {CMD_LISTUSERS} - List all users")
            
            if self.username == "admin" or self.is_admin:
                print(f"  {CMD_KICK} - Kick <username> from channel")
                print(f"  {CMD_BAN} <username> - Ban <username> from channel")
                print(f"  {CMD_MAKEADMIN} <username> - Elevate <username> to Admin")
                print(f"  {CMD_REMOVEADMIN} <username> - Remove <username> as Admin")
                print(f"  {CMD_LISTADMINS} - List all admins in channel")
                
            print(f"\n{Colors.YELLOW}You are in channel: {self.current_channel}{Colors.END}\n")

            while self.running:
                try:
                    message = input()
                    if message.lower() == CMD_EXIT:
                        self.send_message(Message(
                            from_user=self.username,
                            to_channel=self.current_channel,
                            body=CMD_EXIT
                        ))
                        break
                    elif message.lower().startswith(CMD_JOIN + ' '):
                        channel = message[6:].strip()
                        if channel:
                            self.current_channel = channel
                            self.send_message(Message(
                                from_user=self.username,
                                to_channel=self.current_channel,
                                body=f'{CMD_JOIN} {channel}'
                            ))
                    elif message.lower() == CMD_HELP:
                        self.send_message(Message(
                            from_user=self.username,
                            to_channel=self.current_channel,
                            body=CMD_HELP
                        ))
                    elif message.lower() == CMD_LISTUSERS:
                        self.send_message(Message(
                            from_user=self.username,
                            to_channel=self.current_channel,
                            body=CMD_LISTUSERS
                        ))
                    else:
                        self.send_message(Message(
                            from_user=self.username,
                            to_channel=self.current_channel,
                            body=message
                        ))
                except Exception as e:
                    print(f"{Colors.RED}Error sending message: {e}{Colors.END}")
                    break

        except Exception as e:
            print(f"{Colors.RED}Failed to connect to server: {e}{Colors.END}")
        finally:
            self.cleanup()

    def receive_messages(self):
        """Receive and display messages from the server."""
        while self.running:
            try:
                data = self.socket.recv(BUFFER_SIZE)
                if not data:
                    print(f"\n{Colors.RED}Connection to server lost.{Colors.END}")
                    self.running = False
                    break

                message = Message.from_json(data.decode('utf-8'))
                if message:
                    self.display_message(message)

            except socket.timeout:
                # Just a timeout, continue checking if we're still running
                continue
            except ConnectionResetError:
                print(f"\n{Colors.RED}Connection reset by server.{Colors.END}")
                self.running = False
                break
            except Exception as e:
                print(f"{Colors.RED}Error receiving message: {e}{Colors.END}")
                self.running = False
                break

    def display_message(self, message: Message):
        """Display a received message with appropriate formatting."""
        timestamp = datetime.fromisoformat(message.timestamp).strftime('%H:%M:%S')
        
        if message.from_user.lower() == 'server':
            # Handle special server messages
            if message.body.startswith('Welcome to the chat server'):
                # Don't show welcome message, it's redundant
                pass
            elif message.body.startswith('You have admin privileges'):
                self.is_admin = True
                print(f"\n{Colors.YELLOW}[Admin] You now have admin privileges{Colors.END}\n")
            elif message.body.startswith('Joined channel:'):
                channel = message.body.split(': ')[1]
                print(f"\n{Colors.GREEN}[Channel] Joined {channel}{Colors.END}\n")
            elif message.body.startswith('You have been kicked'):
                print(f"\n{Colors.RED}[System] You have been kicked from the server{Colors.END}\n")
                self.running = False
            elif message.body.startswith('You have been banned'):
                print(f"\n{Colors.RED}[System] You have been banned from the server{Colors.END}\n")
                self.running = False
            elif message.body.startswith('You have been promoted to admin'):
                self.is_admin = True
                print(f"\n{Colors.YELLOW}[Admin] You have been promoted to admin{Colors.END}\n")
            elif message.body.startswith('You have been demoted from admin'):
                self.is_admin = False
                print(f"\n{Colors.YELLOW}[Admin] You have been demoted from admin{Colors.END}\n")
            elif message.body.startswith('User joined:'):
                # Show user join notifications
                username = message.body.split(': ')[1]
                print(f"{Colors.CYAN}[Join] {username} joined the chat{Colors.END}")
            elif message.body.startswith('User left:'):
                # Show user leave notifications
                username = message.body.split(': ')[1]
                print(f"{Colors.CYAN}[Leave] {username} left the chat{Colors.END}")
            elif message.body.startswith('User kicked:'):
                # Show user kick notifications
                username = message.body.split(': ')[1]
                print(f"{Colors.RED}[Kick] {username} was kicked from the server{Colors.END}")
            elif message.body.startswith('User banned:'):
                # Show user ban notifications
                username = message.body.split(': ')[1]
                print(f"{Colors.RED}[Ban] {username} was banned from the server{Colors.END}")
            elif message.body.startswith('User promoted:'):
                # Show user promotion notifications
                username = message.body.split(': ')[1]
                print(f"{Colors.YELLOW}[Admin] {username} was promoted to admin{Colors.END}")
            elif message.body.startswith('User demoted:'):
                # Show user demotion notifications
                username = message.body.split(': ')[1]
                print(f"{Colors.YELLOW}[Admin] {username} was demoted from admin{Colors.END}")
            elif message.body == CMD_HELP or message.body.startswith('User commands:'):
                # Display help message
                print(f"\n{Colors.CYAN}{message.body}{Colors.END}\n")
        else:
            # Regular chat messages - only show if they're in the current channel
            if message.to_channel == self.current_channel:
                if message.is_admin:
                    print(f"{Colors.PURPLE}[{timestamp}] {message.from_user} (Admin): {message.body}{Colors.END}")
                else:
                    print(f"{Colors.BLUE}[{timestamp}] {message.from_user}: {message.body}{Colors.END}")

    def send_message(self, message: Message):
        """Send a message to the server."""
        if not self.running:
            return
            
        try:
            encoded_message = message.to_json().encode('utf-8')
            self.socket.send(encoded_message)
        except ConnectionResetError:
            print(f"\n{Colors.RED}Connection reset by server.{Colors.END}")
            self.running = False
        except Exception as e:
            print(f"{Colors.RED}Error sending message: {e}{Colors.END}")
            self.running = False

    def cleanup(self):
        """Clean up resources."""
        self.running = False
        self.socket.close()
        print(f"\n{Colors.YELLOW}Disconnected from server.{Colors.END}")

def main():
    parser = argparse.ArgumentParser(description='Chat Client')
    parser.add_argument('--server', '-s', default=HOST,
                      help='Server IP address (default: localhost)')
    args = parser.parse_args()

    client = ChatClient(server_host=args.server)
    try:
        client.start()
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Disconnecting from server...{Colors.END}")

if __name__ == '__main__':
    main()
