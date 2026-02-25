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
    AIRCRAFT_CARRIER = auto()
    BATTLESHIP = auto()
    CRUISER = auto()
    DESTROYER = auto()
    SUBMARINE = auto()

    @property
    def length(self) -> int:
        return {
            ShipType.AIRCRAFT_CARRIER: 5,
            ShipType.BATTLESHIP: 4,
            ShipType.CRUISER: 3,
            ShipType.DESTROYER: 3,
            ShipType.SUBMARINE: 2,
        }[self]


class ShipOrientation(Enum):
    """Represents the orientation of a ship on the board."""
    HORIZONTAL = auto()
    VERTICAL = auto()
