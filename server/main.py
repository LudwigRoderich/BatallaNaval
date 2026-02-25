"""
Archivo principal para iniciar el servidor de Batalla Naval.
Inicia tanto el servidor WebSocket como el servidor HTTP con FastAPI.
"""

import os
import logging
import threading
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from network.server import BatallaNavalServer

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(filename)s:%(lineno)d | %(message)s',
    datefmt='%H:%M:%S',
    force=True
)
logger = logging.getLogger(__name__)

# ============================================================
# FASTAPI - CONFIGURACIÓN INICIAL
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ciclo de vida de la aplicación FastAPI."""
    logger.info("FastAPI iniciando...")
    yield
    logger.info("FastAPI deteniendo...")

app = FastAPI(
    title="Batalla Naval Server",
    description="Servidor WebSocket + HTTP para Batalla Naval",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins="*",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["Authorization", "Content-Type"],
    expose_headers=["content-disposition"],
)

@app.get("/api/health")
async def health_check():
    """Verifica que el servidor HTTP está activo."""
    return {
        "status": "ok",
        "message": "Servidor de Batalla Naval activo"
    }

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # Sube dos directorios
static_dir = os.path.join(base_dir, 'client')

if os.path.exists(static_dir) and os.path.isdir(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
else:
    logger.warning(f" Directorio frontend NO encontrado en: {static_dir}")
    logger.warning(f" Por favor asegúrate de que existe el directorio 'client'")

def main():
    """Inicia el servidor de Batalla Naval con WebSocket y FastAPI."""
    
    logger.info("=" * 70)
    logger.info("BATALLA NAVAL - INICIANDO SERVIDOR")
    logger.info("=" * 70)
    
    websocket_server = BatallaNavalServer(host='0.0.0.0', port=8080)
    websocket_thread = threading.Thread(
        target=websocket_server.start_server,
        daemon=True,
        name="WebSocket-Server"
    )
    websocket_thread.start()
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )


if __name__ == "__main__":
    main()

