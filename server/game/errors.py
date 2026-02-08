"""
Custom exceptions for the Battleship game.
"""


class BattleshipGameError(Exception):
    """Base exception for all game-related errors."""
    pass


class InvalidCoordinateError(BattleshipGameError):
    """Raised when a coordinate is out of bounds or invalid."""
    pass


class ShipPlacementError(BattleshipGameError):
    """Raised when a ship cannot be placed on the board."""
    pass


class ShipOverlapError(ShipPlacementError):
    """Raised when ships overlap on the board."""
    pass


class InvalidShipError(BattleshipGameError):
    """Raised when ship configuration is invalid."""
    pass


class GameStateError(BattleshipGameError):
    """Raised when an action is not allowed in the current game state."""
    pass


class PlayerError(BattleshipGameError):
    """Raised when there's an issue with player operations."""
    pass


class InvalidAttackError(BattleshipGameError):
    """Raised when an attack cannot be executed."""
    pass

class GameError(BattleshipGameError):
    """Raised for general game errors."""
    pass