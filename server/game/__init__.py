"""
Battleship game module.

This module contains the core game logic for the Battleship game.
"""

from .ship import Ship, Coordinate
from .board import Board
from .player import Player
from .game import Game
from .enums import (
    CellState,
    AttackOutcome,
    GameState,
    ShipType,
    BoardOrientation,
)
from .results import AttackResult, GameOverResult
from .errors import (
    BattleshipGameError,
    InvalidCoordinateError,
    ShipPlacementError,
    ShipOverlapError,
    InvalidShipError,
    GameStateError,
    PlayerError,
    InvalidAttackError,
)

__all__ = [
    # Classes
    "Ship",
    "Coordinate",
    "Board",
    "Player",
    "Game",
    # Enums
    "CellState",
    "AttackOutcome",
    "GameState",
    "ShipType",
    "BoardOrientation",
    # Results
    "AttackResult",
    "GameOverResult",
    # Exceptions
    "BattleshipGameError",
    "InvalidCoordinateError",
    "ShipPlacementError",
    "ShipOverlapError",
    "InvalidShipError",
    "GameStateError",
    "PlayerError",
    "InvalidAttackError",
]
