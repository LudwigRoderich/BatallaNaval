
"""
Board class for the Battleship game.
"""

from typing import Dict, Optional
from .ship import Ship, Coordinate
from .enums import CellState, ShipOrientation
from .errors import InvalidCoordinateError, ShipPlacementError, ShipOverlapError


class Board:
    """Represents a Battleship game board."""

    def __init__(self, size: int = 10) -> None:
        """
        Initialize a board.

        Args:
            size: The size of the square board (default 10x10).

        Raises:
            ValueError: If size is less than 1.
        """
        if size < 1:
            raise ValueError("Board size must be at least 1.")

        self._size = size
        self._cells: Dict[Coordinate, CellState] = {}
        self._ships: Dict[str, Ship] = {}
        self._attacked_coords: set[Coordinate] = set()

        # Initialize all cells as empty
        for x in range(size):
            for y in range(size):
                self._cells[Coordinate(x, y)] = CellState.EMPTY

    @property
    def size(self) -> int:
        """Returns the board size."""
        return self._size

    @property
    def ships(self) -> Dict[str, Ship]:
        """Returns a copy of the ships on the board."""
        return self._ships.copy()

    def is_valid_coordinate(self, coord: Coordinate) -> bool:
        """
        Check if a coordinate is within the board bounds.

        Args:
            coord: The coordinate to validate.

        Returns:
            True if the coordinate is valid.
        """
        return 0 <= coord.x < self._size and 0 <= coord.y < self._size

    def get_cell_state(self, coord: Coordinate) -> CellState:
        """
        Get the state of a cell on the board.

        Args:
            coord: The coordinate of the cell.

        Returns:
            The state of the cell.

        Raises:
            InvalidCoordinateError: If the coordinate is out of bounds.
        """
        if not self.is_valid_coordinate(coord):
            raise InvalidCoordinateError(
                f"Coordinate {coord} is out of bounds for board size {self._size}."
            )
        return self._cells[coord]

    def set_cell_state(self, coord: Coordinate, state: CellState) -> None:
        """
        Set the state of a cell on the board.

        Args:
            coord: The coordinate of the cell.
            state: The new state for the cell.

        Raises:
            InvalidCoordinateError: If the coordinate is out of bounds.
        """
        if not self.is_valid_coordinate(coord):
            raise InvalidCoordinateError(
                f"Coordinate {coord} is out of bounds for board size {self._size}."
            )
        self._cells[coord] = state

    def place_ship(self, ship: Ship) -> None:
        """
        Place a ship on the board.

        Args:
            ship: The ship to place.

        Raises:
            InvalidCoordinateError: If any ship position is out of bounds.
            ShipOverlapError: If the ship overlaps with an existing ship.
        """
        # Validate all positions
        for coord in ship.positions:
            if not self.is_valid_coordinate(coord):
                raise InvalidCoordinateError(
                    f"Ship position {coord} is out of bounds."
                )

        # Check for overlaps
        for coord in ship.positions:
            if self._cells[coord] == CellState.SHIP:
                raise ShipOverlapError(
                    f"Cannot place ship '{ship.ship_id}': overlap at {coord}."
                )
            
        # Validate ship coordinates based on its type (for its lenght) and orientation
        if not self.are_coordinates_valid_for_ship(ship):
            raise ShipPlacementError(
                f"Ship '{ship.ship_id}' has invalid coordinates for its type {ship.ship_type.name}."
            )

        # Check if that type of ship is already placed (only one per type allowed)
        for existing_ship in self._ships.values():
            if existing_ship.ship_type == ship.ship_type:
                raise ShipPlacementError(
                    f"Ship of type '{ship.ship_type.name}' is already placed on the board."
                )

        # Place the ship
        self._ships[ship.ship_id] = ship
        for coord in ship.positions:
            self._cells[coord] = CellState.SHIP

    def remove_ship(self, ship_id: str) -> Optional[Ship]:
        """
        Remove a ship from the board.

        Args:
            ship_id: The ID of the ship to remove.

        Returns:
            The removed ship, or None if not found.
        """
        ship = self._ships.pop(ship_id, None)
        if ship:
            for coord in ship.positions:
                self._cells[coord] = CellState.EMPTY
        return ship

    def get_ship_at(self, coord: Coordinate) -> Optional[Ship]:
        """
        Get the ship at a specific coordinate.

        Args:
            coord: The coordinate to check.

        Returns:
            The ship at that coordinate, or None if no ship is there.
        """
        for ship in self._ships.values():
            if ship.occupies(coord):
                return ship
        return None

    def mark_hit(self, coord: Coordinate) -> bool:
        """
        Mark a coordinate as hit.

        Args:
            coord: The coordinate that was hit.

        Returns:
            True if a ship was hit, False otherwise.

        Raises:
            InvalidCoordinateError: If the coordinate is out of bounds.
        """
        if not self.is_valid_coordinate(coord):
            raise InvalidCoordinateError(
                f"Coordinate {coord} is out of bounds for board size {self._size}."
            )

        self._attacked_coords.add(coord)
        ship = self.get_ship_at(coord)

        if ship:
            ship.register_hit(coord)
            self._cells[coord] = CellState.HIT
            return True
        else:
            self._cells[coord] = CellState.MISS
            return False

    def mark_miss(self, coord: Coordinate) -> None:
        """
        Mark a coordinate as missed (deprecated, use mark_hit instead).

        Args:
            coord: The coordinate that was missed.

        Raises:
            InvalidCoordinateError: If the coordinate is out of bounds.
        """
        if not self.is_valid_coordinate(coord):
            raise InvalidCoordinateError(
                f"Coordinate {coord} is out of bounds for board size {self._size}."
            )
        self._attacked_coords.add(coord)
        if self._cells[coord] == CellState.EMPTY:
            self._cells[coord] = CellState.MISS

    def has_been_attacked(self, coord: Coordinate) -> bool:
        """
        Check if a coordinate has been attacked.

        Args:
            coord: The coordinate to check.

        Returns:
            True if the coordinate has been attacked.
        """
        return coord in self._attacked_coords

    def all_ships_sunk(self) -> bool:
        """
        Check if all ships on the board are sunk.

        Returns:
            True if all ships are sunk, False otherwise.
        """
        return all(ship.is_sunk() for ship in self._ships.values())

    def get_attacked_coordinates(self) -> set[Coordinate]:
        """
        Get all attacked coordinates.

        Returns:
            A set of all coordinates that have been attacked.
        """
        return self._attacked_coords.copy()
    
    def are_coordinates_valid_for_ship(self, ship: Ship) -> bool:
        """
        Check if the ship's coordinates are valid (in a straight line and match ship length).

        Args:
            ship: The ship to validate.
        Returns:
            True if the coordinates are valid for the ship type, False otherwise.
        """
        coords = sorted(ship.positions, key=lambda c: (c.x, c.y))
        if len(coords) != ship.ship_type.length:
            return False
        
        if ship._orientation == ShipOrientation.HORIZONTAL:
            # Verify that all y coordinates are the same and x coordinates are consecutive
            return all(coord.y == coords[0].y for coord in coords) and \
                   all(coords[i].x == coords[0].x + i for i in range(len(coords)))
        elif ship._orientation == ShipOrientation.VERTICAL:
            # Verify that all x coordinates are the same and y coordinates are consecutive
            return all(coord.x == coords[0].x for coord in coords) and \
                   all(coords[i].y == coords[0].y + i for i in range(len(coords)))
        else:
            return False

    def __repr__(self) -> str:
        return f"Board(size={self._size}, ships={len(self._ships)}, attacks={len(self._attacked_coords)})"
