# Batalla Naval - Juego Multijugador en Tiempo Real

Un juego de estrategia clásico **Batalla Naval** implementado con arquitectura cliente-servidor en tiempo real. Los jugadores se enfrentan en partidas uno contra uno, colocando sus flotas en tableros secretos y atacándose mutuamente hasta hundir todos los barcos del oponente.

![Pantalla Principal](assets/capturas%20de%20pantalla/main.png)

## Características del Juego

- **Juego Multijugador en Tiempo Real**: Comunicación bidireccional instantánea mediante WebSockets
- **Interfaz Moderna y Reactiva**: Diseño temático "sonar radar" con animaciones y efectos visuales
- **Reconexión Automática**: Restauración de sesiones interrumpidas sin perder la partida
- **Colocación Flexible de Barcos**: 
  - Interfaz drag-and-drop/click para posicionar la flota
  - Generación aleatoria automática de disposiciones válidas
  - Validación en tiempo real de colocaciones
- **Sistema de Turnos Justo**: Control de turnos centralizado en el servidor
- **Persistencia de Sesión**: Guardado de datos del jugador en `localStorage`
- **Flota Estándar**: Portaaviones (5), Acorazado (4), Crucero (3), Destructor (3), Submarino (2)

## Arquitectura Técnica

### Diagrama de Capas

```
┌─────────────────────────────────────────┐
│     CLIENTE (JavaScript Vanilla)        │
│  - HTML5/CSS3 Responsivo                │
│  - State Management + Reactivity        │
│  - WebSocket + Fetch API                │
└──────────────┬──────────────────────────┘
               │ WebSocket (8080)
               │ HTTP (8000)
               ▼
┌─────────────────────────────────────────┐
│      SERVIDOR (Python FastAPI)          │
│  - WebSocket Server                     │
│  - Game Logic & State Machine           │
│  - Validación de Reglas                 │
│  - Session Management                   │
└─────────────────────────────────────────┘
```

### Stack Tecnológico

#### Backend
- **FastAPI 0.104.1** - Framework web moderno con CORS y servicio de archivos estáticos
- **Uvicorn 0.24.0** - ASGI server con hot-reload en desarrollo
- **Python-dotenv 1.0.0** - Gestión de variables de entorno
- **Python 3.8+** - Runtime

#### Frontend
- **Vanilla JavaScript** - Sin dependencias externas (máxima compatibilidad)
- **HTML5** - Estructura semántica
- **CSS3** - Diseño responsivo, animaciones, variables CSS
- **WebSocket API** - Comunicación real-time
- **Fetch API** - Llamadas HTTP
- **LocalStorage** - Persistencia de sesión

### Protocolo de Comunicación

Todos los mensajes JSON siguen esta estructura:

```json
{
    "type": "join_game|place_ships|attack|game_state|error|...",
    "code": 200,
    "timestamp": 1234567890000,
    "gameId": "session-uuid",
    "playerId": "player-uuid",
    "...": "datos específicos del mensaje"
}
```

**Códigos de Estado Principales:**
- `200` - Operación exitosa
- `210` - Esperando oponente
- `211` - Ambos jugadores conectados, fase de colocación
- `212` - Juego iniciado, fase de combate
- `213` - Barcos colocados, esperando oponente
- `215` - Es tu turno
- `216` - Esperando turno del oponente
- `217` - Ataque registrado
- `220` - Juego finalizado
- `230-231` - Reconexión / Reconexión exitosa
- `400-450` - Errores de validación

### Máquina de Estados del Juego

```
WAITING_FOR_PLAYERS
    ↓ (Se une jugador 1)
    → Esperando oponente
    ↓ (Se une jugador 2)
PLACING_SHIPS
    ↓ (Ambos jugadores colocan barcos)
    → Validación de colocaciones
    ↓ (Ambos listos)
IN_PROGRESS
    ↓ (Comienzan ataques en turnos)
    → Turnos alternados
    → Verificación de hundimientos
    ↓ (Un jugador hunde todos los barcos)
FINISHED
    → Determinar ganador
    → Enviar estadísticas
```

### Flota de Barcos

| Barco | Tipo | Tamaño | Cantidad |
|-------|------|--------|----------|
| Portaaviones | AIRCRAFT_CARRIER | 5 casillas | 1 |
| Acorazado | BATTLESHIP | 4 casillas | 1 |
| Crucero | CRUISER | 3 casillas | 1 |
| Destructor | DESTROYER | 3 casillas | 1 |
| Submarino | SUBMARINE | 2 casillas | 1 |

**Total: 5 barcos, 17 casillas en tablero 10x10**

### Sistema de Validaciones

El servidor implementa validaciones robustas:

**Colocación de Barcos:**
- Coordenadas dentro del tablero (0-9, 0-9)
- Sin solapamiento con otros barcos
- Alineación correcta (horizontal o vertical)
- Un barco de cada tipo por jugador
- Longitud correcta según tipo

**Ataques:**
- Coordenada válida dentro del tablero
- No atacar la misma coordenada dos veces
- Validar turnos correctos
- Detección automática de barcos hundidos

**Sesiones:**
- Timeout de espera de oponente: 120s
- Timeout de colocación de barcos: 180s
- Timeout de turno: 300s
- Timeout de reconexión: 60s
- Timeout de inactividad: 3600s

## Instalación

### Requisitos Previos

- **Python 3.8 o superior**
- **pip** (gestor de paquetes de Python)
- **Navegador web moderno** (Chrome, Firefox, Edge, Safari)

### Pasos de Instalación

#### 1. Clonar o Descargar el Repositorio

```bash
git clone https://github.com/usuario/BatallaNaval.git
cd BatallaNaval
```

#### 2. Crear Entorno Virtual (Recomendado)

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

#### 3. Instalar Dependencias

```bash
cd server
pip install -r requirements.txt
```

**Contenido de requirements.txt:**
```
fastapi==0.104.1
uvicorn[standard]==0.24.0
python-dotenv==1.0.0
```

#### 4. Configuración (Opcional)

Crear archivo `.env` en la carpeta `server/` si necesitas cambiar puertos:

```bash
# server/.env
WEBSOCKET_HOST=127.0.0.1
WEBSOCKET_PORT=8080
HTTP_HOST=127.0.0.1
HTTP_PORT=8000
CORS_ORIGINS=*
```

## Uso

### Iniciar el Servidor

```bash
cd server
python main.py
```

**Salida esperada:**
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     WebSocket server running on ws://127.0.0.1:8080
```

### Acceder al Juego

1. Abre tu navegador web
2. Navega a: **http://localhost:8000**
3. Ingresa tu nombre de jugador (2-30 caracteres)
4. Haz clic en **INICIAR BÚSQUEDA**
5. Espera a que se conecte otro jugador

### Flujo de Juego

#### Fase 1: Búsqueda de Oponente
- Ingresa tu nombre de jugador
- El sistema buscará otro jugador disponible
- Cuando se conecte, avanzarás a la fase de colocación

#### Fase 2: Colocación de Barcos
- Selecciona cada barco de la lista
- Haz clic en el tablero para colocar el barco
- Puedes usar **COLOCACIÓN ALEATORIA** para generar una disposición válida automática
- Haz clic en **CONFIRMAR DISPOSICIÓN** cuando esté listo
- Espera a que el oponente termine de colocar sus barcos

![Colocación de Barcos](assets/capturas%20de%20pantalla/placing%20ships.png)

#### Fase 3: Combate
- Tu tablero (izquierda): Muestra tus barcos y ataques recibidos
- Tablero del oponente (derecha): Tablero de ataque donde registras tus ataques
- Los ataques que aciertan (HIT) o hunden barcos (SUNK) te dan otro turno
- Los ataques que fallan (MISS) cambian al turno del oponente

![Combate - En Progreso 1](assets/capturas%20de%20pantalla/in%20progress%201.png)

![Combate - En Progreso 2](assets/capturas%20de%20pantalla/in%20progress%202.png)

![Combate - En Progreso 3](assets/capturas%20de%20pantalla/in%20progress%203.png)

#### Fase 4: Resultado Final
- El juego termina cuando todos los barcos de un jugador están hundidos
- Se muestra el ganador y estadísticas de la partida

![Victoria](assets/capturas%20de%20pantalla/win.png)

![Derrota](assets/capturas%20de%20pantalla/lose.png)

### Controles

- **Interfaz de Colocación:**
  - Click en barco: Seleccionar barco
  - Click en tablero: Colocar barco seleccionado
  - Botón "COLOCACIÓN ALEATORIA": Generar disposición válida aleatoria
  - Botón "CONFIRMAR DISPOSICIÓN": Finalizar colocación

- **Interfaz de Combate:**
  - Click en tablero de ataque: Realizar ataque en esa coordenada
  - El indicador de turno muestra el estado actual
  - Los impactos (HIT), hundimientos (SUNK) y fallos (MISS) se visualizan

## Estructura del Proyecto

```
BatallaNaval/
├── client/                          # Frontend - Cliente web
│   ├── index.html                   # HTML principal con todas las pantallas
│   ├── css/
│   │   └── styles.css               # Estilos temáticos y animaciones
│   └── js/
│       ├── main.js                  # Punto de entrada y orquestación
│       ├── api.js                   # Gestión WebSocket y comunicación
│       ├── state.js                 # State management con localStorage
│       └── render.js                # Renderización de tableros y UI
│
├── server/                          # Backend - Servidor Python
│   ├── main.py                      # Punto de entrada, inicia servicios
│   ├── config.py                    # Configuración centralizada
│   ├── requirements.txt             # Dependencias de Python
│   │
│   ├── game/                        # Lógica del juego
│   │   ├── __init__.py
│   │   ├── game.py                  # Máquina de estados principal del juego
│   │   ├── player.py                # Clase Player con tableros y métodos
│   │   ├── board.py                 # Tablero 10x10 con gestión de celdas
│   │   ├── ship.py                  # Definición de barcos y coordenadas
│   │   ├── enums.py                 # Enumeraciones: CellState, GameState, ShipType
│   │   ├── errors.py                # Excepciones personalizadas
│   │   └── results.py               # Clases para resultados de ataques
│   │
│   └── network/                     # Red y comunicación
│       ├── __init__.py
│       ├── server.py                # WebSocket server y gestión de sesiones
│       └── protocol.py              # Definición del protocolo de mensajes
│
└── README.md                        # Este archivo
```

### Detalles de Componentes Clave

#### Backend - Lógica del Juego

**game/game.py** - Máquina de estados central
- Gestiona el estado global de la partida
- Coordina turnos entre jugadores
- Valida ataques y detecta barcos hundidos
- Determina ganador cuando todos los barcos están hundidos

**game/player.py** - Representación del jugador
- Mantiene dos tableros:
  - `board`: Tu tablero (defensa) - oculto al oponente
  - `tracking_board`: Tablero del oponente (ataque)
- Procesa ataques entrantes
- Registra tus ataques

**game/board.py** - Tablero 10x10
- Almacena estado de cada celda (vacía, barco, golpeada, fallida)
- Valida colocación de barcos (sin solapamiento, alineación correcta)
- Registra ataques y detecta hundimientos

**game/ship.py** - Representación de barcos
- Mantiene posiciones e impactos del barco
- Determina si está hundido (todos los puntos golpeados)
- Almacena orientación (horizontal/vertical)

#### Backend - Red

**network/server.py** - WebSocket Server
- Acepta conexiones de clientes
- Crea y gestiona sesiones de juego
- Enruta mensajes a handlers apropiados
- Maneja desconexiones y timeouts
- Genera colocaciones aleatorias válidas

**network/protocol.py** - Protocolo de comunicación
- Define estructura de mensajes JSON
- Valida mensajes entrantes
- Genera mensajes de respuesta

#### Frontend - Cliente

**js/main.js** - Orquestación
- Inicializa el cliente al cargar la página
- Configura la arquitectura reactiva
- Los cambios de estado disparan renderizado
- Estructura: GameState → API → Renderer

**js/api.js** - Comunicación WebSocket
- Gestiona conexión WebSocket con reconexión automática
- Health check HTTP antes de WebSocket
- Handlers de mensajes para cada tipo
- Sistema de ping/pong para mantener conexión
- Gestión de sesión en localStorage

**js/state.js** - Administración de Estado
- Estado persistente en localStorage (`playerId`, `sessionId`)
- Estado de sesión en sessionStorage (pantalla actual, nombres)
- Información de tableros y colocación de barcos
- Configuración del juego (tablero 10x10)

**js/render.js** - Renderización
- Renderizar tablero 10x10 con coordenadas (A-J, 1-10)
- Actualizar celdas según estado (vacía, barco, impacto, fallo, hundido)
- Cambiar pantallas según estado del juego
- Efectos visuales y animaciones

## Diseño Visual

- **Paleta de Colores**: Tema oceánico azul profundo con acentos aqua y rojo
- **Tipografía**: "Orbitron" para títulos (efecto militar), "Rajdhani" para cuerpo
- **Efectos**: Glow neon, animaciones suaves, tema "radar sonar"
- **Responsividad**: Diseño adaptable a diferentes tamaños de pantalla

## Flujo de Comunicación

### Inicialización
```
1. Cliente carga HTML
2. Verifica health check (GET /api/health)
3. Conecta WebSocket a ws://host:8080
4. Envía ping
5. Servidor responde pong
6. Muestra pantalla de inicio
```

### Unirse a Partida
```
1. Usuario ingresa nombre y haz clic en INICIAR BÚSQUEDA
2. Cliente envía: {type: 'join_game', playerName: 'Nombre'}
3. Servidor valida nombre y crea/recupera sesión
4. Si 1 jugador: Esperar oponente (código 210)
5. Si 2 jugadores: Iniciar colocación de barcos (código 211)
6. Cliente renderiza pantalla correspondiente
```

### Colocación de Barcos
```
1. Usuario coloca barcos en el tablero
2. Cliente envía: {type: 'place_ships', ships: [...]}
3. Servidor valida cada barco (sin solapamientos, alineación)
4. Si válido: Guardar y esperar oponente (código 213)
5. Cuando ambos listos: Iniciar combate (código 212)
```

### Combate
```
1. Servidor envía: {code: 215} - Es tu turno
2. Usuario haz clic en tablero de ataque
3. Cliente envía: {type: 'attack', coord: {x, y}}
4. Servidor procesa: Validar turno, registrar ataque
5. Servidor responde: {code: 217, outcome: 'HIT|MISS|SUNK'}
6. Si HIT/SUNK: Mismo jugador ataca de nuevo
7. Si MISS: Cambiar turno al oponente
8. Si todos los barcos hundidos: Juego termina (código 220)
```

### Reconexión
```
1. Cliente se desconecta inesperadamente
2. Cliente intenta reconectar automáticamente (5 intentos, delay 3s)
3. Cliente envía: {type: 'reconnect', gameId, playerId}
4. Servidor restaura sesión si existe y está dentro del timeout (60s)
5. Servidor responde con estado actual del juego
6. Juego continúa desde donde se interrumpió
```

## Configuración Avanzada

### Timeouts (en config.py)

Modifica estos valores según necesites:

```python
WAIT_FOR_OPPONENT_TIMEOUT = 120      # segundos esperando oponente
WAIT_FOR_SHIP_PLACEMENT_TIMEOUT = 180  # segundos para colocar barcos
PLAYER_TURN_TIMEOUT = 300            # segundos para hacer ataque
RECONNECT_TIMEOUT = 60               # segundos para reconectar
INACTIVITY_TIMEOUT = 3600            # segundos antes de limpiar sesión
```

### Límites de Jugador

```python
MIN_PLAYER_NAME_LENGTH = 2
MAX_PLAYER_NAME_LENGTH = 30
```

### Tamaño del Tablero

```python
BOARD_SIZE = 10  # Tablero 10x10 (coordenadas 0-9)
```

## Solución de Problemas

### "No se puede conectar al servidor"
- Verifica que el servidor esté ejecutándose: `python main.py`
- Confirma los puertos: WebSocket (8080), HTTP (8000)
- Verifica firewall o bloqueos de puertos

### "Servidor HTTP respondió pero WebSocket no conecta"
- El servidor HTTP está ejecutándose pero WebSocket puede estar bloqueado
- Intenta desde `localhost` en lugar de una IP externa
- Verifica CORS en configuración

### "Mi conexión se cortó durante el juego"
- El cliente intenta reconectar automáticamente (5 intentos)
- Si fue reciente (menos de 60 segundos), la sesión se recuperará
- Recarga la página si la reconexión automática falla

### "No se puede validar mi colocación de barcos"
- Verifica que no haya solapamientos entre barcos
- Asegúrate de que los barcos están alineados (horizontal o vertical)
- Verifica que tengas exactamente 5 barcos de los tipos requeridos

## Desarrollo

### Modo Debug

Para ver logs detallados, modifica el nivel de logging en `main.py`:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Testing Local

Abre dos ventanas del navegador:
1. `http://localhost:8000` - Jugador 1
2. `http://localhost:8000` - Jugador 2

Ingresa diferentes nombres para jugar contra ti mismo.

### Estructura de Datos del Protocolo

**Mensaje de Ataque:**
```json
{
    "type": "attack",
    "playerId": "uuid-xxx",
    "gameId": "uuid-yyy",
    "coord": {"x": 3, "y": 5}
}
```

**Resultado de Ataque:**
```json
{
    "type": "game_state",
    "code": 217,
    "outcome": "HIT|MISS|SUNK",
    "ship_sunk": true,
    "game_finished": false,
    "attacker_id": "uuid-xxx",
    "defender_id": "uuid-yyy",
    "attacked_coordinate": "D6"
}
```

## Licencia

Este proyecto es de código abierto. Siéntete libre de usar, modificar y distribuir.

## Autor

Proyecto de Batalla Naval - Implementación educativa de arquitectura cliente-servidor con WebSockets.

---

**¿Problemas o sugerencias?** Abre un issue en el repositorio o contacta al autor.

**Versión:** 1.0  
**Última actualización:** Mayo 2026
