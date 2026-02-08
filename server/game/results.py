"""
Result classes for the Battleship game.
"""

from dataclasses import dataclass
from typing import Optional
from .enums import AttackOutcome


@dataclass
class AttackResult:
    """Represents the result of an attack."""

    outcome: AttackOutcome
    """The outcome of the attack (hit, miss, sunk, etc)."""

    ship_sunk: bool
    """Whether a ship was sunk by this attack."""

    game_finished: bool
    """Whether the game ended as a result of this attack."""

    defender_id: Optional[str] = None
    """The ID of the player who was attacked."""

    attacked_coordinate: Optional[str] = None
    """The coordinate that was attacked."""

    def __repr__(self) -> str:
        return (
            f"AttackResult(outcome={self.outcome.name}, "
            f"ship_sunk={self.ship_sunk}, game_finished={self.game_finished})"
        )

    def to_dict(self) -> dict:
        """
        Convert the attack result to a dictionary.

        Returns:
            A dictionary representation of the attack result.
        """
        return {
            "outcome": self.outcome.name,
            "ship_sunk": self.ship_sunk,
            "game_finished": self.game_finished,
            "defender_id": self.defender_id,
            "attacked_coordinate": self.attacked_coordinate,
        }


@dataclass
class GameOverResult:
    """Represents the result when a game ends."""

    winner_id: str
    """The ID of the winning player."""

    loser_id: str
    """The ID of the losing player."""

    total_moves: int
    """Total number of moves made in the game."""

    winning_moves: int
    """Number of moves made by the winner."""

    def __repr__(self) -> str:
        return (
            f"GameOverResult(winner_id='{self.winner_id}', "
            f"loser_id='{self.loser_id}', total_moves={self.total_moves}, "
            f"winning_moves={self.winning_moves})"
        )

    def to_dict(self) -> dict:
        """
        Convert the game over result to a dictionary.

        Returns:
            A dictionary representation of the game over result.
        """
        return {
            "winner_id": self.winner_id,
            "loser_id": self.loser_id,
            "total_moves": self.total_moves,
            "winning_moves": self.winning_moves,
        }
