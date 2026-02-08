"""
Protocolo personalizado para el servidor de Batalla Naval.
Define códigos de estado, creación de mensajes y validación.
"""

import time
from typing import Dict, Optional, Tuple


class Protocol:
    """Protocolo para comunicación cliente-servidor en Batalla Naval."""

    # Códigos de estado
    CODES = {
        # Éxito
        200: "OK",
        201: "CREATED",
        
        # Información
        210: "WAITING_FOR_OPPONENT",
        211: "BOTH_PLAYERS_READY",
        212: "GAME_STARTED",
        213: "WAITING_FOR_SHIPS",
        214: "PLACING_SHIPS",
        215: "YOUR_TURN",
        216: "WAITING_FOR_OPPONENT_TURN",
        217: "ATTACK_REGISTERED",
        
        # Fin de juego
        220: "GAME_OVER",
        221: "VICTORY",
        222: "DEFEAT",
        
        # Reconexión
        230: "RECONNECTING",
        231: "RECONNECT_SUCCESS",
        
        # Errores - Validación
        400: "BAD_REQUEST",
        401: "INVALID_MESSAGE_FORMAT",
        402: "MISSING_REQUIRED_FIELD",
        
        # Errores - Jugador
        410: "PLAYER_NOT_FOUND",
        411: "PLAYER_ALREADY_IN_GAME",
        412: "INVALID_PLAYER_ID",
        413: "PLAYER_NOT_READY",
        
        # Errores - Juego
        420: "GAME_NOT_FOUND",
        421: "GAME_NOT_STARTED",
        422: "GAME_ALREADY_FULL",
        423: "GAME_OVER",
        424: "INVALID_MOVE",
        
        # Errores - Barcos
        430: "INVALID_SHIP_PLACEMENT",
        431: "SHIP_OVERLAP",
        432: "INVALID_SHIP_POSITION",
        433: "ALL_SHIPS_REQUIRED",
        
        # Errores - Ataque
        440: "INVALID_COORDINATE",
        441: "COORDINATE_ALREADY_ATTACKED",
        442: "NOT_YOUR_TURN",
        
        # Errores - Conexión
        450: "OPPONENT_DISCONNECTED",
        451: "REQUEST_TIMEOUT",
        452: "CONNECTION_ERROR",
        
        # Errores - Servidor
        500: "INTERNAL_SERVER_ERROR",
        501: "DATABASE_ERROR",
    }

    MESSAGE_TYPES = {
        # Cliente -> Servidor
        "join_game",
        "reconnect",
        "place_ships",
        "attack",
        "surrender",
        "ping",
        
        # Servidor -> Cliente
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
        # Verificar que sea un diccionario
        if not isinstance(data, dict):
            return False, "Mensaje debe ser un diccionario"

        # Verificar campo type
        if "type" not in data:
            return False, "Campo 'type' es obligatorio"

        if data["type"] not in Protocol.MESSAGE_TYPES:
            return False, f"Tipo de mensaje desconocido: {data['type']}"

        return True, ""

    @staticmethod
    def validate_join_message(data: Dict) -> Tuple[bool, str]:
        """Valida mensajes de tipo 'join_game'."""
        required = ["playerId", "playerName"]
        for field in required:
            if field not in data:
                return False, f"Campo obligatorio faltante: {field}"
        return True, ""

    @staticmethod
    def validate_reconnect_message(data: Dict) -> Tuple[bool, str]:
        """Valida mensajes de tipo 'reconnect'."""
        required = ["gameId", "playerId"]
        for field in required:
            if field not in data:
                return False, f"Campo obligatorio faltante: {field}"
        return True, ""

    @staticmethod
    def validate_place_ships_message(data: Dict) -> Tuple[bool, str]:
        """Valida mensajes de tipo 'place_ships'."""
        required = ["gameId", "playerId", "ships"]
        for field in required:
            if field not in data:
                return False, f"Campo obligatorio faltante: {field}"

        if not isinstance(data["ships"], list):
            return False, "El campo 'ships' debe ser una lista"

        return True, ""

    @staticmethod
    def validate_attack_message(data: Dict) -> Tuple[bool, str]:
        """Valida mensajes de tipo 'attack'."""
        required = ["gameId", "playerId", "coordinate"]
        for field in required:
            if field not in data:
                return False, f"Campo obligatorio faltante: {field}"

        coord = data.get("coordinate")
        if not isinstance(coord, dict) or "x" not in coord or "y" not in coord:
            return False, "Coordenada debe tener formato {x, y}"

        return True, ""
