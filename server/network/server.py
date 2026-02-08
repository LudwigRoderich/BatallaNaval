"""
Servidor de Batalla Naval usando WebSockets.
Maneja la lógica del juego y las conexiones de clientes.
"""

import socket
import threading
import json
import base64
import hashlib
import logging
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta

from game.game import Game
from game.ship import Ship, ShipOrientation, Coordinate
from game.enums import GameState, AttackOutcome
from network.protocol import Protocol

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class GameSession:
    """Representa una sesión de juego activa."""

    def __init__(self, game_id: str, game: Game):
        self.game_id = game_id
        self.game = game
        self.players = {}  # {player_id: {'name': str, 'socket': socket, 'ready': bool}}
        self.created_at = datetime.now()
        self.last_activity = datetime.now()
        self.timeout = timedelta(minutes=30)

    def add_player(self, player_id: str, player_name: str, client_socket: socket.socket) -> bool:
        """Añade un jugador a la sesión."""
        if len(self.players) >= 2:
            return False

        self.players[player_id] = {
            'name': player_name,
            'socket': client_socket,
            'ready': False,
        }
        return True

    def get_opponent_id(self, player_id: str) -> Optional[str]:
        """Obtiene el ID del oponente."""
        for pid in self.players:
            if pid != player_id:
                return pid
        return None

    def is_active(self) -> bool:
        """Verifica si la sesión sigue activa."""
        return datetime.now() - self.last_activity < self.timeout


class BatallaNavalServer:
    """Servidor principal de Batalla Naval."""

    def __init__(self, host: str = '0.0.0.0', port: int = 8080):
        self.host = host
        self.port = port
        self.protocol = Protocol()
        
        # Diccionarios de estado
        self.sessions: Dict[str, GameSession] = {}  # {game_id: GameSession}
        self.player_sessions: Dict[str, str] = {}   # {player_id: game_id}
        self.player_sockets: Dict[socket.socket, str] = {}  # {socket: player_id}
        
        # Contador para IDs
        self.next_game_id = 0
        self.next_player_id = 0
        
        # Socket del servidor
        self.server_socket = None
        self.running = False
        self.client_threads = {}

    def start(self):
        """Inicia el servidor."""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            self.running = True
            
            logger.info(f"Servidor iniciado en {self.host}:{self.port}")
            
            while self.running:
                try:
                    client_socket, client_address = self.server_socket.accept()
                    logger.info(f"Conexión aceptada desde {client_address}")
                    
                    # Manejar conexión en un hilo separado
                    thread = threading.Thread(
                        target=self._handle_client,
                        args=(client_socket, client_address),
                        daemon=True
                    )
                    thread.start()
                    
                except Exception as e:
                    if self.running:
                        logger.error(f"Error aceptando conexión: {e}")
                        
        except Exception as e:
            logger.error(f"Error iniciando servidor: {e}")
        finally:
            self.stop()

    def stop(self):
        """Detiene el servidor."""
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        logger.info("Servidor detenido")

    def _handle_client(self, client_socket: socket.socket, client_address: Tuple):
        """Maneja a un cliente conectado."""
        player_id = None
        
        try:
            # WebSocket handshake
            request = client_socket.recv(4096).decode('utf-8')
            if not self._websocket_handshake(client_socket, request):
                logger.warning(f"Handshake fallido desde {client_address}")
                client_socket.close()
                return

            logger.info(f"WebSocket establecido con {client_address}")
            
            # Loop principal de recepción de mensajes
            while self.running:
                frame = self._receive_websocket_frame(client_socket)
                if not frame:
                    break

                try:
                    data = json.loads(frame)
                    is_valid, error_msg = self.protocol.validate_message(data)
                    
                    if not is_valid:
                        self._send_error(client_socket, 401, error_msg)
                        continue

                    msg_type = data.get('type')
                    
                    if msg_type == 'join_game':
                        player_id = self._handle_join_game(client_socket, data)
                    elif msg_type == 'reconnect':
                        player_id = self._handle_reconnect(client_socket, data)
                    elif msg_type == 'place_ships':
                        self._handle_place_ships(client_socket, player_id, data)
                    elif msg_type == 'attack':
                        self._handle_attack(client_socket, player_id, data)
                    elif msg_type == 'surrender':
                        self._handle_surrender(client_socket, player_id, data)
                    elif msg_type == 'ping':
                        self._send_message(client_socket, 'pong', code=200)
                    else:
                        self._send_error(client_socket, 400, f"Tipo de mensaje desconocido: {msg_type}")
                        
                except json.JSONDecodeError:
                    self._send_error(client_socket, 401, "Mensaje JSON inválido")
                except Exception as e:
                    logger.error(f"Error procesando mensaje: {e}")
                    self._send_error(client_socket, 500, "Error interno del servidor")
                    
        except Exception as e:
            logger.error(f"Error en cliente {client_address}: {e}")
        finally:
            self._cleanup_client(client_socket, player_id)

    def _websocket_handshake(self, client_socket: socket.socket, request: str) -> bool:
        """Realiza el handshake WebSocket."""
        try:
            lines = request.split('\r\n')
            headers = {}
            for line in lines[1:]:
                if ':' in line:
                    key, value = line.split(':', 1)
                    headers[key.strip()] = value.strip()

            key = headers.get('Sec-WebSocket-Key')
            if not key:
                return False

            guid = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
            accept_key = base64.b64encode(
                hashlib.sha1((key + guid).encode()).digest()
            ).decode()

            response = (
                "HTTP/1.1 101 Switching Protocols\r\n"
                "Upgrade: websocket\r\n"
                "Connection: Upgrade\r\n"
                f"Sec-WebSocket-Accept: {accept_key}\r\n"
                "\r\n"
            )
            client_socket.send(response.encode())
            return True
        except Exception as e:
            logger.error(f"Error en handshake: {e}")
            return False

    def _receive_websocket_frame(self, client_socket: socket.socket) -> Optional[str]:
        """Recibe y decodifica un frame WebSocket."""
        try:
            data = client_socket.recv(4096)
            if not data:
                return None

            # Parsear frame WebSocket
            if len(data) < 2:
                return None

            fin = (data[0] & 0x80) != 0
            opcode = data[0] & 0x0F
            masked = (data[1] & 0x80) != 0
            payload_length = data[1] & 0x7F
            
            idx = 2
            
            if payload_length == 126:
                payload_length = int.from_bytes(data[2:4], 'big')
                idx = 4
            elif payload_length == 127:
                payload_length = int.from_bytes(data[2:10], 'big')
                idx = 10

            masking_key = None
            if masked:
                masking_key = data[idx:idx+4]
                idx += 4

            payload = data[idx:idx+payload_length]
            
            if masked and masking_key:
                payload = bytes([payload[i] ^ masking_key[i % 4] for i in range(len(payload))])

            if opcode == 0x1:  # Text frame
                return payload.decode('utf-8')
            elif opcode == 0x8:  # Close frame
                return None
            
            return None
        except Exception as e:
            logger.error(f"Error recibiendo frame: {e}")
            return None

    def _send_websocket_frame(self, client_socket: socket.socket, data: str) -> bool:
        """Envía un frame WebSocket."""
        try:
            payload = data.encode('utf-8')
            frame = bytearray()
            frame.append(0x81)  # FIN + text frame
            
            if len(payload) <= 125:
                frame.append(len(payload))
            elif len(payload) <= 65535:
                frame.append(126)
                frame.extend(len(payload).to_bytes(2, 'big'))
            else:
                frame.append(127)
                frame.extend(len(payload).to_bytes(8, 'big'))
            
            frame.extend(payload)
            client_socket.send(bytes(frame))
            return True
        except Exception as e:
            logger.error(f"Error enviando frame: {e}")
            return False

    def _send_message(self, client_socket: socket.socket, msg_type: str, code: int = 200, **kwargs):
        """Envía un mensaje al cliente."""
        message = self.protocol.create_message(msg_type, code, **kwargs)
        self._send_websocket_frame(client_socket, json.dumps(message))

    def _send_error(self, client_socket: socket.socket, code: int, message: str):
        """Envía un mensaje de error."""
        error = self.protocol.create_error(code, message)
        self._send_websocket_frame(client_socket, json.dumps(error))

    def _handle_join_game(self, client_socket: socket.socket, data: Dict) -> Optional[str]:
        """Maneja solicitud de unirse a una partida."""
        is_valid, error_msg = self.protocol.validate_join_message(data)
        if not is_valid:
            self._send_error(client_socket, 402, error_msg)
            return None

        player_id = data.get('playerId')
        player_name = data.get('playerName')

        # Verificar si el jugador ya está en una partida
        if player_id in self.player_sessions:
            self._send_error(client_socket, 411, "Jugador ya está en una partida")
            return None

        # Buscar una partida esperando oponente
        available_session = None
        for session in self.sessions.values():
            if session.game.state == GameState.WAITING_FOR_PLAYERS and len(session.players) == 1:
                available_session = session
                break

        # Crear nueva partida o unirse a una existente
        if available_session is None:
            game_id = f"game_{self.next_game_id}"
            self.next_game_id += 1
            
            game = Game(board_size=10)
            session = GameSession(game_id, game)
            session.add_player(player_id, player_name, client_socket)
            
            self.sessions[game_id] = session
            self.player_sessions[player_id] = game_id
            self.player_sockets[client_socket] = player_id
            
            logger.info(f"Jugador {player_id} creó partida {game_id}")
            
            # Enviar confirmación
            self._send_message(
                client_socket,
                'game_state',
                code=210,
                gameId=game_id,
                playerId=player_id,
                message="Esperando oponente...",
                gameState="WAITING_FOR_OPPONENT"
            )
        else:
            game_id = available_session.game_id
            available_session.add_player(player_id, player_name, client_socket)
            
            self.player_sessions[player_id] = game_id
            self.player_sockets[client_socket] = player_id
            
            logger.info(f"Jugador {player_id} se unió a partida {game_id}")
            
            # Enviar confirmación a ambos jugadores
            for pid, player_info in available_session.players.items():
                self._send_message(
                    player_info['socket'],
                    'game_state',
                    code=211,
                    gameId=game_id,
                    playerId=pid,
                    message="¡Oponente encontrado! Coloca tus barcos.",
                    gameState="PLACING_SHIPS"
                )

        return player_id

    def _handle_reconnect(self, client_socket: socket.socket, data: Dict) -> Optional[str]:
        """Maneja reconexión de un jugador."""
        is_valid, error_msg = self.protocol.validate_reconnect_message(data)
        if not is_valid:
            self._send_error(client_socket, 402, error_msg)
            return None

        game_id = data.get('gameId')
        player_id = data.get('playerId')

        if game_id not in self.sessions:
            self._send_error(client_socket, 420, "Partida no encontrada")
            return None

        session = self.sessions[game_id]
        if player_id not in session.players:
            self._send_error(client_socket, 410, "Jugador no encontrado en esa partida")
            return None

        # Actualizar socket del jugador
        session.players[player_id]['socket'] = client_socket
        self.player_sockets[client_socket] = player_id
        self.player_sessions[player_id] = game_id
        
        logger.info(f"Jugador {player_id} reconectado a partida {game_id}")
        
        # Enviar estado del juego
        self._send_game_state(client_socket, game_id, player_id)
        
        # Notificar al oponente
        opponent_id = session.get_opponent_id(player_id)
        if opponent_id:
            opponent_socket = session.players[opponent_id]['socket']
            self._send_message(
                opponent_socket,
                'notification',
                code=231,
                message=f"{session.players[player_id]['name']} se ha reconectado"
            )

        return player_id

    def _handle_place_ships(self, client_socket: socket.socket, player_id: Optional[str], data: Dict):
        """Maneja colocación de barcos."""
        if not player_id:
            self._send_error(client_socket, 410, "Jugador no encontrado")
            return

        is_valid, error_msg = self.protocol.validate_place_ships_message(data)
        if not is_valid:
            self._send_error(client_socket, 402, error_msg)
            return

        game_id = data.get('gameId')
        ships_data = data.get('ships')

        if game_id not in self.sessions:
            self._send_error(client_socket, 420, "Partida no encontrada")
            return

        session = self.sessions[game_id]
        game = session.game

        try:
            # Convertir datos de barcos y colocarlos
            for ship_data in ships_data:
                start = ship_data['start']
                orientation = ShipOrientation.HORIZONTAL if ship_data['orientation'] == 'horizontal' else ShipOrientation.VERTICAL
                ship_type = ship_data['type']
                
                ship = Ship(ship_type, orientation)
                ship.start_coordinate = Coordinate(start['x'], start['y'])
                
                game.place_ship(player_id, ship)

            # Marcar al jugador como listo
            session.players[player_id]['ready'] = True
            
            # Enviar confirmación
            self._send_message(
                client_socket,
                'game_state',
                code=200,
                gameId=game_id,
                message="Barcos colocados correctamente"
            )
            
            # Verificar si ambos jugadores están listos
            all_ready = all(p['ready'] for p in session.players.values())
            if all_ready:
                # Actualizar estado del juego
                game._state = GameState.IN_PROGRESS
                player_ids = list(session.players.keys())
                game._current_turn = player_ids[0]
                
                logger.info(f"Partida {game_id} iniciada")
                
                # Notificar a ambos jugadores
                for pid, player_info in session.players.items():
                    is_turn = (pid == game._current_turn)
                    self._send_message(
                        player_info['socket'],
                        'game_state',
                        code=212,
                        gameId=game_id,
                        playerId=pid,
                        message="¡Partida iniciada!" if is_turn else "Tu oponente va primero",
                        gameState="IN_PROGRESS",
                        yourTurn=is_turn
                    )
                    
        except Exception as e:
            logger.error(f"Error colocando barcos: {e}")
            self._send_error(client_socket, 430, str(e))

    def _handle_attack(self, client_socket: socket.socket, player_id: Optional[str], data: Dict):
        """Maneja un ataque."""
        if not player_id:
            self._send_error(client_socket, 410, "Jugador no encontrado")
            return

        is_valid, error_msg = self.protocol.validate_attack_message(data)
        if not is_valid:
            self._send_error(client_socket, 402, error_msg)
            return

        game_id = data.get('gameId')
        coord_data = data.get('coordinate')
        coordinate = Coordinate(coord_data['x'], coord_data['y'])

        if game_id not in self.sessions:
            self._send_error(client_socket, 420, "Partida no encontrada")
            return

        session = self.sessions[game_id]
        game = session.game
        opponent_id = session.get_opponent_id(player_id)

        try:
            # Verificar que sea el turno del jugador
            if game.current_turn != player_id:
                self._send_error(client_socket, 442, "No es tu turno")
                return

            # Realizar ataque
            attack_result = game.attack(player_id, coordinate)
            outcome = attack_result.outcome

            logger.info(f"Jugador {player_id} atacó {coordinate} en partida {game_id}: {outcome.name}")

            # Preparar respuesta
            response_data = {
                'coordinate': {'x': coordinate.x, 'y': coordinate.y},
                'outcome': outcome.name.lower(),
                'shipType': attack_result.ship_type.name if attack_result.ship_type else None,
            }

            # Enviar al atacante
            self._send_message(
                client_socket,
                'attack_result',
                code=217,
                gameId=game_id,
                **response_data
            )

            # Enviar al oponente
            if opponent_id:
                opponent_socket = session.players[opponent_id]['socket']
                self._send_message(
                    opponent_socket,
                    'opponent_move',
                    code=217,
                    gameId=game_id,
                    **response_data
                )

            # Verificar fin de juego
            if game.state == GameState.FINISHED:
                winner_id = game.winner
                loser_id = opponent_id if winner_id == player_id else player_id
                
                # Notificar a ambos jugadores
                for pid, player_info in session.players.items():
                    is_winner = (pid == winner_id)
                    self._send_message(
                        player_info['socket'],
                        'game_over',
                        code=220,
                        gameId=game_id,
                        playerId=pid,
                        winner=winner_id,
                        loser=loser_id,
                        message="¡Victoria!" if is_winner else "Derrota"
                    )
            else:
                # Cambiar turno
                next_player = session.get_opponent_id(game.current_turn)
                
                for pid, player_info in session.players.items():
                    is_turn = (pid == next_player)
                    self._send_message(
                        player_info['socket'],
                        'game_state',
                        code=215 if is_turn else 216,
                        gameId=game_id,
                        playerId=pid,
                        yourTurn=is_turn
                    )
                    
        except Exception as e:
            logger.error(f"Error en ataque: {e}")
            self._send_error(client_socket, 440, str(e))

    def _handle_surrender(self, client_socket: socket.socket, player_id: Optional[str], data: Dict):
        """Maneja rendición de un jugador."""
        if not player_id:
            self._send_error(client_socket, 410, "Jugador no encontrado")
            return

        game_id = data.get('gameId')

        if game_id not in self.sessions:
            self._send_error(client_socket, 420, "Partida no encontrada")
            return

        session = self.sessions[game_id]
        opponent_id = session.get_opponent_id(player_id)

        # Marcar game como terminado
        game = session.game
        game._state = GameState.FINISHED
        game._winner = opponent_id
        
        logger.info(f"Jugador {player_id} se rindió en partida {game_id}")

        # Notificar a ambos jugadores
        for pid, player_info in session.players.items():
            is_winner = (pid == opponent_id)
            self._send_message(
                player_info['socket'],
                'game_over',
                code=220,
                gameId=game_id,
                winner=opponent_id,
                message="¡Victoria!" if is_winner else "Tu oponente se rindió",
                reason="surrender"
            )

        # Limpiar sesión
        self._cleanup_session(game_id)

    def _send_game_state(self, client_socket: socket.socket, game_id: str, player_id: str):
        """Envía el estado actual del juego."""
        if game_id not in self.sessions:
            self._send_error(client_socket, 420, "Partida no encontrada")
            return

        session = self.sessions[game_id]
        game = session.game

        self._send_message(
            client_socket,
            'game_state',
            code=200,
            gameId=game_id,
            playerId=player_id,
            gameState=game.state.name,
            currentTurn=game.current_turn,
            yourTurn=(game.current_turn == player_id)
        )

    def _cleanup_client(self, client_socket: socket.socket, player_id: Optional[str]):
        """Limpia recursos de un cliente desconectado."""
        try:
            client_socket.close()
        except:
            pass

        if player_id and player_id in self.player_sessions:
            game_id = self.player_sessions[player_id]
            
            if game_id in self.sessions:
                session = self.sessions[game_id]
                
                # Notificar al oponente
                opponent_id = session.get_opponent_id(player_id)
                if opponent_id and opponent_id in session.players:
                    opponent_socket = session.players[opponent_id]['socket']
                    self._send_message(
                        opponent_socket,
                        'notification',
                        code=450,
                        message="Tu oponente se desconectó. Esperando reconexión..."
                    )
                
                # Eliminar jugador
                if player_id in session.players:
                    del session.players[player_id]
                
                # Si la partida está vacía, eliminarla
                if len(session.players) == 0:
                    self._cleanup_session(game_id)
            
            del self.player_sessions[player_id]

        if client_socket in self.player_sockets:
            del self.player_sockets[client_socket]

        logger.info(f"Cliente desconectado: {player_id}")

    def _cleanup_session(self, game_id: str):
        """Limpia una sesión de juego."""
        if game_id in self.sessions:
            session = self.sessions[game_id]
            
            # Desconectar todos los jugadores
            for player_id in list(session.players.keys()):
                if player_id in self.player_sessions:
                    del self.player_sessions[player_id]
            
            del self.sessions[game_id]
            logger.info(f"Sesión {game_id} eliminada")
