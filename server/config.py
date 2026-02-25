"""
Configuración centralizada del servidor de Batalla Naval.
Define parámetros de timeout, límites y otros valores sin necesidad de .env
"""
import logging


logger = logging.getLogger(__name__)


class ServerConfig:
    """
    Configuración centralizada del servidor.
    
    Todos los valores de timeout están en segundos.
    Modifica estos valores para testing rápido vs ambientes de producción.
    """

    TIMEOUT_WAITING_FOR_OPPONENT: int = 120
    TIMEOUT_PLACING_SHIPS: int = 180
    TIMEOUT_PLAYER_TURN: int = 300
    TIMEOUT_RECONNECTION: int = 60
    TIMEOUT_GAME_INACTIVE: int = 3600
    CLEANUP_CHECK_INTERVAL: int = 10
    BOARD_SIZE: int = 10
    WEBSOCKET_HOST: str = '0.0.0.0'
    WEBSOCKET_PORT: int = 8080
    HTTP_HOST: str = '0.0.0.0'
    HTTP_PORT: int = 8000
    MIN_PLAYER_NAME_LENGTH: int = 2
    MAX_PLAYER_NAME_LENGTH: int = 30
    LOG_LEVEL: str = 'INFO'
    LOG_FILE: str = 'logs/server.log'


def get_config() -> ServerConfig:
    """Obtiene la configuración global del servidor."""
    return ServerConfig()

SERVER_HOST = '0.0.0.0'
SERVER_PORT = 8080
SERVER_DEBUG = 'False'
BOARD_SIZE = 10
GAME_TIMEOUT_MINUTES = 30
RECONNECT_TIMEOUT_SECONDS = 300

