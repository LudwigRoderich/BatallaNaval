"""
Local server for Battleship game.
Manages game logic and communication with clients.
"""

import socket
import threading
import json
import sys
from typing import Dict, Optional, Tuple
from pathlib import Path

# Add parent directory to path to import game module
sys.path.insert(0, str(Path(__file__).parent.parent))

from server.game import (
    Game, Player, Ship, Coordinate, ShipType, 
    GameState, AttackOutcome
)
from protocol import Message, MessageType, create_connect_message
from protocol import create_place_ship_message, create_attack_message


class ClientHandler(threading.Thread):
    """Handles communication with a single client."""
    
    def __init__(
        self,
        client_socket: socket.socket,
        client_address: Tuple[str, int],
        server: "BattleshipServer",
        client_id: int
    ) -> None:
        super().__init__(daemon=True)
        self.client_socket = client_socket
        self.client_address = client_address
        self.server = server
        self.client_id = client_id
        self.player_id: Optional[str] = None
        self.running = True
    
    def run(self) -> None:
        """Main client handler loop."""
        try:
            print(f"[CLIENT {self.client_id}] Connected from {self.client_address}")
            
            while self.running:
                # Receive message
                data = self.client_socket.recv(4096)
                if not data:
                    break
                
                try:
                    message = Message.from_json(data.decode("utf-8"))
                    self.handle_message(message)
                except json.JSONDecodeError as e:
                    self.send_error(f"Invalid message format: {e}")
                except Exception as e:
                    print(f"[CLIENT {self.client_id}] Error: {e}")
                    self.send_error(str(e))
        
        except Exception as e:
            print(f"[CLIENT {self.client_id}] Connection error: {e}")
        finally:
            self.cleanup()
    
    def handle_message(self, message: Message) -> None:
        """Process incoming message."""
        msg_type = message.msg_type
        
        if msg_type == MessageType.CONNECT:
            self.handle_connect(message)
        elif msg_type == MessageType.PLACE_SHIP:
            self.handle_place_ship(message)
        elif msg_type == MessageType.READY:
            self.handle_ready(message)
        elif msg_type == MessageType.ATTACK:
            self.handle_attack(message)
        elif msg_type == MessageType.DISCONNECT:
            self.handle_disconnect(message)
        else:
            self.send_error(f"Unknown message type: {msg_type}")
    
    def handle_connect(self, message: Message) -> None:
        """Handle player connection."""
        player_name = message.data.get("player_name", f"Player{self.client_id}")
        
        try:
            player_id = self.server.register_player(player_name, self)
            self.player_id = player_id
            
            # Send confirmation
            response = Message(
                MessageType.PLAYER_REGISTERED,
                {
                    "player_id": player_id,
                    "player_name": player_name,
                    "message": "Successfully registered"
                },
                player_id
            )
            self.send_message(response)
            
            # Notify server about registration
            self.server.check_game_state()
        
        except Exception as e:
            self.send_error(f"Registration failed: {e}")
    
    def handle_place_ship(self, message: Message) -> None:
        """Handle ship placement."""
        if not self.player_id:
            self.send_error("Not connected. Send CONNECT first.")
            return
        
        try:
            ship_id = message.data.get("ship_id")
            ship_type_str = message.data.get("ship_type")
            positions_list = message.data.get("positions")
            
            if not all([ship_id, ship_type_str, positions_list]):
                raise ValueError("Missing required ship placement data")
            
            # Convert positions to Coordinate objects
            positions = {Coordinate(x, y) for x, y in positions_list}
            
            # Create ship
            ship_type = ShipType[ship_type_str]
            ship = Ship(ship_id, ship_type, positions)
            
            # Place ship in game
            self.server.game.place_ship(self.player_id, ship)
            
            # Send confirmation
            response = Message(
                MessageType.SHIP_PLACED,
                {
                    "ship_id": ship_id,
                    "message": f"Ship {ship_id} placed successfully"
                },
                self.player_id
            )
            self.send_message(response)
        
        except Exception as e:
            self.send_error(f"Ship placement failed: {e}")
    
    def handle_ready(self, message: Message) -> None:
        """Handle player ready status."""
        if not self.player_id:
            self.send_error("Not connected.")
            return
        
        try:
            self.server.mark_player_ready(self.player_id)
            self.server.check_game_state()
        except Exception as e:
            self.send_error(f"Ready failed: {e}")
    
    def handle_attack(self, message: Message) -> None:
        """Handle attack action."""
        if not self.player_id:
            self.send_error("Not connected.")
            return
        
        if self.server.game.state != GameState.IN_PROGRESS:
            self.send_error("Game is not in progress.")
            return
        
        if self.server.game.current_turn != self.player_id:
            self.send_error(f"It's not your turn. Current turn: {self.server.game.current_turn}")
            return
        
        try:
            x = message.data.get("x")
            y = message.data.get("y")
            
            if x is None or y is None:
                raise ValueError("Missing x or y coordinate")
            
            coord = Coordinate(x, y)
            
            # Execute attack
            result = self.server.game.attack(self.player_id, coord)
            
            # Notify both players
            self.server.broadcast_attack_result(self.player_id, result)
            
            # Check if game is finished
            if result.game_finished:
                self.server.notify_game_over()
        
        except Exception as e:
            self.send_error(f"Attack failed: {e}")
    
    def handle_disconnect(self, message: Message) -> None:
        """Handle player disconnection."""
        print(f"[CLIENT {self.client_id}] Player {self.player_id} disconnected")
        self.running = False
    
    def send_message(self, message: Message) -> None:
        """Send message to client."""
        try:
            self.client_socket.sendall(message.to_json().encode("utf-8"))
        except Exception as e:
            print(f"[CLIENT {self.client_id}] Send error: {e}")
    
    def send_error(self, error_msg: str) -> None:
        """Send error message to client."""
        error_msg_obj = Message(
            MessageType.ERROR,
            {"error": error_msg},
            self.player_id
        )
        self.send_message(error_msg_obj)
    
    def cleanup(self) -> None:
        """Clean up resources."""
        try:
            self.client_socket.close()
        except:
            pass
        
        if self.player_id:
            self.server.unregister_player(self.player_id)


class BattleshipServer:
    """Local Battleship game server."""
    
    def __init__(self, host: str = "localhost", port: int = 5000) -> None:
        self.host = host
        self.port = port
        self.game = Game(board_size=10)
        self.clients: Dict[str, ClientHandler] = {}
        self.ready_players: set[str] = set()
        self.lock = threading.Lock()
        self.running = True
    
    def start(self) -> None:
        """Start the server."""
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            server_socket.bind((self.host, self.port))
            server_socket.listen(2)  # Max 2 players
            
            print(f"[SERVER] Battleship Server started on {self.host}:{self.port}")
            print("[SERVER] Waiting for players...")
            
            client_id = 1
            while self.running and len(self.clients) < 2:
                try:
                    client_socket, client_address = server_socket.accept()
                    
                    # Start game first if not started
                    if self.game.state == GameState.WAITING_FOR_PLAYERS:
                        self.game.start()
                    
                    # Handle client
                    handler = ClientHandler(
                        client_socket,
                        client_address,
                        self,
                        client_id
                    )
                    handler.start()
                    client_id += 1
                
                except KeyboardInterrupt:
                    break
                except Exception as e:
                    print(f"[SERVER] Error accepting connection: {e}")
        
        except Exception as e:
            print(f"[SERVER] Error: {e}")
        finally:
            server_socket.close()
            print("[SERVER] Server stopped")
    
    def register_player(self, player_name: str, handler: ClientHandler) -> str:
        """Register a new player."""
        with self.lock:
            if len(self.clients) >= 2:
                raise Exception("Game is full (2 players max)")
            
            try:
                self.game.add_player(player_name)
                self.clients[player_name] = handler
                print(f"[SERVER] Player '{player_name}' registered ({len(self.clients)}/2)")
                return player_name
            except Exception as e:
                raise Exception(f"Failed to register player: {e}")
    
    def unregister_player(self, player_id: str) -> None:
        """Unregister a player."""
        with self.lock:
            if player_id in self.clients:
                del self.clients[player_id]
                print(f"[SERVER] Player '{player_id}' unregistered ({len(self.clients)}/2)")
    
    def mark_player_ready(self, player_id: str) -> None:
        """Mark a player as ready."""
        with self.lock:
            self.ready_players.add(player_id)
            print(f"[SERVER] Player '{player_id}' is ready ({len(self.ready_players)}/2)")
    
    def check_game_state(self) -> None:
        """Check if game state should change."""
        with self.lock:
            if len(self.clients) == 2:
                if self.game.state == GameState.PLACING_SHIPS:
                    # Check if all players are ready
                    if len(self.ready_players) == 2:
                        self.game.finish_ship_placement()
                        print("[SERVER] All players ready. Game started!")
                        
                        # Notify all players
                        for handler in self.clients.values():
                            msg = Message(
                                MessageType.GAME_STARTED,
                                {"message": "Game has started!"},
                                handler.player_id
                            )
                            handler.send_message(msg)
                        
                        # Notify current player
                        if self.game.current_turn:
                            current_handler = self.clients[self.game.current_turn]
                            msg = Message(
                                MessageType.YOUR_TURN,
                                {"current_turn": self.game.current_turn},
                                self.game.current_turn
                            )
                            current_handler.send_message(msg)
                    else:
                        # Notify waiting for opponent
                        for player_id, handler in self.clients.items():
                            if player_id not in self.ready_players:
                                msg = Message(
                                    MessageType.WAITING_FOR_OPPONENT,
                                    {"message": "Waiting for opponent to be ready"},
                                    player_id
                                )
                                handler.send_message(msg)
                
                elif self.game.state == GameState.WAITING_FOR_PLAYERS:
                    # All players have joined
                    for handler in self.clients.values():
                        msg = Message(
                            MessageType.START_PLACING_SHIPS,
                            {"message": "All players joined. Start placing ships."},
                            handler.player_id
                        )
                        handler.send_message(msg)
    
    def broadcast_attack_result(self, attacker_id: str, result) -> None:
        """Broadcast attack result to both players."""
        # Notify attacker
        attacker_handler = self.clients[attacker_id]
        msg = Message(
            MessageType.ATTACK_RESULT,
            {
                "outcome": result.outcome.name,
                "ship_sunk": result.ship_sunk,
                "game_finished": result.game_finished,
                "attacked_coordinate": result.attacked_coordinate,
            },
            attacker_id
        )
        attacker_handler.send_message(msg)
        
        # Notify defender
        defender_id = result.defender_id
        if defender_id:
            defender_handler = self.clients[defender_id]
            msg = Message(
                MessageType.ATTACK_RESULT,
                {
                    "outcome": result.outcome.name,
                    "ship_sunk": result.ship_sunk,
                    "attacker": attacker_id,
                    "attacked_coordinate": result.attacked_coordinate,
                },
                defender_id
            )
            defender_handler.send_message(msg)
        
        # If game not finished, notify next player
        if not result.game_finished and self.game.current_turn:
            next_player = self.game.current_turn
            next_handler = self.clients[next_player]
            msg = Message(
                MessageType.YOUR_TURN,
                {"current_turn": next_player},
                next_player
            )
            next_handler.send_message(msg)
            
            # Notify other player it's their turn to wait
            other_player = [p for p in self.clients.keys() if p != next_player][0]
            msg = Message(
                MessageType.OPPONENT_TURN,
                {"opponent": next_player},
                other_player
            )
            self.clients[other_player].send_message(msg)
    
    def notify_game_over(self) -> None:
        """Notify players that game is over."""
        winner = self.game.winner
        if not winner:
            return
        
        loser = [p for p in self.clients.keys() if p != winner][0]
        
        result = self.game.get_game_result()
        if not result:
            return
        
        # Notify winner
        msg = Message(
            MessageType.GAME_OVER,
            {
                "result": "WIN",
                "winner": winner,
                "total_moves": result.total_moves,
                "winning_moves": result.winning_moves,
            },
            winner
        )
        self.clients[winner].send_message(msg)
        
        # Notify loser
        msg = Message(
            MessageType.GAME_OVER,
            {
                "result": "LOSS",
                "winner": winner,
                "total_moves": result.total_moves,
            },
            loser
        )
        self.clients[loser].send_message(msg)
