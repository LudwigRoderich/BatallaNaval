# Arquitectura del Servidor de Batalla Naval

## Descripción General

El servidor de Batalla Naval es una aplicación basada en WebSockets que gestiona múltiples partidas simultáneas entre jugadores. Está construido con Python puro, utilizando solo la librería estándar sin dependencias externas.

## Componentes Principales

### 1. **network/server.py** - Servidor WebSocket
- **BatallaNavalServer**: Clase principal que gestiona:
  - Aceptación de conexiones WebSocket
  - Handshake WebSocket HTTP
  - Envío/recepción de frames WebSocket
  - Manejo de clientes en threads separados
  - Enrutamiento de mensajes según tipo

- **GameSession**: Representa una partida activa:
  - Información de jugadores conectados
  - Socket de conexión de cada jugador
  - Estado de preparación
  - Timeout automático

### 2. **network/protocol.py** - Protocolo Personalizado
- **Protocol**: Define:
  - Códigos de estado (200, 210, 220, 400, 420, etc.)
  - Tipos de mensajes válidos
  - Creación de mensajes estructurados
  - Validación de mensajes entrantes

### 3. **game/** - Lógica del Juego (Existente)
- **Game**: Gestiona el flujo y estado de una partida
- **Board**: Representa el tablero de juego
- **Player**: Datos y métodos del jugador
- **Ship**: Información de barcos
- **Enums**: Estados y resultados

### 4. **state/game_manager.py** - Gestión Centralizada
- **GameManager**: Proporciona:
  - Creación de partidas
  - Registro de jugadores
  - Búsqueda de partidas activas
  - Estadísticas de sesiones
  - Limpieza de partidas inactivas

### 5. **utils/validators.py** - Validación de Entrada
- **Validators**: Valida:
  - Nombres de jugadores
  - Coordenadas
  - Colocación de barcos
  - Listas de barcos

## Flujo de Comunicación

```
CLIENTE                          SERVIDOR
   |                                |
   |------ WebSocket Connect ------>|
   |                                |
   |      (HTTP Upgrade)            |
   |                                |
   |<----- Conexión Aceptada -------|
   |                                |
   |------ join_game ------->|      |
   |                         |      |
   |                    Crear GameSession
   |                    Buscar oponente
   |                         |      |
   |<----- game_state -------|      |
   |   (WAITING_FOR_OPPONENT)|      |
   |                                |
   |     (Otro cliente se une)      |
   |<----- game_state -------|      |
   |   (PLACING_SHIPS)              |
   |                                |
   |------ place_ships ----->|      |
   |                    Validar pos. |
   |                    Marcar listo|
   |<----- game_state -------|      |
   |                                |
   |<----- game_state -------|      |
   |   (GAME_STARTED)               |
   |                                |
   |------ attack -------->|        |
   |                    Validar mov.|
   |                    Comprobar hit
   |<----- attack_result---|        |
   |                                |
   |<----- opponent_move---|        |
   |     (Al oponente)              |
   |                                |
```

## Manejo de Estados

### Estados del Juego
- **WAITING_FOR_PLAYERS**: Esperando que se unan los jugadores
- **PLACING_SHIPS**: Los jugadores colocan sus barcos
- **IN_PROGRESS**: Juego activo, alternancia de turnos
- **FINISHED**: Juego terminado

### Estados de Conexión
- **CONNECTED**: Cliente conectado vía WebSocket
- **RECONNECTING**: Cliente intentando reconectar
- **DISCONNECTED**: Cliente desconectado

## Estructura de Datos

### GameSession
```python
{
    'game_id': 'game_0',
    'game': Game(),
    'players': {
        'player_001': {
            'name': 'Juan',
            'socket': <socket>,
            'ready': False
        },
        'player_002': {
            'name': 'María',
            'socket': <socket>,
            'ready': False
        }
    },
    'created_at': datetime,
    'last_activity': datetime
}
```

## Manejo de Errores

Todos los errores se envían con código de estado específico:

```json
{
  "type": "error",
  "code": 420,
  "message": "Partida no encontrada",
  "timestamp": 1707405600000
}
```

## Threading y Concurrencia

- **Main Thread**: Acepta conexiones y inicia threads de cliente
- **Client Threads**: Cada cliente tiene su propio thread que:
  - Lee frames WebSocket
  - Procesa mensajes
  - Envía respuestas
  - Maneja desconexiones

## Reconexión

Si un jugador se desconecta:
1. El servidor marca al jugador como desconectado
2. Mantiene la sesión activa por 5 minutos (configurable)
3. El jugador puede reconectar con su ID de jugador y partida
4. Si la sesión expira, se limpia automáticamente

## Logging

Todos los eventos importantes se registran:
- Conexiones/desconexiones
- Creación de partidas
- Cambios de estado
- Errores
- Intentos de reconexión

Logs guardados en `logs/server.log` y salida a consola.

## Escalabilidad

### Limitaciones Actuales
- Basado en threads (eficiente para ~100 conexiones simultáneas)
- En memoria (se pierden datos al reiniciar)
- Un solo servidor (sin cluster)

### Mejoras Futuras
- Migrar a async/await con asyncio
- Persistencia en base de datos
- Balanceo de carga
- Sistema de caché (Redis)

## Seguridad

- Validación completa de entrada
- Verificación de turnos y estados
- IDs únicos de sesión
- Timeout de inactividad
- Manejo robusto de excepciones

## Performance

- WebSocket nativo (sin overhead de librerías)
- Procesamiento asíncrono de mensajes
- Limpieza automática de sesiones inactivas
- Garbage collection integrado de Python
