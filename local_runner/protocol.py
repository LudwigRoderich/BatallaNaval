"""
Communication protocol for local Battleship game.
"""

import json
from dataclasses import asdict
from typing import Any, Dict, Union
from enum import Enum


class MessageType(Enum):
    """Types of messages in the protocol."""
    # Client -> Server
    CONNECT = "CONNECT"
    PLACE_SHIP = "PLACE_SHIP"
    READY = "READY"
    ATTACK = "ATTACK"
    DISCONNECT = "DISCONNECT"
    
    # Server -> Client
    PLAYER_REGISTERED = "PLAYER_REGISTERED"
    WAITING_FOR_OPPONENT = "WAITING_FOR_OPPONENT"
    OPPONENT_JOINED = "OPPONENT_JOINED"
    START_PLACING_SHIPS = "START_PLACING_SHIPS"
    SHIP_PLACED = "SHIP_PLACED"
    SHIP_PLACEMENT_ERROR = "SHIP_PLACEMENT_ERROR"
    ALL_READY = "ALL_READY"
    GAME_STARTED = "GAME_STARTED"
    YOUR_TURN = "YOUR_TURN"
    OPPONENT_TURN = "OPPONENT_TURN"
    ATTACK_RESULT = "ATTACK_RESULT"
    GAME_OVER = "GAME_OVER"
    ERROR = "ERROR"


class Message:
    """Represents a protocol message."""
    
    def __init__(
        self,
        msg_type: MessageType,
        data: Dict[str, Any] | None = None,
        player_id: str | None = None
    ) -> None:
        self.msg_type = msg_type
        self.data = data or {}
        self.player_id = player_id
    
    def to_json(self) -> str:
        """Convert message to JSON string."""
        return json.dumps({
            "type": self.msg_type.value,
            "player_id": self.player_id,
            "data": self.data
        })
    
    @classmethod
    def from_json(cls, json_str: str) -> "Message":
        """Create message from JSON string."""
        data = json.loads(json_str)
        return cls(
            msg_type=MessageType(data["type"]),
            data=data.get("data", {}),
            player_id=data.get("player_id")
        )
    
    def __repr__(self) -> str:
        return f"Message({self.msg_type.value}, player={self.player_id})"


def create_connect_message(player_name: str) -> Message:
    """Create a CONNECT message."""
    return Message(MessageType.CONNECT, {"player_name": player_name})


def create_place_ship_message(
    ship_id: str,
    ship_type: str,
    positions: list[tuple[int, int]]
) -> Message:
    """Create a PLACE_SHIP message."""
    return Message(
        MessageType.PLACE_SHIP,
        {
            "ship_id": ship_id,
            "ship_type": ship_type,
            "positions": positions
        }
    )


def create_attack_message(x: int, y: int) -> Message:
    """Create an ATTACK message."""
    return Message(
        MessageType.ATTACK,
        {"x": x, "y": y}
    )


def create_ready_message() -> Message:
    """Create a READY message."""
    return Message(MessageType.READY, {})


def create_disconnect_message() -> Message:
    """Create a DISCONNECT message."""
    return Message(MessageType.DISCONNECT, {})
