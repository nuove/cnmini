import socket
import threading
import json
import argparse
import os
from typing import Optional
from datetime import datetime
from constants import (
    HOST, PORT, BUFFER_SIZE, Colors,
    CMD_JOIN, CMD_EXIT, CMD_KICK, CMD_BAN,
    CMD_MAKEADMIN, CMD_REMOVEADMIN, CMD_LISTADMINS,
    CMD_HELP
)
from message import Message, MessageValidator

class ChatClient:
    def __init__(self, server_host=HOST):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
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
            print(f"{Colors.CYAN}Available commands:{Colors.END}")
            print(f"  {CMD_JOIN} <channel> - Join a channel")
            print(f"  {CMD_EXIT} - Exit the chat")
            print(f"  {CMD_HELP} - Show all commands")
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
                data = self.socket.recv(BUFFER_SIZE).decode('utf-8')
                if not data:
                    break

                message = Message.from_json(data)
                if message:
                    self.display_message(message)

            except Exception as e:
                print(f"{Colors.RED}Error receiving message: {e}{Colors.END}")
                break

    def display_message(self, message: Message):
        """Display a received message with appropriate formatting."""
        timestamp = datetime.fromisoformat(message.timestamp).strftime('%H:%M:%S')
        
        if message.from_user.lower() == 'server':
            # Handle special server messages
            if message.body.startswith('Welcome to the chat server'):
                print(f"\n{Colors.GREEN}[{timestamp}] {message.body}{Colors.END}\n")
            elif message.body.startswith('You have admin privileges'):
                self.is_admin = True
                print(f"\n{Colors.YELLOW}[{timestamp}] {message.body}{Colors.END}\n")
            elif message.body.startswith('Joined channel:'):
                print(f"\n{Colors.GREEN}[{timestamp}] {message.body}{Colors.END}\n")
                print(f"{Colors.YELLOW}You are now in channel: {message.body.split(': ')[1]}{Colors.END}\n")
            elif message.body.startswith('You have been kicked'):
                print(f"\n{Colors.RED}[{timestamp}] {message.body}{Colors.END}\n")
                self.running = False
            elif message.body.startswith('You have been banned'):
                print(f"\n{Colors.RED}[{timestamp}] {message.body}{Colors.END}\n")
                self.running = False
            elif message.body.startswith('You have been promoted to admin'):
                self.is_admin = True
                print(f"\n{Colors.YELLOW}[{timestamp}] {message.body}{Colors.END}\n")
            elif message.body.startswith('You have been demoted from admin'):
                self.is_admin = False
                print(f"\n{Colors.YELLOW}[{timestamp}] {message.body}{Colors.END}\n")
            else:
                print(f"{Colors.YELLOW}[{timestamp}] {message.body}{Colors.END}")
        else:
            # Regular chat messages
            if message.is_admin:
                print(f"{Colors.PURPLE}[{timestamp}] {message.from_user} (Admin): {message.body}{Colors.END}")
            else:
                print(f"{Colors.BLUE}[{timestamp}] {message.from_user}: {message.body}{Colors.END}")

    def send_message(self, message: Message):
        """Send a message to the server."""
        try:
            self.socket.send(message.to_json().encode('utf-8'))
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
    except Exception as e:
        print(f"{Colors.RED}Error: {e}{Colors.END}")
    finally:
        client.cleanup()

if __name__ == '__main__':
    main()
