"""
Servidor de Batalla Naval usando WebSockets.
Arquitectura con separación de responsabilidades:
- GameSession genera mensajes (qué y para quién)
- BatallaNavalServer los envía (cómo)

"""
import socket
import threading
import json
import base64
import hashlib
import logging
import uuid
import random
from typing import Dict, Optional, Tuple, List
from datetime import datetime, timedelta
from dataclasses import dataclass

from game.game import Game
from game.ship import Ship, ShipOrientation, Coordinate
from game.enums import GameState, ShipType
from network.protocol import Protocol
from config import ServerConfig

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(filename)s:%(lineno)d | %(message)s',
    datefmt='%H:%M:%S',
    force=True
)



@dataclass
class OutgoingMessage:
    """Mensaje que debe enviarse a un jugador específico."""
    player_id: str
    payload: Dict


def generate_valid_ship_placement(board_size: int = 10) -> Dict[str, list]:
    """
    Genera una disposición aleatoria válida de barcos sin solapamientos.
    
    Garantiza que:
    - No haya solapamientos entre barcos
    - Todos los barcos estén dentro del tablero
    - Cada barco esté alineado (horizontal o vertical)
    - Solo haya un barco de cada tipo
    
    Args:
        board_size: Tamaño del tablero (default: 10x10)
    
    Returns:
        Diccionario con ships: [
            {
                'type': 'AIRCRAFT_CARRIER|BATTLESHIP|CRUISER|DESTROYER|SUBMARINE',
                'orientation': 'HORIZONTAL|VERTICAL',
                'positions': [{'x': int, 'y': int}, ...]
            }
        ]
    """
    ship_types = {
        'AIRCRAFT_CARRIER': 5,
        'BATTLESHIP': 4,
        'CRUISER': 3,
        'DESTROYER': 3,
        'SUBMARINE': 2,
    }
    
    occupied = set()
    ships = []
    
    for ship_type, length in ship_types.items():
        placed = False
        max_attempts = 100
        attempts = 0
        
        while not placed and attempts < max_attempts:
            attempts += 1
            
            orientation = random.choice(['HORIZONTAL', 'VERTICAL'])
            if orientation == 'HORIZONTAL':
                max_x = board_size - length
                start_x = random.randint(0, max_x)
                start_y = random.randint(0, board_size - 1)
            else:
                start_x = random.randint(0, board_size - 1)
                max_y = board_size - length
                start_y = random.randint(0, max_y)
            
            positions = []
            if orientation == 'HORIZONTAL':
                positions = [{'x': start_x + i, 'y': start_y} for i in range(length)]
            else:
                positions = [{'x': start_x, 'y': start_y + i} for i in range(length)]
            
            overlap = False
            for pos in positions:
                if (pos['x'], pos['y']) in occupied:
                    overlap = True
                    break
            
            if not overlap:
                for pos in positions:
                    occupied.add((pos['x'], pos['y']))
                
                ships.append({
                    'type': ship_type,
                    'orientation': orientation,
                    'positions': positions
                })
                placed = True
        
        if not placed:
            return generate_valid_ship_placement(board_size)
    
    return {'ships': ships}


class GameSession:
    """
    Representa una sesión de juego independiente desde su creación hasta su fin.
    
    Responsabilidad: Generar los mensajes que deben enviarse basado en la lógica del juego.
    Esta clase es la "máquina de estados" que coordina todo lo que sucede en una partida,
    desde la adición de jugadores hasta el fin de la partida.
    """

    def __init__(self, session_id: str, board_size: int = 10):
        """
        Inicializa una sesión de juego.
        
        Args:
            session_id: ID único de esta sesión de juego.
            board_size: Tamaño del tablero para ambos jugadores (defecto: 10x10).
            
        """
        self.logger = logging.getLogger("GameSession")
        self.session_id = session_id
        self.game = Game(board_size)
        self.players: Dict[str, dict] = {}
        
        self.ships_placement_lock = threading.Lock()
        
        self.disconnected_player: Optional[str] = None
        self.reconnect_timeout: Optional[datetime] = None
        
        self.created_at = datetime.now()
        self.started_at: Optional[datetime] = None
        self.finished_at: Optional[datetime] = None
        self.last_activity_at: datetime = datetime.now()
        self.is_active = True
        
        self.logger.info(f"[SESSION {self.session_id[:8]}] Sesión créada (reconexión timeout: {ServerConfig().TIMEOUT_RECONNECTION}s)")

    def add_player(self, player_id: str, player_name: str, client_socket: socket.socket) -> Tuple[bool, List[OutgoingMessage]]:
        """
        Añade un jugador a la sesión y genera los mensajes correspondientes.
        
        Cuando se añade el primer jugador, notifica que se está esperando oponente.
        Cuando se añade el segundo jugador, notifica a ambos que pueden comenzar a colocar barcos.
        
        Args:
            player_id: ID único del jugador a añadir.
            player_name: Nombre del jugador (visible para otros).
            client_socket: Socket del cliente para enviar/recibir mensajes.
        
        Returns:
            Tupla (éxito: bool, mensajes: List[OutgoingMessage]). 
            éxito es False si la sesión está llena o hay error.
        """
        if len(self.players) >= 2:
            self.logger.warning(f"[SESSION {self.session_id[:8]}] Intento de añadir jugador pero sesión está llena")
            return False, []

        try:
            self.game.add_player(player_id)
            self.players[player_id] = {
                'socket': client_socket,
                'name': player_name,
                'connected': True
            }
            self.logger.info(f"[SESSION {self.session_id[:8]}] Jugador {player_id[:8]} ({player_name}) añadido")
            
            messages: List[OutgoingMessage] = []
            
            if len(self.players) == 1:
                msg = OutgoingMessage(
                    player_id,
                    {
                        'type': 'game_state',
                        'code': 210,  # WAITING_FOR_OPPONENT
                        'gameId': self.session_id,
                        'playerId': player_id,
                        'state': self.game.state.name,
                        'playerCount': 1,
                        'message': 'Esperando al oponente...'
                    }
                )
                messages.append(msg)
            
            elif len(self.players) == 2:
                for pid, player_info in self.players.items():
                    other_player_id = self._get_other_player(pid)
                    other_player_name = self.players[other_player_id]['name'] if other_player_id else 'Desconocido'
                    msg = OutgoingMessage(
                        pid,
                        {
                            'type': 'game_state',
                            'code': 211,  # BOTH_PLAYERS_READY
                            'gameId': self.session_id,
                            'playerId': pid,
                            'playerName': player_info['name'],
                            'opponentName': other_player_name,
                            'state': self.game.state.name,
                            'playerCount': 2,
                            'players': {p_id: self.players[p_id]['name'] for p_id in self.players},
                            'message': 'Ambos jugadores listos. Coloquen sus barcos.'
                        }
                    )
                    messages.append(msg)
            
            return True, messages
            
        except Exception as e:
            self.logger.error(f"[SESSION {self.session_id[:8]}] Error al añadir jugador: {e}")
            return False, []

    def place_ships(self, player_id: str, ships_data: list) -> Tuple[bool, List[OutgoingMessage]]:
        """
        Coloca barcos para un jugador y genera mensajes de confirmación.
        
        Si ambos jugadores colocaron barcos, inicia el juego inmediatamente.
        Si solo uno colocó, notifica al jugador que espere al oponente.
        
        Args:
            player_id: ID del jugador que está colocando los barcos.
            ships_data: Lista de diccionarios con datos de los barcos 
                       (type, positions, orientation).
        
        Returns:
            Tupla (éxito: bool, mensajes: List[OutgoingMessage]).
            éxito es False si hay error en la colocación de barcos.
        """
        with self.ships_placement_lock:
            try:
                ships = []
                for ship_data in ships_data:
                    orientation = ShipOrientation[ship_data['orientation'].upper()]
                    ship_type = ShipType[ship_data['type']]
                    ship_id = player_id[:8] + "_" + str(ship_type.name)
                    positions = [
                        Coordinate(
                            x=coord['x'],
                            y=coord['y']
                        )
                        for coord in ship_data['positions']
                    ]
                    if orientation == ShipOrientation.HORIZONTAL:
                        positions.sort(key=lambda c: c.y)
                    else:  # VERTICAL
                        positions.sort(key=lambda c: c.x)
                    
                    ship = Ship(
                        ship_id=ship_id,
                        ship_type=ship_type,
                        positions=positions,
                        orientation=orientation
                    )
                    ships.append(ship)
                
                for ship in ships:
                    self.game.place_ship(player_id, ship)

                self.logger.info(f"[SESSION {self.session_id[:8]}] Jugador {player_id[:8]} colocó sus barcos")
                
                
                messages: List[OutgoingMessage] = []
                
                all_placed = self.game.all_ships_placed()
                
                if all_placed:
                    self.game.finish_ship_placement()
                    self.started_at = datetime.now()
                    self.logger.info(f"[SESSION {self.session_id[:8]}] Ambos jugadores listos, juego iniciado")
                    
                    current_turn = self.game.current_turn
                    self.logger.info(f"[SESSION {self.session_id[:8]}] Juego iniciado. Turno inicial: {current_turn}")
                    
                    # === PASO 1: Enviar game_state 212 (GAME_STARTED) a ambos ===
                    for pid in self.players:
                        other_player_id = self._get_other_player(pid)
                        if other_player_id not in self.players:
                            continue
                        
                        other_player_name = self.players[other_player_id]['name']
                        msg = OutgoingMessage(
                            pid,
                            {
                                'type': 'game_state',
                                'code': 212,  # GAME_STARTED
                                'gameId': self.session_id,
                                'playerId': pid,
                                'playerName': self.players[pid]['name'],
                                'opponentName': other_player_name,
                                'state': self.game.state.name,
                                'message': '¡Juego iniciado!'
                            }
                        )
                        messages.append(msg)
                        self.logger.info(f"[SESSION {self.session_id[:8]}] Mensaje 212 (GAME_STARTED) enviado a {pid}")
                    
                    # === PASO 2: Enviar game_state 215/216 para asignar turno inicial ===
                    for pid in self.players:
                        other_player_id = self._get_other_player(pid)
                        if other_player_id not in self.players:
                            continue
                        
                        other_player_name = self.players[other_player_id]['name']
                        is_your_turn = (pid == current_turn)
                        code = 215 if is_your_turn else 216  # 215 = YOUR_TURN, 216 = WAITING
                        
                        msg = OutgoingMessage(
                            pid,
                            {
                                'type': 'game_state',
                                'code': code,
                                'gameId': self.session_id,
                                'playerId': pid,
                                'playerName': self.players[pid]['name'],
                                'opponentName': other_player_name,
                                'state': self.game.state.name,
                                'currentTurn': current_turn,
                                'yourTurn': is_your_turn,
                                'message': '¡Es tu turno!' if is_your_turn else 'Esperando a tu oponente...'
                            }
                        )
                        messages.append(msg)
                        self.logger.info(f"[SESSION {self.session_id[:8]}] Mensaje {code} enviado a {pid}")
                else:
                    # Solo un jugador colocó, esperar al otro
                    other_player_id = self._get_other_player(player_id)
                    if other_player_id:
                        other_player_name = self.players[other_player_id]['name']
                        msg = OutgoingMessage(
                            player_id,
                            {
                                'type': 'game_state',
                                'code': 213,  # WAITING_FOR_SHIPS
                                'gameId': self.session_id,
                                'playerId': player_id,
                                'playerName': self.players[player_id]['name'],
                                'opponentName': other_player_name,
                                'message': 'Barcos colocados. Esperando al oponente...'
                            }
                        )
                        messages.append(msg)
                        self.logger.info(f"[SESSION {self.session_id[:8]}] {player_id[:8]} colocó barcos, esperando a {other_player_id}")
                
                return True, messages
                
            except Exception as e:
                self.logger.error(f"[SESSION {self.session_id[:8]}] Error al colocar barcos: {e}")
                import traceback
                self.logger.error(traceback.format_exc())
                return False, []

    def execute_attack(self, attacker_id: str, coordinate_dict: dict) -> Tuple[bool, List[OutgoingMessage]]:
        """
        Ejecuta un ataque y genera todos los mensajes correspondientes.
        
        Procesa el ataque, actualiza el estado del juego, y genera los siguientes mensajes:
        - Respuesta al atacante (resultado del ataque)
        - Notificación al defensor (recibió ataque)
        - Cambio de turno (a ambos jugadores)
        - Fin de juego (si aplica, con ganador/perdedor)
        
        Args:
            attacker_id: ID del jugador que ataca.
            coordinate_dict: Diccionario con coordenadas del ataque {'x': int, 'y': int}.
        
        Returns:
            Tupla (éxito: bool, mensajes: List[OutgoingMessage]).
            éxito es False si el ataque es inválido.
        """
        try:
            coord = Coordinate(x=coordinate_dict['x'], y=coordinate_dict['y'])
            result = self.game.attack(attacker_id, coord)
            
            defender_id = result.defender_id
            if result.outcome.name in ['HIT', 'SHIP_SUNK']:
                self.logger.info(
                    f"[SESSION {self.session_id[:8]}] Ataque de {attacker_id[:8]} a ({coord.x}, {coord.y}): {result.outcome.name}"
                )
            
            messages: List[OutgoingMessage] = []            
            attack_result_msg = OutgoingMessage(
                attacker_id,
                {
                    'type': 'attack_result',
                    'code': 217,  # ATTACK_REGISTERED
                    'gameId': self.session_id,
                    'playerId': attacker_id,
                    'outcome': result.outcome.name,  # HIT, MISS, SHIP_SUNK, etc
                    'x': coord.x,
                    'y': coord.y,
                    'shipSunk': result.ship_sunk,
                    'message': f"Ataque a ({coord.x}, {coord.y}) - {result.outcome.name}"
                }
            )
            messages.append(attack_result_msg)
            self.logger.debug(f"[SESSION {self.session_id[:8]}] attack_result enviado a {attacker_id[:8]}")
            
            # =====================================================================
            # MENSAJE 2: opponent_attack al DEFENSOR
            # =====================================================================
            if defender_id in self.players:
                attacker_name = self.players[attacker_id]['name']
                
                opponent_attack_msg = OutgoingMessage(
                    defender_id,
                    {
                        'type': 'opponent_attack',
                        'code': 217,  # ATTACK_REGISTERED
                        'gameId': self.session_id,
                        'playerId': defender_id,
                        'outcome': result.outcome.name,  # HIT, MISS, SHIP_SUNK, etc
                        'x': coord.x,
                        'y': coord.y,
                        'shipSunk': result.ship_sunk,
                        'opponentName': attacker_name,
                        'message': f"{attacker_name} atacó en ({coord.x}, {coord.y}) - {result.outcome.name}"
                    }
                )
                messages.append(opponent_attack_msg)
                self.logger.debug(f"[SESSION {self.session_id[:8]}] opponent_attack enviado a {defender_id}")
            
            # =====================================================================
            # MENSAJE 3: game_state 220 (GAME_OVER) o 215/216 (TURN_CHANGE)
            # =====================================================================
            if result.game_finished:
                # Juego terminado - enviar code 220 a ambos
                winner_id = self.game.winner
                self.finished_at = datetime.now()
                self.is_active = False  # Marcar sesión como inactiva para permitir limpieza
                self.logger.info(f"[SESSION {self.session_id[:8]}] ¡Juego terminado! Ganador: {winner_id}")

                # calcular estadísticas de cada jugador
                statistics: Dict[str, dict] = {}
                for pid in self.players:
                    player_obj = self.game._players.get(pid)
                    if player_obj:
                        stats_obj = player_obj.get_stadistics_resume()
                        statistics[pid] = stats_obj.to_dict()

                for pid in self.players:
                    other_id = self._get_other_player(pid)
                    other_name = self.players[other_id]['name'] if other_id else 'Desconocido'

                    winner_name = self.players[winner_id]['name'] if winner_id and winner_id in self.players else 'Desconocido'

                    game_over_msg = OutgoingMessage(
                        pid,
                        {
                            'type': 'game_state',
                            'code': 220,  # GAME_OVER
                            'gameId': self.session_id,
                            'playerId': pid,
                            'playerName': self.players[pid]['name'],
                            'opponentName': other_name,
                            'winner': winner_id,
                            'state': 'FINISHED',
                            'statistics': statistics[pid],
                            'message': f"¡Game Over! Ganador: {winner_name}",
                        }
                    )
                    messages.append(game_over_msg)
                    self.logger.debug(f"[SESSION {self.session_id[:8]}] game_state 220 enviado a {pid}")
            else:
                # Cambiar turno - enviar code 215/216 a ambos
                current_turn = self.game.current_turn
                self.logger.debug(f"[SESSION {self.session_id[:8]}] Turno cambiado a: {current_turn}")
                
                for pid in self.players:
                    other_id = self._get_other_player(pid)
                    other_name = self.players[other_id]['name'] if other_id else 'Desconocido'
                    is_your_turn = (pid == current_turn)
                    code = 215 if is_your_turn else 216  # 215 = YOUR_TURN, 216 = WAITING
                    
                    # Calcular barcos restantes
                    your_player = self.game._players.get(pid)
                    other_player = self.game._players.get(other_id) if other_id else None
                    your_ships_remaining = sum(1 for ship in your_player.get_ships().values() if not ship.is_sunk()) if your_player else 0
                    enemy_ships_remaining = sum(1 for ship in other_player.get_ships().values() if not ship.is_sunk()) if other_player else 0
                    
                    turn_msg = OutgoingMessage(
                        pid,
                        {
                            'type': 'game_state',
                            'code': code,
                            'gameId': self.session_id,
                            'playerId': pid,
                            'playerName': self.players[pid]['name'],
                            'opponentName': other_name,
                            'currentTurn': current_turn,
                            'yourTurn': is_your_turn,
                            'state': 'IN_PROGRESS',
                            'yourShipsRemaining': your_ships_remaining,
                            'enemyShipsRemaining': enemy_ships_remaining,
                            'message': '¡Es tu turno!' if is_your_turn else 'Esperando al oponente...'
                        }
                    )
                    messages.append(turn_msg)
                    self.logger.debug(f"[SESSION {self.session_id[:8]}] game_state {code} enviado a {pid}")
            
            return True, messages
            
        except Exception as e:
            self.logger.error(f"[SESSION {self.session_id[:8]}] Error en ataque: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False, [OutgoingMessage(attacker_id, {
                'type': 'error',
                'code': 440,
                'message': f"Error en ataque: {str(e)}"
            })]

    def handle_surrender(self, player_id: str) -> Tuple[bool, List[OutgoingMessage]]:
        """
        Maneja la rendición de un jugador.
        
        Finaliza inmediatamente el juego, dando la victoria al otro jugador,
        y genera mensajes de fin de juego para ambos.
        
        Args:
            player_id: ID del jugador que se rinde.
        
        Returns:
            Tupla (éxito: bool, mensajes: List[OutgoingMessage]).
        """
        try:
            # El otro jugador gana
            winner_id = self._get_other_player(player_id)
            self.game._state = GameState.FINISHED
            self.game._winner = winner_id
            self.finished_at = datetime.now()
            self.is_active = False  # Marcar sesión como inactiva para permitir limpieza
            
            self.logger.info(f"[SESSION {self.session_id[:8]}] Jugador {player_id[:8]} se rindió")
            
            messages: List[OutgoingMessage] = []
            
            for pid in self.players:
                other_id = self._get_other_player(pid)
                other_name = self.players[other_id]['name'] if other_id else 'Desconocido'
                game_over_payload = {
                    'type': 'game_over',
                    'code': 220,
                    'gameId': self.session_id,
                    'playerId': pid,
                    'playerName': self.players[pid]['name'],
                    'opponentName': other_name,
                    'winner': winner_id,
                    'isWinner': (pid == winner_id),
                    'reason': 'surrender',
                    'message': 'Juego finalizado'
                }
                messages.append(OutgoingMessage(pid, game_over_payload))
            
            return True, messages
            
        except Exception as e:
            self.logger.error(f"[SESSION {self.session_id[:8]}] Error en rendición: {e}")
            return False, []

    def reconnect_player(self, player_id: str, client_socket: socket.socket) -> Tuple[bool, List[OutgoingMessage]]:
        """
        Reconecta un jugador después de una desconexión.
        
        Actualiza el socket del jugador, marca como reconectado, y genera mensajes
        de confirmación de reconexión y notificación al oponente.
        
        Args:
            player_id: ID del jugador que se reconecta.
            client_socket: Nuevo socket del cliente.
        
        Returns:
            Tupla (éxito: bool, mensajes: List[OutgoingMessage]).
            éxito es False si el jugador no estaba en la sesión.
        """
        try:
            if player_id not in self.players:
                return False, []
            
            self.players[player_id]['socket'] = client_socket
            self.players[player_id]['connected'] = True
            self.disconnected_player = None
            self.reconnect_timeout = None
            
            self.logger.info(f"[SESSION {self.session_id[:8]}] Jugador {player_id[:8]} reconectado")
            
            messages: List[OutgoingMessage] = []
            
            game_state = self.game.get_public_state_for(player_id)
            other_pid = self._get_other_player(player_id)
            other_name = self.players[other_pid]['name'] if other_pid else 'Desconocido'
            reconnect_msg = OutgoingMessage(
                player_id,
                {
                    'type': 'game_state',
                    'code': 231,  # RECONNECT_SUCCESS
                    'gameId': self.session_id,
                    'playerId': player_id,
                    'playerName': self.players[player_id]['name'],
                    'opponentName': other_name,
                    'state': game_state,
                    'message': 'Reconectado exitosamente'
                }
            )
            messages.append(reconnect_msg)
            
            if other_pid:
                notification = OutgoingMessage(
                    other_pid,
                    {
                        'type': 'notification',
                        'code': 231,
                        'gameId': self.session_id,
                        'message': 'Tu oponente se reconectó'
                    }
                )
                messages.append(notification)
            
            return True, messages
            
        except Exception as e:
            self.logger.error(f"[SESSION {self.session_id[:8]}] Error en reconexión: {e}")
            return False, []

    def mark_player_disconnected(self, player_id: str) -> List[OutgoingMessage]:
        """
        Marca un jugador como desconectado e inicia un timer configurable.
        
        Si el jugador no se reconecta dentro del TIMEOUT_RECONNECTION configurado,
        la sesión terminará dando la victoria al otro jugador.
        
        Args:
            player_id: ID del jugador que se desconectó.
        
        Returns:
            Lista de mensajes a enviar (notificación al otro jugador).
        """
        if player_id in self.players:
            self.players[player_id]['connected'] = False
            self.disconnected_player = player_id
            
            timeout_seconds = int(ServerConfig().TIMEOUT_RECONNECTION)
            self.reconnect_timeout = datetime.now() + timedelta(seconds=timeout_seconds)
            
            self.logger.warning(
                f"[SESSION {self.session_id[:8]}] Jugador {player_id[:8]} desconectado. "
                f"Timer: {timeout_seconds}s"
            )
            
            messages: List[OutgoingMessage] = []
            
            other_id = self._get_other_player(player_id)
            if other_id:
                notification = OutgoingMessage(
                    other_id,
                    {
                        'type': 'notification',
                        'code': 450,  # OPPONENT_DISCONNECTED
                        'gameId': self.session_id,
                        'message': f'Tu oponente se desconectó. Esperando reconexión ({timeout_seconds}s)...'
                    }
                )
                messages.append(notification)
            
            return messages
        
        return []

    def check_reconnection_timeout(self) -> Tuple[bool, List[OutgoingMessage]]:
        """
        Verifica si el timer de reconexión ha expirado.
        
        Si ha expirado, finaliza el juego de forma inmediata dando victoria
        al jugador conectado, y retorna mensajes de fin de juego para ambos.
        
        El cliente que se desconectó recibirá un mensaje especial indicándole
        que debe limpiar sus datos (localStorage, sessionStorage).
        
        Returns:
            Tupla (session_should_close: bool, mensajes: List[OutgoingMessage])
            True si la sesión debe cerrarse después de enviar los mensajes.
        """
        if not self.disconnected_player or not self.reconnect_timeout:
            return False, []

        if datetime.now() > self.reconnect_timeout:
            winner_id = self._get_other_player(self.disconnected_player)
            loser_id = self.disconnected_player
            
            self.logger.warning(
                f"[SESSION {self.session_id[:8]}] Reconexión expirada. "
                f"{winner_id} gana por timeout de reconexión."
            )
            
            self.game._state = GameState.FINISHED
            self.game._winner = winner_id
            self.is_active = False
            self.finished_at = datetime.now()
            
            messages: List[OutgoingMessage] = []
            
            if winner_id and self.players[winner_id]['connected']:
                game_over_payload = {
                    'type': 'game_over',
                    'code': 220,
                    'gameId': self.session_id,
                    'playerId': winner_id,
                    'winner': winner_id,
                    'isWinner': True,
                    'reason': 'opponent_timeout',
                    'message': 'Ganaste por timeout del oponente'
                }
                messages.append(OutgoingMessage(winner_id, game_over_payload))
            
            disconnected_msg = {
                'type': 'game_over',
                'code': 220,
                'gameId': self.session_id,
                'playerId': loser_id,
                'winner': winner_id,
                'isWinner': False,
                'reason': 'reconnect_timeout',
                'message': 'Perdiste por no reconectarte a tiempo',
                'clearSession': True  # Señal especial para el cliente
            }
            messages.append(OutgoingMessage(loser_id, disconnected_msg))
            
            return True, messages
        
        return False, []

    def _get_other_player(self, player_id: str) -> Optional[str]:
        """
        Obtiene el ID del otro jugador en la sesión.
        
        Args:
            player_id: ID de un jugador en la sesión.
        
        Returns:
            ID del otro jugador, o None si solo hay un jugador.
        """
        for pid in self.players:
            if pid != player_id:
                return pid
        return None

    def is_full(self) -> bool:
        """
        Verifica si hay dos jugadores conectados en la sesión.
        
        Returns:
            True si hay 2 jugadores conectados, False en caso contrario.
        """
        return len([p for p in self.players.values() if p['connected']]) >= 2

    def is_game_in_progress(self) -> bool:
        """
        Verifica si el juego está actualmente en progreso.
        
        Returns:
            True si el estado del juego es IN_PROGRESS, False en caso contrario.
        """
        return self.game.state == GameState.IN_PROGRESS

    def is_game_finished(self) -> bool:
        """
        Verifica si el juego ha terminado.
        
        Returns:
            True si el estado del juego es FINISHED, False en caso contrario.
        """
        return self.game.state == GameState.FINISHED

    def __repr__(self) -> str:
        return f"GameSession({self.session_id[:8]}, players={len(self.players)}, state={self.game.state.name})"


class BatallaNavalServer:
    """
    Servidor de WebSocket que coordina múltiples GameSessions de forma concurrente.
    
    Responsabilidad principal: Aceptar conexiones WebSocket, validar mensajes y 
    enviar respuestas. NO maneja la lógica de juego, solo la lógica de red.
    La lógica de juego se delega a instancias de GameSession.
    
    Flujo de arquitectura:
    1. Cliente conecta → BatallaNavalServer establece WebSocket
    2. Cliente envía mensaje → BatallaNavalServer valida y parsea
    3. BatallaNavalServer delega a GameSession apropiada
    4. GameSession genera mensajes (qué y para quién)
    5. BatallaNavalServer envía mensajes a clientes (cómo)
    """

    def __init__(self, host: str = '0.0.0.0', port: int = 8080):
        """
        Inicializa el servidor de WebSocket.
        
        Args:
            host: Dirección IP a la que se une el servidor (defecto: 0.0.0.0 = todas las interfaces).
            port: Puerto TCP en el que escucha (defecto: 8080).
        """
        self.host = host
        self.port = port
        self.protocol = Protocol()
        
        self.sessions: Dict[str, GameSession] = {}
        self.player_to_session: Dict[str, str] = {}
        self.socket_to_player: Dict[socket.socket, str] = {}
        self.socket_to_session: Dict[socket.socket, str] = {}
        
        self.server_socket = None
        self.running = False
        
        self.cleanup_thread = None
        self.cleanup_running = False

        self.logger = logging.getLogger("ServerNaval")


    def start(self):
        """
        Inicia el servidor WebSocket y comienza a aceptar conexiones.
        
        Establece un socket TCP listening, acepta conexiones de clientes,
        realiza handshake WebSocket, y maneja toda la comunicación
        con cada cliente en un thread separado.
        
        También inicia un thread de limpieza automática para verificar
        timeouts de reconexión y sesiones inactivas.
        
        Para detener el servidor, establecer self.running = False o usar Ctrl+C.
        """
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            self.server_socket.settimeout(150.0)
            
            self.running = True
            
            self.cleanup_running = True
            self.cleanup_thread = threading.Thread(
                target=self._cleanup_loop,
                daemon=True,
                name="Cleanup-Thread"
            )
            self.cleanup_thread.start()
            
            self.logger.info(f"Servidor iniciado en {self.host}:{self.port}")
            self.logger.info(f"Thread de limpieza iniciado (intervalo: {int(ServerConfig().CLEANUP_CHECK_INTERVAL)}s)")
            
            while self.running:
                try:
                    client_socket, client_address = self.server_socket.accept()
                    self.logger.info(f"Conexión desde {client_address}")
                    
                    thread = threading.Thread(
                        target=self._handle_client,
                        args=(client_socket, client_address),
                        daemon=True
                    )
                    thread.start()
                    
                except socket.timeout:
                    continue
                except Exception as e:
                    if self.running:
                        self.logger.error(f"Error aceptando conexión: {e}")
                        
        except KeyboardInterrupt:
            self.logger.info("Interrupción detectada (Ctrl+C)")
        except Exception as e:
            self.logger.error(f"Error en servidor: {e}")
        finally:
            self.stop()

    def stop(self):
        """
        Detiene el servidor y cierra todas las conexiones abiertas.
        
        Establece running = False, cierra el socket del servidor,
        detiene el thread de limpieza, e impide que acepte nuevas conexiones.
        """
        self.logger.info("Deteniendo servidor...")
        self.running = False
        self.cleanup_running = False
        
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        
        if self.cleanup_thread:
            try:
                self.cleanup_thread.join(timeout=5)
            except:
                pass
        
        self.logger.info("Servidor detenido")

    def _cleanup_loop(self):
        """
        Loop de limpieza que se ejecuta periódicamente en un thread separado.
        
        Verifica:
        1. Timeouts de reconexión de jugadores desconectados
        2. Sesiones inactivas que deben cerrarse
        
        Ejecuta continuamente cada CLEANUP_CHECK_INTERVAL segundos.
        """
        
        while self.cleanup_running:
            try:
                import time
                time.sleep(int(ServerConfig().CLEANUP_CHECK_INTERVAL))
                
                if not self.cleanup_running:
                    break
                
                sessions_to_remove = []
                for session_id, session in list(self.sessions.items()):
                    should_close, messages = session.check_reconnection_timeout()
                    
                    if should_close:
                        self.logger.warning(
                            f"[SESSION {session_id[:8]}] Cerrando sesión por timeout de reconexión"
                        )
                        self._send_messages(session, messages)
                        sessions_to_remove.append(session_id)
                    
                    elif messages:
                        self._send_messages(session, messages)
                    
                    now = datetime.now()
                    time_since_creation = (now - session.created_at).total_seconds()
                    
                    if (len(session.players) == 1 and 
                        time_since_creation > int(ServerConfig().TIMEOUT_WAITING_FOR_OPPONENT)):
                        self.logger.warning(
                            f"[SESSION {session_id[:8]}] Cerrando por timeout de espera de oponente "
                            f"({time_since_creation}s)"
                        )
                        sessions_to_remove.append(session_id)
                
                for session_id in sessions_to_remove:
                    self._remove_session(session_id)
                    
            except Exception as e:
                self.logger.error(f"Error en cleanup_loop: {e}")

    def _remove_session(self, session_id: str):
        """
        Elimina una sesión completamente del servidor.
        
        Limpia mapeos, cierra conexiones y registra el evento.
        
        Args:
            session_id: ID de la sesión a eliminar.
        """
        if session_id not in self.sessions:
            return
        
        session = self.sessions[session_id]
        
        for player_id in session.players:
            if player_id in self.player_to_session:
                del self.player_to_session[player_id]
        
        sockets_to_remove = []
        for sock, pid in list(self.socket_to_player.items()):
            if pid in session.players:
                sockets_to_remove.append(sock)
        
        for sock in sockets_to_remove:
            if sock in self.socket_to_player:
                del self.socket_to_player[sock]
            if sock in self.socket_to_session:
                del self.socket_to_session[sock]
        
        del self.sessions[session_id]
        
        self.logger.info(f"[SESSION {session_id[:8]}] Sesión eliminada del servidor")

    def _handle_client(self, client_socket: socket.socket, client_address: Tuple):
        """
        Maneja la comunicación completa con un cliente en un thread separado.
        
        Realiza el handshake WebSocket, recibe mensajes en bucle,
        valida y procesa cada mensaje según su tipo, y se dispone
        de limpieza cuando el cliente se desconecta.
        
        Args:
            client_socket: Socket TCP conectado al cliente.
            client_address: Tupla (host, puerto) de la conexión.
        """
        player_id = None
        session_id = None
        
        try:
            request = client_socket.recv(4096).decode('utf-8')
            if not self._websocket_handshake(client_socket, request):
                self.logger.warning(f"Handshake fallido desde {client_address}")
                client_socket.close()
                return

            self.logger.info(f"WebSocket establecido con {client_address}")
            
            while self.running:
                frame = self._receive_websocket_frame(client_socket)
                if not frame:
                    break

                try:
                    data = json.loads(frame)
                    is_valid, error_msg = self.protocol.validate_message(data)
                    
                    if not is_valid:
                        self.logger.warning(f"Mensaje inválido de {client_address}: {error_msg}\nContenido: {data}")
                        self._send_error(client_socket, 401, error_msg)
                        continue

                    msg_type = data.get('type')
                    
                    if msg_type == 'join_game':
                        player_id, session_id = self._handle_join_game(client_socket, data)
                    elif msg_type == 'reconnect':
                        player_id, session_id = self._handle_reconnect(client_socket, data)
                    elif msg_type == 'place_ships':
                        self._handle_place_ships(client_socket, player_id, session_id, data)
                    elif msg_type == 'attack':
                        self._handle_attack(client_socket, player_id, session_id, data)
                    elif msg_type == 'surrender':
                        self._handle_surrender(client_socket, player_id, session_id, data)
                    elif msg_type == 'generate_random_placement':
                        self._handle_generate_random_placement(client_socket, data)
                    elif msg_type == 'ping':
                        self._send_message(client_socket, {'type': 'pong', 'code': 200})
                    else:
                        self._send_error(client_socket, 400, f"Tipo desconocido: {msg_type}")
                        
                except json.JSONDecodeError:
                    self._send_error(client_socket, 401, "JSON inválido")
                except Exception as e:
                    self.logger.error(f"Error procesando mensaje: {e}")
                    self._send_error(client_socket, 500, "Error interno")
                    
        except Exception as e:
            self.logger.error(f"Error en cliente {client_address}: {e}")
        finally:
            self._cleanup_client(client_socket, player_id, session_id)

    def _handle_join_game(self, client_socket: socket.socket, data: dict) -> Tuple[Optional[str], Optional[str]]:
        """
        Maneja cuando un cliente se une a una partida.
        
        Busca una sesión disponible (sin juego completo).
        Si no la encuentra, crea una nueva.
        Añade el jugador a la sesión y envía mensajes de confirmación.
        
        Args:
            client_socket: Socket del cliente.
            data: Diccionario con datos del mensaje (playerId, playerName).
        
        Returns:
            Tupla (player_id: str, session_id: str) o (None, None) si hay error.
        """
        try:
            is_valid, error_msg = self.protocol.validate_join_message(data)
            if not is_valid:
                self._send_error(client_socket, 402, error_msg)
                return None, None

            player_id = str(uuid.uuid4())
            player_name = data.get('playerName', f"Unknown_{player_id[:5]}")
            
            available_session = None
            for sess in self.sessions.values():
                if not sess.is_full() and sess.game.state == GameState.WAITING_FOR_PLAYERS:
                    available_session = sess
                    break
            
            if available_session is None:
                session_id = str(uuid.uuid4())
                available_session = GameSession(session_id)
                self.sessions[session_id] = available_session
                self.logger.info(f"Nueva sesión creada: {session_id[:8]}")
            else:
                session_id = available_session.session_id
            
            success, messages = available_session.add_player(player_id, player_name, client_socket)
            if not success:
                self._send_error(client_socket, 422, "No se pudo añadir el jugador")
                return None, None
            
            self.player_to_session[player_id] = session_id
            self.socket_to_player[client_socket] = player_id
            self.socket_to_session[client_socket] = session_id
            
            self._send_messages(available_session, messages)
            
            return player_id, session_id
            
        except Exception as e:
            self.logger.error(f"Error en join_game: {e}")
            self._send_error(client_socket, 500, "Error interno")
            return None, None

    def _handle_reconnect(self, client_socket: socket.socket, data: dict) -> Tuple[Optional[str], Optional[str]]:
        """
        Maneja reconexión de un jugador a una partida en curso.
        
        Busca la sesión y al jugador, reconecta a ambos, y envía
        el estado actual del juego al jugador.
        
        Si la sesión no existe o ha expirado su timeout de reconexión,
        envía al cliente un mensaje especial indicándole que limpie sus datos.
        
        Args:
            client_socket: Socket del cliente.
            data: Diccionario con datos del mensaje (gameId, playerId).
        
        Returns:
            Tupla (player_id: str, session_id: str) o (None, None) si hay error.
        """
        try:
            is_valid, error_msg = self.protocol.validate_reconnect_message(data)
            if not is_valid:
                self._send_error(client_socket, 402, error_msg)
                return None, None

            player_id = data.get('playerId')
            session_id = data.get('gameId')
            if not player_id or not session_id:
                self._send_error(client_socket, 410, "Faltan playerId o gameId")
                return None, None
            
            if session_id not in self.sessions:
                self.logger.warning(f"Intento de reconexión a sesión inexistente: {session_id[:8]}")
                error_response = {
                    'type': 'game_over',
                    'code': 220,
                    'gameId': session_id,
                    'playerId': player_id,
                    'reason': 'session_expired',
                    'message': 'La sesión ha expirado',
                    'clearSession': True  # Señal para que el cliente limpie datos
                }
                self._send_message(client_socket, error_response)
                return None, None
            
            session = self.sessions[session_id]
            
            if player_id and player_id not in session.players:
                self.logger.warning(
                    f"Intento de reconexión con jugador inexistente: {player_id[:8]} en {session_id[:8]}"
                )
                error_response = {
                    'type': 'error',
                    'code': 410,
                    'message': 'Jugador no encontrado en la sesión',
                    'clearSession': True
                }
                self._send_message(client_socket, error_response)
                return None, None
            
            success, messages = session.reconnect_player(player_id, client_socket)
            if not success:
                self._send_error(client_socket, 420, "Error en reconexión")
                return None, None
            
            self.socket_to_player[client_socket] = player_id
            self.socket_to_session[client_socket] = session_id
            
            self._send_messages(session, messages)
            
            self.logger.info(f"[SESSION {session_id[:8]}] Jugador {player_id[:8]} reconectado")
            return player_id, session_id
            
        except Exception as e:
            self.logger.error(f"Error en reconnect: {e}")
            self._send_error(client_socket, 500, "Error interno")
            return None, None

    def _handle_place_ships(self, client_socket: socket.socket, player_id: Optional[str], 
                           session_id: Optional[str], data: dict):
        """
        Maneja la colocación de barcos de un jugador.
        
        Valida el mensaje, delega a la sesión de juego para procesar
        la colocación, y envía los mensajes generados.
        
        Args:
            client_socket: Socket del cliente.
            player_id: ID del jugador (puede ser None si no identificado).
            session_id: ID de la sesión (puede ser None si no identificado).
            data: Diccionario con datos de los barcos (gameId, playerId, ships).
        """
        if not player_id or not session_id:
            self._send_error(client_socket, 410, "Jugador o partida no identificados")
            return

        try:
            is_valid, error_msg = self.protocol.validate_place_ships_message(data)
            if not is_valid:
                self._send_error(client_socket, 402, error_msg)
                return

            if session_id not in self.sessions:
                self._send_error(client_socket, 420, "Partida no encontrada")
                return

            session = self.sessions[session_id]
            ships_data = data.get('ships', [])
            
            success, messages = session.place_ships(player_id, ships_data)
            
            if not success:
                self._send_error(client_socket, 430, "Error colocando barcos")
                return
            
            self._send_messages(session, messages)
            
        except Exception as e:
            self.logger.error(f"Error en place_ships: {e}")
            self._send_error(client_socket, 500, "Error interno")

    def _handle_attack(self, client_socket: socket.socket, player_id: Optional[str],
                      session_id: Optional[str], data: dict):
        """
        Maneja un ataque de un jugador.
        
        Valida el mensaje, ejecuta el ataque en la sesión de juego,
        y envía los mensajes generados (resultado, turno, fin de juego, etc).
        
        Args:
            client_socket: Socket del cliente.
            player_id: ID del jugador que ataca (puede ser None si no identificado).
            session_id: ID de la sesión (puede ser None si no identificado).
            data: Diccionario con coordenadas del ataque (gameId, playerId, coordinate).
        """
        if not player_id or not session_id:
            self._send_error(client_socket, 410, "Jugador o partida no identificados")
            return

        try:
            is_valid, error_msg = self.protocol.validate_attack_message(data)
            if not is_valid:
                self._send_error(client_socket, 402, error_msg)
                return

            if session_id not in self.sessions:
                self._send_error(client_socket, 420, "Partida no encontrada")
                return

            session = self.sessions[session_id]
            coordinate = data.get('coordinate')
            if not coordinate: return
            
            success, messages = session.execute_attack(player_id, coordinate)
            
            if not success:
                self._send_error(client_socket, 440, "Ataque inválido")
                return
            
            self._send_messages(session, messages)
            
        except Exception as e:
            self.logger.error(f"Error en attack: {e}")
            self._send_error(client_socket, 500, "Error interno")

    def _handle_surrender(self, client_socket: socket.socket, player_id: Optional[str],
                         session_id: Optional[str], data: dict):
        """
        Maneja la rendición de un jugador.
        
        Procesa la rendición a través de la sesión de juego,
        que finaliza el juego inmediatamente con el otro como ganador.
        
        Args:
            client_socket: Socket del cliente.
            player_id: ID del jugador que se rinde (puede ser None si no identificado).
            session_id: ID de la sesión (puede ser None si no identificado).
            data: Diccionario con datos de la rendición (gameId, playerId).
        """
        if not player_id or not session_id:
            self._send_error(client_socket, 410, "Jugador o partida no identificados")
            return

        try:
            if session_id not in self.sessions:
                self._send_error(client_socket, 420, "Partida no encontrada")
                return

            session = self.sessions[session_id]
            
            success, messages = session.handle_surrender(player_id)
            
            if not success:
                self._send_error(client_socket, 500, "Error en rendición")
                return
            
            self._send_messages(session, messages)
            
        except Exception as e:
            self.logger.error(f"Error en surrender: {e}")
            self._send_error(client_socket, 500, "Error interno")

    def _handle_generate_random_placement(self, client_socket: socket.socket, data: dict):
        """
        Maneja la solicitud de generación aleatoria de disposición de barcos.
        
        Genera una disposición válida sin solapamientos y la envía al cliente.
        
        Args:
            client_socket: Socket del cliente.
            data: Diccionario con datos del mensaje (boardSize opcional).
        """
        try:
            board_size = data.get('boardSize', 10)
            
            if not isinstance(board_size, int) or board_size < 5:
                self._send_error(client_socket, 403, "boardSize inválido")
                return
            
            placement = generate_valid_ship_placement(board_size)
            
            response = {
                'type': 'random_placement',
                'code': 250,
                'ships': placement['ships']
            }
            self._send_message(client_socket, response)
            self.logger.info(f"Disposición aleatoria generada (5 barcos, {len(placement['ships'])} validados)")
            
        except Exception as e:
            self.logger.error(f"Error generando disposición aleatoria: {e}")
            self._send_error(client_socket, 500, "Error al generar disposición")

    def _send_messages(self, session: GameSession, messages: List[OutgoingMessage]):
        """
        Envía una lista de OutgoingMessage a sus respectivos jugadores.
        
        Cada OutgoingMessage especifica el player_id destino, se obtiene
        su socket de la sesión, y se envía el payload al cliente.
        
        Args:
            session: La sesión de juego que contiene los sockets.
            messages: Lista de OutgoingMessage a enviar.
        """
        for msg in messages:
            if msg.player_id in session.players:
                sock = session.players[msg.player_id]['socket']
                self._send_message(sock, msg.payload)

    def _send_message(self, client_socket: socket.socket, message: dict):
        """
        Envía un mensaje JSON a través de WebSocket.
        
        Serializa el diccionario a JSON, lo encapsula en un frame WebSocket,
        y lo envía al cliente.
        
        Args:
            client_socket: Socket del cliente destino.
            message: Diccionario con el mensaje a enviar.
        """
        try:
            json_str = json.dumps(message)
            frame = self._create_websocket_frame(json_str)
            client_socket.send(frame)
        except Exception as e:
            self.logger.error(f"Error enviando mensaje: {e}")

    def _send_error(self, client_socket: socket.socket, code: int, message: str):
        """
        Envía un mensaje de error al cliente.
        
        Formatea el error según el protocolo y lo envía.
        
        Args:
            client_socket: Socket del cliente destino.
            code: Código de error del protocolo.
            message: Mensaje descriptivo del error.
        """
        error_msg = self.protocol.create_error(code, message)
        self._send_message(client_socket, error_msg)

    def _cleanup_client(self, client_socket: socket.socket, player_id: Optional[str], 
                       session_id: Optional[str]):
        """
        Limpia cuando un cliente se desconecta.
        
        Cierra el socket, marca el jugador como desconectado en la sesión,
        genera mensajes de notificación al oponente, y limpia los mapeos
        de socket a jugador/sesión.
        
        Args:
            client_socket: Socket del cliente que se desconectó.
            player_id: ID del jugador (si estaba identificado).
            session_id: ID de la sesión (si estaba en una).
        """
        try:
            client_socket.close()
        except:
            pass

        if player_id and session_id and session_id in self.sessions:
            session = self.sessions[session_id]
            
            messages = session.mark_player_disconnected(player_id)
            self._send_messages(session, messages)
            
            self.logger.warning(f"[SESSION {session_id[:8]}] Jugador {player_id[:8]} desconectado")

        if client_socket in self.socket_to_player:
            del self.socket_to_player[client_socket]
        if client_socket in self.socket_to_session:
            del self.socket_to_session[client_socket]
        if player_id and player_id in self.player_to_session:
            del self.player_to_session[player_id]

    def _websocket_handshake(self, client_socket: socket.socket, request: str) -> bool:
        """
        Realiza el handshake WebSocket con un cliente.
        
        Sigue el protocolo RFC 6455 para establecer una conexión WebSocket:
        1. Parsea el header HTTP con la clave Sec-WebSocket-Key
        2. Calcula la aceptación usando SHA1 + Base64
        3. Envía la respuesta HTTP 101 Switching Protocols
        
        Args:
            client_socket: Socket del cliente.
            request: La solicitud HTTP inicial del cliente.
        
        Returns:
            True si el handshake fue exitoso, False en caso contrario.
        """
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
            self.logger.error(f"Error en handshake: {e}")
            return False

    def _receive_websocket_frame(self, client_socket: socket.socket) -> Optional[str]:
        """
        Recibe y parsea un WebSocket frame según RFC 6455.
        
        Detecta opcodes (texto, binario, cierre, ping),
        maneja frames enmascarados, extrae y desenmascara el payload.
        Automáticamente responde a pings con pongs.
        
        Args:
            client_socket: Socket del cliente.
        
        Returns:
            String con el contenido del frame, o None si el cliente cerró/error.
        """
        try:
            data = client_socket.recv(1024)
            if not data:
                return None

            if len(data) < 2:
                return None

            first_byte = data[0]
            second_byte = data[1]
            opcode = first_byte & 0x0F
            masked = (second_byte & 0x80) != 0
            payload_length = second_byte & 0x7F
            index = 2

            if not masked:
                try:
                    self.logger.warning("Cliente envió frame no enmascarado, cerrando conexión")
                    client_socket.close()
                except:
                    self.logger.warning("Cliente envió frame no enmascarado, cerrando conexión (error al cerrar)")
                return None
                    

            if payload_length == 126:
                if len(data) < index + 2:
                    self.logger.warning("Frame con payload length 126 pero datos insuficientes")
                    return None
                payload_length = int.from_bytes(data[index:index+2], 'big')
                index += 2
            elif payload_length == 127:
                if len(data) < index + 8:
                    self.logger.warning("Frame con payload length 127 pero datos insuficientes")
                    return None
                payload_length = int.from_bytes(data[index:index+8], 'big')
                index += 8

            if opcode == 8:  # Close
                return None

            if opcode == 9:  # Ping
                pong = bytearray([0x8A, 0x00])
                client_socket.send(pong)
                return None  # evita recursión

            # Masking key
            if len(data) < index + 4:
                self.logger.warning("Frame con máscara pero datos insuficientes para la clave de enmascarado")
                return None
            masking_key = data[index:index + 4]
            index += 4

            # Payload
            if len(data) < index + payload_length:
                self.logger.warning("Frame con payload pero datos insuficientes para el payload completo")
                return None

            payload = data[index:index + payload_length]

            # Unmask
            payload = bytes(
                payload[i] ^ masking_key[i % 4]
                for i in range(len(payload))
            )

            if opcode == 1:
                try:
                    return payload.decode('utf-8')
                except UnicodeDecodeError as e:
                    self.logger.error(
                        f"UnicodeDecodeError al decodificar payload: {e}\n"
                        f"Payload length: {len(payload)} bytes\n"
                        f"Primeros 100 bytes (hex): {payload[:100].hex()}\n"
                        f"Masking key: {masking_key.hex()}\n"
                        f"Opcode: {opcode}"
                    )
                    try:
                        return payload.decode('utf-8', errors='replace')
                    except Exception as inner_e:
                        self.logger.error(f"Falló recuperación con errors='replace': {inner_e}")
                        return None

            # Si llega binario
            self.logger.warning(f"Recibido frame con opcode {opcode} no soportado")
            return None

        except Exception:
            return None

    def _create_websocket_frame(self, data: str) -> bytes:
        """
        Crea un WebSocket frame de texto según RFC 6455.
        
        Encapsula el string en un frame WebSocket no enmascarado
        con opcode de texto (0x81) y añade información de longitud.
        
        Args:
            data: String con el contenido del frame.
        
        Returns:
            Bytes con el frame completo listo para enviar.
        """
        data_encoded = data.encode('utf-8')
        frame = bytearray()
        frame.append(0x81)

        if len(data_encoded) <= 125:
            frame.append(len(data_encoded))
        else:
            frame.append(126)
            frame.extend(len(data_encoded).to_bytes(2, 'big'))

        frame.extend(data_encoded)
        return bytes(frame)

    def start_server(self):
        """
        Inicia el servidor (para usar en un thread separado).
        
        Wrapper que llama a start() para permitir ejecutar el servidor
        en un thread daemon.
        """
        self.start()
