"""
Game class for the Battleship game.
"""

from typing import Dict, Optional, Tuple
from .ship import Ship, Coordinate
from .player import Player
from .board import Board
from .enums import GameState, AttackOutcome
from .results import AttackResult, GameOverResult
from .errors import GameStateError, PlayerError, InvalidCoordinateError, GameError


class Game:
    """Manages a Battleship game between two players."""

    def __init__(self, board_size: int = 10) -> None:
        """
        Initialize a game.

        Args:
            board_size: The size of each player's board (default 10x10).
        """
        self._board_size = board_size
        self._players: Dict[str, Player] = {}
        self._state = GameState.WAITING_FOR_PLAYERS
        self._current_turn: Optional[str] = None
        self._move_count = 0
        self._winner: Optional[str] = None

    @property
    def state(self) -> GameState:
        """Returns the current game state."""
        return self._state

    @property
    def players(self) -> Dict[str, Player]:
        """Returns a copy of the players in the game."""
        return self._players.copy()

    @property
    def move_count(self) -> int:
        """Returns the total number of moves made."""
        return self._move_count

    @property
    def current_turn(self) -> Optional[str]:
        """Returns the ID of the player whose turn it is."""
        return self._current_turn

    @property
    def winner(self) -> Optional[str]:
        """Returns the ID of the winning player, or None if game is ongoing."""
        return self._winner

    def add_player(self, player_id: str) -> None:
        """
        Add a player to the game.

        Args:
            player_id: Unique identifier for the player.

        Raises:
            GameStateError: If the game is not in WAITING_FOR_PLAYERS state.
            PlayerError: If the player ID already exists.
        """
        if self._state != GameState.WAITING_FOR_PLAYERS:
            raise GameStateError(
                f"Cannot add player: game is in {self._state.name} state."
            )

        if player_id in self._players:
            raise PlayerError(f"Player '{player_id}' already exists in the game.")

        if len(self._players) >= 2:
            raise PlayerError("Game already has 2 players.")

        self._players[player_id] = Player(player_id, self._board_size)
        print(f"Player '{player_id}' added to the game.")

    def place_ship(self, player_id: str, ship: Ship) -> None:
        """
        Place a ship for a player.

        Args:
            player_id: The ID of the player.
            ship: The ship to place.

        Raises:
            GameStateError: If the game is not in PLACING_SHIPS state.
            PlayerError: If the player doesn't exist or the ship cannot be placed.
        """
        if self._state != GameState.PLACING_SHIPS:
            raise GameStateError(
                f"Cannot place ship: game is in {self._state.name} state."
            )

        if player_id not in self._players:
            raise PlayerError(f"Player '{player_id}' not found in the game.")

        try:
            self._players[player_id].place_ship(ship)
            print(f"Player '{player_id}' placed ship '{ship.ship_id}'.")
        except PlayerError as e:
            raise GameError(
                f"Player '{player_id}' failed to place ship '{ship.ship_id}'"
            ) from e


    def start(self) -> None:
        """
        Start the game.

        Raises:
            GameStateError: If the game is not ready to start.
        """
        if self._state != GameState.WAITING_FOR_PLAYERS:
            raise GameStateError(
                f"Cannot start game: game is in {self._state.name} state."
            )

        if len(self._players) != 2:
            raise GameStateError(
                f"Cannot start game: expected 2 players, got {len(self._players)}."
            )

        if len(self.players) == 2: self._state = GameState.PLACING_SHIPS
        #self._current_turn = self._players.keys().__iter__().__next__()
        print("Game started. Players can now place their ships.")
        #print(f"Current turn: {self._current_turn}")
        #self._state = GameState.PLACING_SHIPS

    def finish_ship_placement(self) -> None:
        """
        Transition from ship placement to game in progress.

        Raises:
            GameStateError: If the game is not in PLACING_SHIPS state.
        """
        if self._state != GameState.PLACING_SHIPS:
            raise GameStateError(
                f"Cannot finish ship placement: game is in {self._state.name} state."
            )
        
        if not self.all_ships_placed():
            raise GameStateError(
                "Cannot finish ship placement: not all players have placed all their ships."
            )

        # Start the game
        self._state = GameState.IN_PROGRESS
        player_ids = list(self._players.keys())
        self._current_turn = player_ids[0]

    def attack(self, attacker_id: str, coord: Coordinate) -> AttackResult:
        """
        Execute an attack from one player to another.

        Args:
            attacker_id: The ID of the attacking player.
            coord: The coordinate to attack.

        Returns:
            An AttackResult object with the outcome.

        Raises:
            GameStateError: If the game is not in progress.
            PlayerError: If the attacker is not in the game or it's not their turn.
            InvalidCoordinateError: If the coordinate is invalid.
        """
        if self._state != GameState.IN_PROGRESS:
            raise GameStateError(
                f"Cannot attack: game is in {self._state.name} state."
            )

        if attacker_id not in self._players:
            raise PlayerError(f"Player '{attacker_id}' not found in the game.")

        if attacker_id != self._current_turn:
            raise PlayerError(
                f"It's not {attacker_id}'s turn. Current turn: {self._current_turn}"
            )

        # Get the defender (the other player)
        defender_id = self._get_other_player(attacker_id)
        defender = self._players[defender_id]

        # Execute the attack
        outcome = defender.receive_attack(coord)

        # Update attacker's tracking board
        self._players[attacker_id].update_tracking_board(coord, outcome)

        # Increment move count
        self._move_count += 1

        # Check if the game is finished
        game_finished = False
        ship_sunk = outcome == AttackOutcome.SHIP_SUNK

        if defender.all_ships_sunk():
            game_finished = True
            self._state = GameState.FINISHED
            self._winner = attacker_id

        # Switch turns (only if attack didn't hit or game is not finished)
        if outcome == AttackOutcome.MISS or outcome == AttackOutcome.ALREADY_ATTACKED:
            self._switch_turn()

        return AttackResult(
            outcome=outcome,
            ship_sunk=ship_sunk,
            game_finished=game_finished,
            defender_id=defender_id,
            attacked_coordinate=str(coord),
        )

    def get_current_turn(self) -> Optional[str]:
        """
        Get the player whose turn it is.

        Returns:
            The ID of the current player, or None if game is not in progress.
        """
        return self._current_turn

    def get_state(self) -> GameState:
        """
        Get the current state of the game.

        Returns:
            The current GameState.
        """
        return self._state

    def is_finished(self) -> bool:
        """
        Check if the game has ended.

        Returns:
            True if the game is finished.
        """
        return self._state == GameState.FINISHED

    def get_winner(self) -> Optional[str]:
        """
        Get the winner of the game.

        Returns:
            The ID of the winning player, or None if the game is not finished.
        """
        return self._winner

    def get_public_state_for(self, player_id: str) -> dict:
        """
        Get the public game state visible to a specific player.

        Args:
            player_id: The ID of the player.

        Returns:
            A dictionary with the public game state.
        """
        if player_id not in self._players:
            raise PlayerError(f"Player '{player_id}' not found in the game.")

        opponent_id = self._get_other_player(player_id)
        opponent_board_state = self._players[opponent_id].get_public_board_state()

        return {
            "game_state": self._state.name,
            "current_turn": self._current_turn,
            "move_count": self._move_count,
            "your_id": player_id,
            "opponent_id": opponent_id,
            "your_ships": len(self._players[player_id].get_ships()),
            "opponent_board": opponent_board_state,
            "opponent_ships_sunk": sum(
                1
                for ship in self._players[opponent_id].get_ships().values()
                if ship.is_sunk()
            ),
            "is_finished": self.is_finished(),
            "winner": self._winner,
        }

    def get_game_result(self) -> Optional[GameOverResult]:
        """
        Get the game result if the game is finished.

        Returns:
            A GameOverResult if the game is finished, None otherwise.
        """
        if not self.is_finished() or self._winner is None:
            return None

        loser_id = self._get_other_player(self._winner)
        winner = self._players[self._winner]

        # Count winning moves (hits + sinks)
        winning_moves = 0
        for coord in winner.tracking_board.get_attacked_coordinates():
            state = winner.tracking_board.get_cell_state(coord)
            from .enums import CellState

            if state == CellState.HIT:
                winning_moves += 1

        ships_saved = len(
            [
                ship
                for ship in winner.get_ships().values()
                if not ship.is_sunk()
            ])

        return GameOverResult(
            winner_id=self._winner,
            loser_id=loser_id,
            total_moves=self._move_count,
            ships_saved=ships_saved,
        )

    def _get_other_player(self, player_id: str) -> str:
        """
        Get the ID of the other player.

        Args:
            player_id: The ID of a player.

        Returns:
            The ID of the other player.

        Raises:
            PlayerError: If the player is not in the game.
        """
        if player_id not in self._players:
            raise PlayerError(f"Player '{player_id}' not found in the game.")

        for pid in self._players:
            if pid != player_id:
                return pid

        raise PlayerError("Game does not have two players.")
    
    def all_ships_placed(self) -> bool:
        """
        Check if all players have placed all their ships.

        Returns:
            True if all players have placed all their ships.
        """
        for player in self._players.values():
            if not player.all_ships_placed():
                return False
        return True

    def _switch_turn(self) -> None:
        """Switch the current turn to the other player."""
        if self._current_turn is not None:
            self._current_turn = self._get_other_player(self._current_turn)

    def __repr__(self) -> str:
        return (
            f"Game(state={self._state.name}, players={len(self._players)}, "
            f"turn={self._current_turn}, moves={self._move_count})"
        )



