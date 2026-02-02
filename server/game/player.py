
"""
Player class for the Battleship game.
"""

from typing import Optional, Dict
from .ship import Ship, Coordinate
from .board import Board
from .enums import AttackOutcome
from .errors import PlayerError, InvalidCoordinateError


class Player:
    """Represents a player in the Battleship game."""

    def __init__(self, player_id: str, board_size: int = 10) -> None:
        """
        Initialize a player.

        Args:
            player_id: Unique identifier for the player.
            board_size: The size of the player's board (default 10x10).
        """
        self._player_id = player_id
        self._board = Board(board_size)
        self._tracking_board = Board(board_size)  # To track opponent's board state

    @property
    def player_id(self) -> str:
        """Returns the player's unique identifier."""
        return self._player_id

    @property
    def board(self) -> Board:
        """Returns the player's board."""
        return self._board

    @property
    def tracking_board(self) -> Board:
        """Returns the player's tracking board (for opponent's board state)."""
        return self._tracking_board

    def place_ship(self, ship: Ship) -> None:
        """
        Place a ship on the player's board.

        Args:
            ship: The ship to place.

        Raises:
            PlayerError: If the ship cannot be placed.
        """
        try:
            self._board.place_ship(ship)
        except Exception as e:
            raise PlayerError(f"Cannot place ship '{ship.ship_id}': {str(e)}")

    def receive_attack(self, coord: Coordinate) -> AttackOutcome:
        """
        Process an incoming attack on the player's board.

        Args:
            coord: The coordinate being attacked.

        Returns:
            The outcome of the attack.

        Raises:
            InvalidCoordinateError: If the coordinate is out of bounds.
        """
        if not self._board.is_valid_coordinate(coord):
            return AttackOutcome.INVALID_COORDINATE

        if self._board.has_been_attacked(coord):
            return AttackOutcome.ALREADY_ATTACKED

        # Mark the attack
        hit = self._board.mark_hit(coord)

        if hit:
            ship = self._board.get_ship_at(coord)
            if ship and ship.is_sunk():
                return AttackOutcome.SHIP_SUNK
            return AttackOutcome.HIT
        else:
            return AttackOutcome.MISS

    def update_tracking_board(
        self,
        coord: Coordinate,
        outcome: AttackOutcome
    ) -> None:
        """
        Update the player's tracking board based on an attack outcome.

        Args:
            coord: The coordinate that was attacked.
            outcome: The outcome of the attack.
        """
        from .enums import CellState

        if outcome == AttackOutcome.HIT or outcome == AttackOutcome.SHIP_SUNK:
            self._tracking_board.set_cell_state(coord, CellState.HIT)
        elif outcome == AttackOutcome.MISS:
            self._tracking_board.set_cell_state(coord, CellState.MISS)

    def all_ships_sunk(self) -> bool:
        """
        Check if all the player's ships are sunk.

        Returns:
            True if all ships are sunk.
        """
        return self._board.all_ships_sunk()

    def has_ship_at(self, coord: Coordinate) -> bool:
        """
        Check if the player has a ship at a specific coordinate.

        Args:
            coord: The coordinate to check.

        Returns:
            True if there's a ship at this coordinate.
        """
        return self._board.get_ship_at(coord) is not None

    def get_public_board_state(self) -> Dict:
        """
        Get the public state of the player's board (what opponents can see).

        Returns:
            A dictionary representing the board state visible to other players.
        """
        from .enums import CellState

        board_state = {}
        for coord in self._board._cells:
            state = self._board.get_cell_state(coord)
            if state == CellState.SHIP:
                # Hide ship locations from public view
                board_state[str(coord)] = "unknown"
            elif state == CellState.HIT:
                board_state[str(coord)] = "hit"
            elif state == CellState.MISS:
                board_state[str(coord)] = "miss"
            else:
                board_state[str(coord)] = "empty"

        return board_state

    def get_ships(self) -> Dict[str, Ship]:
        """
        Get all ships placed on the player's board.

        Returns:
            A dictionary of ship_id to Ship objects.
        """
        return self._board.ships

    def __repr__(self) -> str:
        ships_count = len(self._board.ships)
        return f"Player(id='{self._player_id}', ships={ships_count})"
