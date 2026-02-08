"""
Configuración del servidor de Batalla Naval.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# Configuración del servidor
SERVER_HOST = os.getenv('SERVER_HOST', '0.0.0.0')
SERVER_PORT = int(os.getenv('SERVER_PORT', 8080))
SERVER_DEBUG = os.getenv('SERVER_DEBUG', 'False').lower() == 'true'

# Configuración del juego
BOARD_SIZE = int(os.getenv('BOARD_SIZE', 10))
GAME_TIMEOUT_MINUTES = int(os.getenv('GAME_TIMEOUT_MINUTES', 30))
RECONNECT_TIMEOUT_SECONDS = int(os.getenv('RECONNECT_TIMEOUT_SECONDS', 300))

# Configuración de logging
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FILE = os.getenv('LOG_FILE', 'logs/server.log')

# Crear directorio de logs si no existe
os.makedirs(os.path.dirname(LOG_FILE) if os.path.dirname(LOG_FILE) else '.', exist_ok=True)

# Configuración de WebSocket
WS_HEARTBEAT_INTERVAL = int(os.getenv('WS_HEARTBEAT_INTERVAL', 30))
WS_MAX_MESSAGE_SIZE = int(os.getenv('WS_MAX_MESSAGE_SIZE', 65536))
