# Servidor de Batalla Naval

Servidor WebSocket completo para el juego de Batalla Naval, construido con Python puro usando sockets.

## Características

- ✅ **Protocolo personalizado** - Sistema de códigos y mensajes estructurado
- ✅ **WebSocket nativo** - Implementación de WebSocket desde cero sin dependencias externas
- ✅ **Manejo de sesiones** - Gestión automática de partidas y jugadores
- ✅ **Reconexión automática** - Los jugadores pueden reconectarse a sus partidas
- ✅ **Logging detallado** - Sistema de logs para monitoreo y debugging
- ✅ **Validación robusta** - Validación completa de entrada de datos
- ✅ **Manejo de errores** - Sistema estructurado de errores con códigos específicos

## Estructura del Proyecto

```
server/
├── main.py                    # Punto de entrada principal
├── config.py                  # Configuración del servidor
├── network/
│   ├── protocol.py           # Protocolo personalizado
│   └── server.py             # Servidor WebSocket
├── game/                      # Lógica del juego (ya existente)
│   ├── game.py
│   ├── board.py
│   ├── player.py
│   ├── ship.py
│   ├── enums.py
│   ├── errors.py
│   ├── results.py
│   └── ...
├── state/
│   └── game_manager.py       # Gestor centralizado de partidas
└── utils/
    └── validators.py         # Validadores de entrada
```

## Instalación

### Requisitos
- Python 3.8+

### Dependencias
El servidor usa solo la librería estándar de Python. No requiere dependencias externas.

### Setup
```bash
# Clonar/navegar al proyecto
cd server/

# Ejecutar el servidor
python main.py
```

## Protocolo de Comunicación

### Estructura de Mensajes

#### Mensaje Genérico
```json
{
  "type": "string",           // Tipo de mensaje
  "code": 200,                // Código de estado
  "timestamp": 1707405600000, // Timestamp en millisegundos
  "gameId": "game_0",         // ID de la partida (opcional)
  "playerId": "player_123",   // ID del jugador (opcional)
  // ... campos adicionales según tipo
}
```

#### Mensaje de Error
```json
{
  "type": "error",
  "code": 420,
  "message": "Partida no encontrada",
  "timestamp": 1707405600000
}
```

### Flujo de Conexión

#### 1. Unirse a Partida
**Cliente → Servidor:**
```json
{
  "type": "join_game",
  "playerId": "player_123",
  "playerName": "Juan"
}
```

**Servidor → Cliente (primer jugador):**
```json
{
  "type": "game_state",
  "code": 210,
  "gameId": "game_0",
  "message": "Esperando oponente...",
  "gameState": "WAITING_FOR_OPPONENT"
}
```

**Servidor → Ambos Jugadores (cuando llega el segundo):**
```json
{
  "type": "game_state",
  "code": 211,
  "gameId": "game_0",
  "message": "¡Oponente encontrado! Coloca tus barcos.",
  "gameState": "PLACING_SHIPS"
}
```

#### 2. Colocar Barcos
**Cliente → Servidor:**
```json
{
  "type": "place_ships",
  "gameId": "game_0",
  "playerId": "player_123",
  "ships": [
    {
      "type": "AIRCRAFT_CARRIER",
      "start": {"x": 0, "y": 0},
      "orientation": "horizontal"
    },
    // ... más barcos
  ]
}
```

**Servidor → Cliente:**
```json
{
  "type": "game_state",
  "code": 200,
  "gameId": "game_0",
  "message": "Barcos colocados correctamente"
}
```

#### 3. Ataque
**Cliente → Servidor:**
```json
{
  "type": "attack",
  "gameId": "game_0",
  "playerId": "player_123",
  "coordinate": {"x": 5, "y": 7}
}
```

**Servidor → Atacante:**
```json
{
  "type": "attack_result",
  "code": 217,
  "coordinate": {"x": 5, "y": 7},
  "outcome": "hit",
  "shipType": "DESTROYER"
}
```

**Servidor → Defensor:**
```json
{
  "type": "opponent_move",
  "coordinate": {"x": 5, "y": 7},
  "outcome": "hit",
  "shipType": "DESTROYER"
}
```

### Códigos de Estado

| Código | Significado |
|--------|-------------|
| 200 | OK |
| 210 | Esperando oponente |
| 211 | Ambos listos |
| 212 | Juego iniciado |
| 217 | Ataque registrado |
| 220 | Fin de juego |
| 400 | Solicitud incorrecta |
| 410 | Jugador no encontrado |
| 420 | Partida no encontrada |
| 430 | Colocación de barcos inválida |
| 440 | Coordenada inválida |
| 442 | No es tu turno |
| 450 | Oponente desconectado |
| 500 | Error interno del servidor |

## Configuración

Editar `config.py` para personalizar:

```python
SERVER_HOST = '0.0.0.0'           # Host del servidor
SERVER_PORT = 8080                # Puerto WebSocket
BOARD_SIZE = 10                   # Tamaño del tablero
GAME_TIMEOUT_MINUTES = 30         # Timeout de partidas inactivas
```

## Uso desde el Cliente

### Conectar a Servidor
```javascript
const ws = new WebSocket('ws://localhost:8080');

ws.addEventListener('open', () => {
  // Unirse a partida
  ws.send(JSON.stringify({
    type: 'join_game',
    playerId: 'player_123',
    playerName: 'Juan'
  }));
});

ws.addEventListener('message', (event) => {
  const message = JSON.parse(event.data);
  console.log('Mensaje recibido:', message);
});
```

## Logging

Los logs se guardan en `logs/server.log` y también se imprimen en consola.

Niveles disponibles:
- DEBUG: Información detallada
- INFO: Información general
- WARNING: Advertencias
- ERROR: Errores

## Manejo de Errores

El servidor siempre responde con un código de estado y un mensaje descriptivo:

```json
{
  "type": "error",
  "code": 442,
  "message": "No es tu turno",
  "timestamp": 1707405600000
}
```

## Testing

Para probar el servidor manualmente:

```bash
# Terminal 1: Iniciar servidor
python main.py

# Terminal 2: Conectar cliente
python -c "
import socket, json, base64, hashlib

def handshake(sock, key):
    guid = '258EAFA5-E914-47DA-95CA-C5AB0DC85B11'
    accept = base64.b64encode(hashlib.sha1((key + guid).encode()).digest()).decode()
    response = f'HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Accept: {accept}\r\n\r\n'
    sock.send(response.encode())

# Conectar...
"
```

## Próximas Mejoras

- [ ] Base de datos para persistencia de partidas
- [ ] Sistema de ranking y estadísticas
- [ ] Soporte para múltiples tableros diferentes
- [ ] Chat entre jugadores
- [ ] Notificaciones por email de desconexión

## Licencia

MIT
