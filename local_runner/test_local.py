"""
Quick test to validate the game logic and local_runner setup.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from server.game import (
    Game, Player, Ship, Coordinate, ShipType,
    GameState, AttackOutcome, AttackResult
)


def test_game_logic():
    """Test the complete game flow."""
    print("=" * 60)
    print("BATTLESHIP GAME LOGIC TEST")
    print("=" * 60)
    
    # Create game
    print("\n1. Creating game...")
    game = Game(board_size=10)
    assert game.state == GameState.WAITING_FOR_PLAYERS
    print("   ✓ Game created in WAITING_FOR_PLAYERS state")
    
    # Add players
    print("\n2. Adding players...")
    game.add_player("Alice")
    game.add_player("Bob")
    print("   ✓ Players added")
    
    # Start game (transitions to PLACING_SHIPS)
    print("\n3. Starting game...")
    game.start()
    assert game.state == GameState.PLACING_SHIPS
    print("   ✓ Game transitioned to PLACING_SHIPS")
    
    # Place ships for Alice
    print("\n4. Placing Alice's ships...")
    alice_positions = {Coordinate(0, 0), Coordinate(0, 1), Coordinate(0, 2), Coordinate(0, 3)}
    alice_battleship = Ship("alice_ship1", ShipType.BATTLESHIP, alice_positions)
    game.place_ship("Alice", alice_battleship)
    print("   ✓ Alice's battleship placed")
    
    # Place ships for Bob
    print("\n5. Placing Bob's ships...")
    bob_positions = {Coordinate(5, 5), Coordinate(5, 6), Coordinate(5, 7), Coordinate(5, 8)}
    bob_battleship = Ship("bob_ship1", ShipType.BATTLESHIP, bob_positions)
    game.place_ship("Bob", bob_battleship)
    print("   ✓ Bob's battleship placed")
    
    # Finish ship placement
    print("\n6. Finishing ship placement...")
    game.finish_ship_placement()
    assert game.state == GameState.IN_PROGRESS
    assert game.current_turn is not None
    print(f"   ✓ Game started. Current turn: {game.current_turn}")
    
    # Execute attacks
    print("\n7. Executing attacks...")
    current_player = game.current_turn
    opponent = "Bob" if current_player == "Alice" else "Alice"
    
    # Attack 1: Miss
    result = game.attack(current_player, Coordinate(1, 1))
    assert result.outcome == AttackOutcome.MISS
    print(f"   ✓ Attack by {current_player} on (1, 1): MISS")
    
    # Attack 2: Hit (opponent's turn now)
    current_player = game.current_turn
    opponent_ship_pos = list(game.players[opponent].board.ships.values())[0].positions
    hit_coord = list(opponent_ship_pos)[0]
    result = game.attack(current_player, hit_coord)
    assert result.outcome == AttackOutcome.HIT
    print(f"   ✓ Attack by {current_player} on {hit_coord}: HIT")
    
    # Continue attacking to sink opponent's ship
    print("\n8. Sinking ships...")
    ship_positions = list(opponent_ship_pos)
    for coord in ship_positions[1:]:
        current_player = game.current_turn
        result = game.attack(current_player, coord)
        if coord == ship_positions[-1]:
            assert result.outcome == AttackOutcome.SHIP_SUNK
            print(f"   ✓ Ship sunk!")
        else:
            assert result.outcome == AttackOutcome.HIT
    
    # Game should be finished
    print("\n9. Checking game state...")
    assert game.is_finished()
    assert game.winner is not None
    print(f"   ✓ Game finished. Winner: {game.winner}")
    
    # Get game result
    result = game.get_game_result()
    assert result is not None
    print(f"   ✓ Total moves: {result.total_moves}")
    print(f"   ✓ Winning moves: {result.winning_moves}")
    
    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED!")
    print("=" * 60)


def test_protocol():
    """Test the protocol."""
    print("\n" + "=" * 60)
    print("PROTOCOL TEST")
    print("=" * 60)
    
    from local_runner.protocol import (
        Message, MessageType,
        create_connect_message,
        create_place_ship_message,
        create_attack_message
    )
    
    # Test message serialization
    print("\n1. Testing message serialization...")
    msg = create_connect_message("TestPlayer")
    json_str = msg.to_json()
    print(f"   ✓ Serialized: {json_str[:50]}...")
    
    # Test message deserialization
    print("\n2. Testing message deserialization...")
    msg2 = Message.from_json(json_str)
    assert msg2.msg_type == MessageType.CONNECT
    assert msg2.data.get("player_name") == "TestPlayer"
    print("   ✓ Deserialized correctly")
    
    # Test place ship message
    print("\n3. Testing place ship message...")
    ship_msg = create_place_ship_message("ship1", "BATTLESHIP", [(0, 0), (0, 1), (0, 2), (0, 3)])
    json_str = ship_msg.to_json()
    ship_msg2 = Message.from_json(json_str)
    assert ship_msg2.msg_type == MessageType.PLACE_SHIP
    print("   ✓ Ship message works")
    
    # Test attack message
    print("\n4. Testing attack message...")
    attack_msg = create_attack_message(5, 5)
    json_str = attack_msg.to_json()
    attack_msg2 = Message.from_json(json_str)
    assert attack_msg2.msg_type == MessageType.ATTACK
    assert attack_msg2.data.get("x") == 5
    print("   ✓ Attack message works")
    
    print("\n" + "=" * 60)
    print("✅ PROTOCOL TESTS PASSED!")
    print("=" * 60)


if __name__ == "__main__":
    try:
        test_game_logic()
        test_protocol()
        
        print("\n🎉 ALL TESTS COMPLETED SUCCESSFULLY!\n")
        print("Next steps:")
        print("1. Open 3 terminals")
        print("2. Terminal 1: python -m local_runner.run_console server")
        print("3. Terminal 2: python -m local_runner.run_console client --name Alice")
        print("4. Terminal 3: python -m local_runner.run_console client --name Bob")
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
