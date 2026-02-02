"""
Enumerations and constants for the Battleship game.
"""

from enum import Enum, auto


class CellState(Enum):
    """Represents the state of a cell on the board."""
    EMPTY = auto()
    SHIP = auto()
    HIT = auto()
    MISS = auto()


class AttackOutcome(Enum):
    """Represents the outcome of an attack."""
    HIT = auto()
    MISS = auto()
    SHIP_SUNK = auto()
    ALREADY_ATTACKED = auto()
    INVALID_COORDINATE = auto()


class GameState(Enum):
    """Represents the state of a game."""
    WAITING_FOR_PLAYERS = auto()
    PLACING_SHIPS = auto()
    IN_PROGRESS = auto()
    FINISHED = auto()


class ShipType(Enum):
    """Represents different types of ships and their sizes."""
    BATTLESHIP = 4
    CRUISER = 3
    DESTROYER = 2
    SUBMARINE = 1

    @property
    def length(self) -> int:
        """Returns the length of the ship."""
        return self.value


class BoardOrientation(Enum):
    """Represents the orientation of a ship on the board."""
    HORIZONTAL = auto()
    VERTICAL = auto()
