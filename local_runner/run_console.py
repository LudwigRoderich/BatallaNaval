"""
Battleship Console Game - Interactive local play
Run in 3 terminals: one for server, two for players
"""

import argparse
import sys
import threading
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from server.game import ShipType, Coordinate
from .server import BattleshipServer
from .client import BattleshipClient
from protocol import MessageType


def run_server() -> None:
    """Run the game server."""
    print("=" * 60)
    print("BATTLESHIP SERVER")
    print("=" * 60)
    
    server = BattleshipServer(host="localhost", port=5000)
    server.start()


def display_board(size: int = 10) -> str:
    """Display an empty board for reference."""
    board = "\n     "
    board += "".join(f"{i:2}" for i in range(size))
    board += "\n"
    for y in range(size):
        board += f"  {y:2} "
        board += "".join(f" ." for _ in range(size))
        board += "\n"
    return board


def get_ship_positions(ship_type: ShipType) -> list[tuple[int, int]]:
    """Interactively get ship positions from player."""
    print(f"\n📍 Placing {ship_type.name} (size: {ship_type.length})")
    print(display_board())
    
    positions = []
    for i in range(ship_type.length):
        while True:
            try:
                coords = input(f"  Position {i+1}/{ship_type.length} (x y): ").strip().split()
                x, y = int(coords[0]), int(coords[1])
                
                if not (0 <= x < 10 and 0 <= y < 10):
                    print("  ❌ Out of bounds! Try again (0-9)")
                    continue
                
                if (x, y) in positions:
                    print("  ❌ Position already used! Try again")
                    continue
                
                positions.append((x, y))
                break
            except (ValueError, IndexError):
                print("  ❌ Invalid format. Use: x y (e.g., 3 5)")
    
    return positions


def run_client(player_name: str) -> None:
    """Run a game client for a player."""
    print("=" * 60)
    print(f"BATTLESHIP CLIENT - {player_name}")
    print("=" * 60)
    
    client = BattleshipClient(player_name)
    
    # Connect to server
    if not client.connect():
        print("Failed to connect to server")
        return
    
    # Wait for START_PLACING_SHIPS message in a separate thread
    def message_listener():
        while client.connected:
            msg = client.receive_message()
            if msg:
                if msg.msg_type == MessageType.START_PLACING_SHIPS:
                    print(f"\n✓ {msg.data.get('message')}")
                elif msg.msg_type == MessageType.SHIP_PLACED:
                    print(f"✓ {msg.data.get('message')}")
                elif msg.msg_type == MessageType.WAITING_FOR_OPPONENT:
                    print(f"⏳ {msg.data.get('message')}")
                elif msg.msg_type == MessageType.GAME_STARTED:
                    print(f"\n🎮 {msg.data.get('message')}\n")
                elif msg.msg_type == MessageType.YOUR_TURN:
                    print(f"\n>>> YOUR TURN <<<\n")
                    # This is where attack input would happen
                elif msg.msg_type == MessageType.OPPONENT_TURN:
                    print(f"⏳ {msg.data.get('message')}")
                elif msg.msg_type == MessageType.ATTACK_RESULT:
                    outcome = msg.data.get("outcome")
                    coord = msg.data.get("attacked_coordinate")
                    print(f"Attack result: {outcome} at {coord}")
                    if msg.data.get("ship_sunk"):
                        print("💥 SHIP SUNK!")
                elif msg.msg_type == MessageType.GAME_OVER:
                    result = msg.data.get("result")
                    if result == "WIN":
                        print("\n🎉 YOU WIN! 🎉\n")
                    else:
                        print(f"\n😢 You lost. Winner: {msg.data.get('winner')}\n")
                    break
                elif msg.msg_type == MessageType.ERROR:
                    print(f"❌ ERROR: {msg.data.get('error')}")
    
    listener_thread = threading.Thread(target=message_listener, daemon=True)
    listener_thread.start()
    
    # Interactive ship placement
    print("\n🚢 SHIP PLACEMENT PHASE")
    print("Place your ships on a 10x10 board")
    
    ships = [
        ("ship_1", ShipType.BATTLESHIP),
        ("ship_2", ShipType.CRUISER),
        ("ship_3", ShipType.DESTROYER),
        ("ship_4", ShipType.SUBMARINE),
    ]
    
    for ship_id, ship_type in ships:
        positions = get_ship_positions(ship_type)
        if not client.place_ship(ship_id, ship_type, positions):
            print(f"Failed to place {ship_type.name}, exiting")
            return
        time.sleep(0.5)
    
    # Ready up
    print("\n✓ All ships placed!")
    client.send_ready()
    print("⏳ Waiting for opponent and game start...")
    
    # Wait for game to start and handle attacks
    while client.connected:
        try:
            # Check if it's our turn by waiting for YOUR_TURN message
            time.sleep(0.1)
            
            # Simple check - in real implementation, use event/condition variable
            # For now, we'll handle attacks interactively
        except KeyboardInterrupt:
            break
    
    client.disconnect()


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Battleship Local Game")
    parser.add_argument(
        "mode",
        choices=["server", "client"],
        help="Run as server or client"
    )
    parser.add_argument(
        "-n", "--name",
        type=str,
        default=None,
        help="Player name (required for client mode)"
    )
    
    args = parser.parse_args()
    
    if args.mode == "server":
        run_server()
    else:  # client
        if not args.name:
            print("Error: --name is required for client mode")
            print("Usage: python run_console.py client --name YourName")
            sys.exit(1)
        
        run_client(args.name)


if __name__ == "__main__":
    main()
