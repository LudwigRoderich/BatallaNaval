"""
Protocolo personalizado para el servidor de Batalla Naval.
Define códigos de estado, creación de mensajes y validación.
"""

import time
from typing import Dict, Optional, Tuple


class Protocol:
    """Protocolo para comunicación cliente-servidor en Batalla Naval."""

    CODES = {
        200: "OK",
        
        210: "WAITING_FOR_OPPONENT",
        211: "BOTH_PLAYERS_READY",
        212: "GAME_STARTED",
        213: "WAITING_FOR_SHIPS",
        215: "YOUR_TURN",
        216: "WAITING_FOR_OPPONENT_TURN",
        217: "ATTACK_REGISTERED",
        
        220: "GAME_OVER",

        230: "RECONNECTING",
        231: "RECONNECT_SUCCESS",
        
        400: "BAD_REQUEST",
        401: "INVALID_MESSAGE_FORMAT",
        402: "MISSING_REQUIRED_FIELD",
        
        410: "PLAYER_NOT_FOUND",
        
        420: "GAME_NOT_FOUND",
        422: "GAME_ALREADY_FULL",
        
        430: "INVALID_SHIP_PLACEMENT",
        
        440: "INVALID_COORDINATE",
        
        450: "OPPONENT_DISCONNECTED",
        451: "REQUEST_TIMEOUT",
        
        500: "INTERNAL_SERVER_ERROR"
    }

    MESSAGE_TYPES = {
        "join_game",
        "reconnect",
        "place_ships",
        "attack",
        "surrender",
        "ping",
        "generate_random_placement",
        
        "game_state",
        "attack_result",
        "opponent_move",
        "game_over",
        "error",
        "notification",
    }

    @staticmethod
    def create_message(
        msg_type: str,
        code: int = 200,
        game_id: Optional[str] = None,
        player_id: Optional[str] = None,
        **kwargs
    ) -> Dict:
        """
        Crea un mensaje válido según el protocolo.

        Args:
            msg_type: Tipo de mensaje.
            code: Código de estado.
            game_id: ID de la partida (opcional).
            player_id: ID del jugador (opcional).
            **kwargs: Datos adicionales del mensaje.

        Returns:
            Diccionario con el mensaje formateado.
        """
        message = {
            "type": msg_type,
            "code": code,
            "timestamp": int(time.time() * 1000),
        }
        
        if game_id:
            message["gameId"] = game_id
        if player_id:
            message["playerId"] = player_id
            
        message.update(kwargs)
        return message

    @staticmethod
    def create_error(
        code: int,
        message: Optional[str] = None,
        **kwargs
    ) -> Dict:
        """
        Crea un mensaje de error.

        Args:
            code: Código de error.
            message: Mensaje de error personalizado.
            **kwargs: Datos adicionales.

        Returns:
            Diccionario con el error formateado.
        """
        error_msg = message or Protocol.CODES.get(code, "UNKNOWN_ERROR")
        return {
            "type": "error",
            "code": code,
            "message": error_msg,
            "timestamp": int(time.time() * 1000),
            **kwargs
        }

    @staticmethod
    def validate_message(data: Dict) -> Tuple[bool, str]:
        """
        Valida que un mensaje tenga el formato correcto.

        Args:
            data: Mensaje a validar.

        Returns:
            Tupla (válido: bool, mensaje_error: str).
        """
        if not isinstance(data, dict):
            return False, "Mensaje debe ser un diccionario"

        if "type" not in data:
            return False, "Campo 'type' es obligatorio"

        if data["type"] not in Protocol.MESSAGE_TYPES:
            return False, f"Tipo de mensaje desconocido: {data['type']}"

        return True, ""

    @staticmethod
    def validate_join_message(data: Dict) -> Tuple[bool, str]:
        """
        Valida mensajes de tipo 'join_game'.
        
        Verifica que el mensaje contenga todos los campos obligatorios para
        que un jugador se una a una partida.
        
        Args:
            data: Diccionario con los datos del mensaje a validar.
        
        Returns:
            Tupla (válido: bool, mensaje_error: str). Si válido es True, mensaje_error es vacío.
        """
        required = ["playerName"]
        for field in required:
            if field not in data:
                return False, f"Campo obligatorio faltante: {field}"
        return True, ""

    @staticmethod
    def validate_reconnect_message(data: Dict) -> Tuple[bool, str]:
        """
        Valida mensajes de tipo 'reconnect'.
        
        Verifica que el mensaje contenga los campos necesarios para que un jugador
        se reconecte a una partida existente.
        
        Args:
            data: Diccionario con los datos del mensaje a validar.
        
        Returns:
            Tupla (válido: bool, mensaje_error: str). Si válido es True, mensaje_error es vacío.
        """
        required = ["gameId", "playerId"]
        for field in required:
            if field not in data:
                return False, f"Campo obligatorio faltante: {field}"
        return True, ""

    @staticmethod
    def validate_place_ships_message(data: Dict) -> Tuple[bool, str]:
        """
        Valida mensajes de tipo 'place_ships'.
        
        Verifica que el mensaje contenga todos los campos requeridos para que un jugador
        coloque sus barcos, y que el campo 'ships' sea una lista válida.
        
        Args:
            data: Diccionario con los datos del mensaje a validar.
        
        Returns:
            Tupla (válido: bool, mensaje_error: str). Si válido es True, mensaje_error es vacío.
        """
        required = ["gameId", "playerId", "ships"]
        for field in required:
            if field not in data:
                return False, f"Campo obligatorio faltante: {field}"

        if not isinstance(data["ships"], list):
            return False, "El campo 'ships' debe ser una lista"

        return True, ""

    @staticmethod
    def validate_attack_message(data: Dict) -> Tuple[bool, str]:
        """
        Valida mensajes de tipo 'attack'.
        
        Verifica que el mensaje contenga los campos requeridos para que un jugador
        realice un ataque, incluyendo validación del formato de la coordenada.
        
        Args:
            data: Diccionario con los datos del mensaje a validar.
        
        Returns:
            Tupla (válido: bool, mensaje_error: str). Si válido es True, mensaje_error es vacío.
        """
        required = ["gameId", "playerId", "coordinate"]
        for field in required:
            if field not in data:
                return False, f"Campo obligatorio faltante: {field}"

        coord = data.get("coordinate")
        if not isinstance(coord, dict) or "x" not in coord or "y" not in coord:
            return False, "Coordenada debe tener formato {x, y}"

        return True, ""
