
"""
Ship class for the Battleship game.
"""

from dataclasses import dataclass
from typing import Set
from .enums import ShipType


@dataclass(frozen=True)
class Coordinate:
    """Represents a coordinate on the board."""
    x: int
    y: int

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Coordinate):
            return NotImplemented
        return self.x == other.x and self.y == other.y

    def __hash__(self) -> int:
        return hash((self.x, self.y))

    def __repr__(self) -> str:
        return f"Coordinate({self.x}, {self.y})"


class Ship:
    """Represents a ship in the Battleship game."""

    def __init__(
        self,
        ship_id: str,
        ship_type: ShipType,
        positions: Set[Coordinate]
    ) -> None:
        """
        Initialize a ship.

        Args:
            ship_id: Unique identifier for the ship.
            ship_type: Type of ship (determines size and behavior).
            positions: Set of coordinates the ship occupies.

        Raises:
            ValueError: If the number of positions doesn't match the ship type's length.
        """
        if len(positions) != ship_type.length:
            raise ValueError(
                f"Ship '{ship_id}' of type {ship_type.name} requires "
                f"{ship_type.length} positions, but {len(positions)} were provided."
            )

        self._ship_id = ship_id
        self._ship_type = ship_type
        self._positions = frozenset(positions)
        self._hits: Set[Coordinate] = set()

    @property
    def ship_id(self) -> str:
        """Returns the ship's unique identifier."""
        return self._ship_id

    @property
    def ship_type(self) -> ShipType:
        """Returns the ship's type."""
        return self._ship_type

    @property
    def positions(self) -> frozenset[Coordinate]:
        """Returns the coordinates occupied by the ship."""
        return self._positions

    @property
    def hits(self) -> Set[Coordinate]:
        """Returns the set of coordinates where the ship has been hit."""
        return self._hits.copy()

    def register_hit(self, coord: Coordinate) -> bool:
        """
        Register a hit on the ship at the given coordinate.

        Args:
            coord: The coordinate to hit.

        Returns:
            True if the hit was registered (coordinate belongs to ship),
            False otherwise.
        """
        if coord in self._positions:
            self._hits.add(coord)
            return True
        return False

    def is_hit_at(self, coord: Coordinate) -> bool:
        """
        Check if the ship has been hit at a specific coordinate.

        Args:
            coord: The coordinate to check.

        Returns:
            True if the ship has been hit at this coordinate.
        """
        return coord in self._hits

    def is_sunk(self) -> bool:
        """
        Check if the ship is sunk (all positions have been hit).

        Returns:
            True if the ship is sunk.
        """
        return len(self._hits) == len(self._positions)

    def occupies(self, coord: Coordinate) -> bool:
        """
        Check if the ship occupies a specific coordinate.

        Args:
            coord: The coordinate to check.

        Returns:
            True if the ship occupies this coordinate.
        """
        return coord in self._positions

    def health(self) -> int:
        """
        Get the ship's remaining health (unhit positions).

        Returns:
            Number of unhit positions.
        """
        return len(self._positions) - len(self._hits)

    def __repr__(self) -> str:
        return (
            f"Ship(id='{self._ship_id}', type={self._ship_type.name}, "
            f"health={self.health()}/{len(self._positions)})"
        )
