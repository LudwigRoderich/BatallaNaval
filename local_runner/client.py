"""
Local client for Battleship game.
"""

import socket
import json
import sys
from typing import Optional, Tuple
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from server.game import ShipType, Coordinate
from protocol import (
    Message, MessageType,
    create_connect_message,
    create_place_ship_message,
    create_attack_message,
    create_ready_message,
    create_disconnect_message
)


class BattleshipClient:
    """Local Battleship game client."""
    
    def __init__(self, player_name: str, host: str = "localhost", port: int = 5000) -> None:
        self.player_name = player_name
        self.player_id: Optional[str] = None
        self.host = host
        self.port = port
        self.socket: Optional[socket.socket] = None
        self.connected = False
        self.game_state = None
    
    def connect(self) -> bool:
        """Connect to server."""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            self.connected = True
            print(f"[{self.player_name}] Connected to server")
            
            # Send connect message
            msg = create_connect_message(self.player_name)
            self.send_message(msg)
            
            # Receive registration confirmation
            response = self.receive_message()
            if response and response.msg_type == MessageType.PLAYER_REGISTERED:
                self.player_id = response.data.get("player_id")
                print(f"[{self.player_name}] Registered as: {self.player_id}")
                return True
            else:
                print(f"[{self.player_name}] Unexpected response: {response}")
                return False
        
        except Exception as e:
            print(f"[{self.player_name}] Connection failed: {e}")
            return False
    
    def send_message(self, message: Message) -> None:
        """Send message to server."""
        if not self.socket:
            print(f"[{self.player_name}] Not connected")
            return
        
        try:
            if self.player_id:
                message.player_id = self.player_id
            self.socket.sendall(message.to_json().encode("utf-8"))
        except Exception as e:
            print(f"[{self.player_name}] Send error: {e}")
    
    def receive_message(self) -> Optional[Message]:
        """Receive message from server."""
        if not self.socket:
            return None
        
        try:
            data = self.socket.recv(4096)
            if not data:
                return None
            return Message.from_json(data.decode("utf-8"))
        except Exception as e:
            print(f"[{self.player_name}] Receive error: {e}")
            return None
    
    def place_ship(
        self,
        ship_id: str,
        ship_type: ShipType,
        positions: list[Tuple[int, int]]
    ) -> bool:
        """Place a ship."""
        try:
            msg = create_place_ship_message(ship_id, ship_type.name, positions)
            self.send_message(msg)
            
            # Wait for confirmation
            response = self.receive_message()
            if response:
                if response.msg_type == MessageType.SHIP_PLACED:
                    print(f"[{self.player_name}] Ship {ship_id} placed successfully")
                    return True
                elif response.msg_type == MessageType.ERROR:
                    print(f"[{self.player_name}] Ship placement error: {response.data.get('error')}")
                    return False
            return False
        except Exception as e:
            print(f"[{self.player_name}] Place ship error: {e}")
            return False
    
    def send_ready(self) -> bool:
        """Signal ready for game start."""
        try:
            msg = create_ready_message()
            self.send_message(msg)
            print(f"[{self.player_name}] Sent ready signal")
            return True
        except Exception as e:
            print(f"[{self.player_name}] Ready error: {e}")
            return False
    
    def attack(self, x: int, y: int) -> bool:
        """Send attack."""
        try:
            msg = create_attack_message(x, y)
            self.send_message(msg)
            return True
        except Exception as e:
            print(f"[{self.player_name}] Attack error: {e}")
            return False
    
    def listen_for_messages(self) -> None:
        """Listen for messages from server."""
        while self.connected:
            try:
                message = self.receive_message()
                if not message:
                    break
                
                self.handle_message(message)
            except Exception as e:
                print(f"[{self.player_name}] Listen error: {e}")
                break
    
    def handle_message(self, message: Message) -> None:
        """Handle incoming message."""
        msg_type = message.msg_type
        
        if msg_type == MessageType.START_PLACING_SHIPS:
            print(f"\n[{self.player_name}] {message.data.get('message')}")
        
        elif msg_type == MessageType.WAITING_FOR_OPPONENT:
            print(f"[{self.player_name}] {message.data.get('message')}")
        
        elif msg_type == MessageType.SHIP_PLACED:
            print(f"[{self.player_name}] ✓ Ship placed: {message.data.get('ship_id')}")
        
        elif msg_type == MessageType.GAME_STARTED:
            print(f"\n[{self.player_name}] 🎮 GAME STARTED!\n")
        
        elif msg_type == MessageType.YOUR_TURN:
            print(f"\n[{self.player_name}] >>> YOUR TURN <<<\n")
        
        elif msg_type == MessageType.OPPONENT_TURN:
            print(f"[{self.player_name}] Opponent's turn, please wait...")
        
        elif msg_type == MessageType.ATTACK_RESULT:
            outcome = message.data.get("outcome")
            coord = message.data.get("attacked_coordinate")
            print(f"[{self.player_name}] Attack result: {outcome} at {coord}")
            if message.data.get("ship_sunk"):
                print(f"[{self.player_name}] 💥 SHIP SUNK!")
        
        elif msg_type == MessageType.GAME_OVER:
            result = message.data.get("result")
            if result == "WIN":
                print(f"\n[{self.player_name}] 🎉 YOU WIN! 🎉")
            else:
                print(f"\n[{self.player_name}] You lost. Winner: {message.data.get('winner')}")
        
        elif msg_type == MessageType.ERROR:
            print(f"[{self.player_name}] ❌ ERROR: {message.data.get('error')}")
        
        else:
            print(f"[{self.player_name}] Message: {msg_type.value}")
    
    def disconnect(self) -> None:
        """Disconnect from server."""
        try:
            msg = create_disconnect_message()
            self.send_message(msg)
            if self.socket:
                self.socket.close()
            self.connected = False
            print(f"[{self.player_name}] Disconnected")
        except Exception as e:
            print(f"[{self.player_name}] Disconnect error: {e}")
