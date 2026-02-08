#!/usr/bin/env python3
"""
Punto de entrada principal del servidor de Batalla Naval.
Inicia el servidor y maneja la ejecución.
"""

import sys
import logging
from network.server import BatallaNavalServer
from config import SERVER_HOST, SERVER_PORT, LOG_LEVEL, LOG_FILE

# Configurar logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def main():
    """Función principal."""
    try:
        logger.info("=" * 60)
        logger.info("SERVIDOR DE BATALLA NAVAL")
        logger.info("=" * 60)
        
        # Crear y iniciar servidor
        server = BatallaNavalServer(host=SERVER_HOST, port=SERVER_PORT)
        
        logger.info(f"Iniciando servidor en {SERVER_HOST}:{SERVER_PORT}...")
        server.start()
        
    except KeyboardInterrupt:
        logger.info("Servidor interrumpido por el usuario")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error fatal: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
