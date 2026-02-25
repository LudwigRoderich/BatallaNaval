"""
Configuración centralizada del servidor de Batalla Naval.
Define parámetros de timeout, límites y otros valores sin necesidad de .env
"""

import os
import logging
from dotenv import load_dotenv

# Intentar cargar .env si existe
try:
    load_dotenv()
except:
    pass

logger = logging.getLogger(__name__)


class ServerConfig:
    """
    Configuración centralizada del servidor.
    
    Todos los valores de timeout están en segundos.
    Modifica estos valores para testing rápido vs ambientes de producción.
    """

    TIMEOUT_WAITING_FOR_OPPONENT: int = int(os.getenv('TIMEOUT_WAITING_FOR_OPPONENT', 120))
    TIMEOUT_PLACING_SHIPS: int = int(os.getenv('TIMEOUT_PLACING_SHIPS', 180))
    TIMEOUT_PLAYER_TURN: int = int(os.getenv('TIMEOUT_PLAYER_TURN', 300))
    TIMEOUT_RECONNECTION: int = int(os.getenv('TIMEOUT_RECONNECTION', 60))
    TIMEOUT_GAME_INACTIVE: int = int(os.getenv('TIMEOUT_GAME_INACTIVE', 3600))
    CLEANUP_CHECK_INTERVAL: int = 10
    BOARD_SIZE: int = 10
    WEBSOCKET_HOST: str = '0.0.0.0'
    WEBSOCKET_PORT: int = 8080
    HTTP_HOST: str = '0.0.0.0'
    HTTP_PORT: int = 8000
    MIN_PLAYER_NAME_LENGTH: int = 2
    MAX_PLAYER_NAME_LENGTH: int = 30
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE: str = os.getenv('LOG_FILE', 'logs/server.log')


def get_config() -> ServerConfig:
    """Obtiene la configuración global del servidor."""
    return ServerConfig()

SERVER_HOST = os.getenv('SERVER_HOST', '0.0.0.0')
SERVER_PORT = int(os.getenv('SERVER_PORT', 8080))
SERVER_DEBUG = os.getenv('SERVER_DEBUG', 'False').lower() == 'true'
BOARD_SIZE = int(os.getenv('BOARD_SIZE', 10))
GAME_TIMEOUT_MINUTES = int(os.getenv('GAME_TIMEOUT_MINUTES', 30))
RECONNECT_TIMEOUT_SECONDS = int(os.getenv('RECONNECT_TIMEOUT_SECONDS', 300))

