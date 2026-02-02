# Battleship - Local Console Mode

Sistema para jugar Batalla Naval en modo local usando 3 terminales separadas: 1 servidor y 2 clientes.

## Arquitectura

- **Servidor**: Maneja la lógica del juego, orquesta turnos, valida movimientos
- **Cliente 1 y 2**: Jugadores interactivos que se conectan vía sockets TCP/IP

La comunicación es **sincrónica** mediante protocolo de mensajes JSON sobre TCP en `localhost:5000`.

## Instalación

Asegúrate de que Python 3.10+ esté instalado.

```bash
# Navega a la carpeta del proyecto
cd BatallaNaval
```

## Uso

### Terminal 1: Iniciar el Servidor

```bash
python -m local_runner.run_console server
```

Deberías ver:
```
============================================================
BATTLESHIP SERVER
============================================================
[SERVER] Battleship Server started on localhost:5000
[SERVER] Waiting for players...
```

### Terminal 2: Iniciar Cliente 1 (Jugador 1)

```bash
python -m local_runner.run_console client --name Alice
```

### Terminal 3: Iniciar Cliente 2 (Jugador 2)

```bash
python -m local_runner.run_console client --name Bob
```

## Flujo de Juego

### 1. **Conexión**
Cuando ambos clientes se conectan, el servidor confirma y avanza a la fase de colocación de barcos.

### 2. **Colocación de Barcos**
Cada jugador coloca 4 barcos:
- Acorazado (4 casillas)
- Crucero (3 casillas)
- Destructor (2 casillas)
- Submarino (1 casilla)

El sistema pide las coordenadas `x y` para cada casilla del barco.

### 3. **Espera**
Una vez colocados todos los barcos, ambos jugadores deben confirmar "READY" para empezar.

### 4. **Batalla**
- Turno alterno de ataques
- El atacante ingresa coordenadas `x y`
- El servidor informa: HIT, MISS, SHIP_SUNK
- Continúa hasta que todos los barcos de un jugador se hundan

### 5. **Fin del Juego**
El ganador recibe notificación con estadísticas (movimientos totales, movimientos ganadores).

## Ejemplo de Interacción

```
BATTLESHIP CLIENT - Alice
============================================================
[Alice] Connected to server
[Alice] Registered as: Alice

✓ All players joined. Start placing ships.

🚢 SHIP PLACEMENT PHASE
Place your ships on a 10x10 board

     0 1 2 3 4 5 6 7 8 9
  0  . . . . . . . . . .
  1  . . . . . . . . . .
  2  . . . . . . . . . .
  ...

📍 Placing BATTLESHIP (size: 4)
Position 1/4 (x y): 2 0
Position 2/4 (x y): 2 1
Position 3/4 (x y): 2 2
Position 4/4 (x y): 2 3
✓ Ship placed: ship_1

[continúa para otros barcos...]

✓ All ships placed!
⏳ Waiting for opponent and game start...

🎮 GAME STARTED!

>>> YOUR TURN <<<

```

## Protocolo de Mensajes

### Cliente → Servidor

- `CONNECT`: Registrar jugador
- `PLACE_SHIP`: Colocar barco con coordenadas
- `READY`: Confirmar lista para jugar
- `ATTACK`: Atacar coordenada (x, y)
- `DISCONNECT`: Desconectar

### Servidor → Cliente

- `PLAYER_REGISTERED`: Confirmación de registro
- `START_PLACING_SHIPS`: Comenzar a colocar barcos
- `SHIP_PLACED`: Confirmación de barco colocado
- `GAME_STARTED`: El juego comienza
- `YOUR_TURN`: Es tu turno
- `OPPONENT_TURN`: Turno del oponente
- `ATTACK_RESULT`: Resultado del ataque (HIT/MISS/SHIP_SUNK)
- `GAME_OVER`: Fin del juego
- `ERROR`: Mensaje de error

## Estructura de Archivos

```
local_runner/
├── __init__.py
├── protocol.py        # Protocolo de comunicación
├── server.py          # Lógica del servidor
├── client.py          # Lógica del cliente
├── run_console.py     # Entrada principal
└── README.md          # Este archivo
```

## Características

✅ Comunicación bidireccional TCP/IP  
✅ Protocolo JSON para mensajes  
✅ Threading para manejo concurrente de clientes  
✅ Validación completa de movimientos  
✅ Estados de juego sincronizados  
✅ Manejo robusto de errores  

## Troubleshooting

### "Address already in use"
El puerto 5000 ya está ocupado. Espera 30 segundos o:
```bash
# En Windows PowerShell
netstat -ano | findstr :5000
taskkill /PID <PID> /F
```

### "Connection refused"
Asegúrate de que el servidor está corriendo antes de iniciar los clientes.

### "Ship placement error"
Verifica que las coordenadas sean válidas (0-9) y no sobrepasen el tablero.

## Desarrollo Futuro

- [ ] Modo GUI con tkinter o PyQt
- [ ] Persistencia de partidas
- [ ] Estadísticas y ranking
- [ ] AI para jugar solo
- [ ] Soporte para más de 2 jugadores
- [ ] WebSocket para juego en red real

## Licencia

MIT
