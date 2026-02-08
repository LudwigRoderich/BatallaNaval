"""
Gestor de sesiones y estado del juego.
Proporciona funcionalidades centralizadas para gestionar múltiples partidas.
"""

from typing import Dict, Optional, List
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class GameManager:
    """Gestor centralizado de partidas activas."""

    def __init__(self, game_timeout_minutes: int = 30):
        self.games: Dict[str, any] = {}  # {game_id: GameSession}
        self.players: Dict[str, str] = {}  # {player_id: game_id}
        self.game_timeout = timedelta(minutes=game_timeout_minutes)
        self.next_game_id = 0

    def create_game(self, game_class) -> str:
        """Crea una nueva partida."""
        game_id = f"game_{self.next_game_id}"
        self.next_game_id += 1
        
        game = game_class(board_size=10)
        self.games[game_id] = {
            'game': game,
            'players': {},
            'created_at': datetime.now(),
            'last_activity': datetime.now()
        }
        
        logger.info(f"Partida creada: {game_id}")
        return game_id

    def get_game(self, game_id: str) -> Optional[any]:
        """Obtiene una partida."""
        return self.games.get(game_id, {}).get('game')

    def add_player_to_game(self, game_id: str, player_id: str, player_name: str) -> bool:
        """Añade un jugador a una partida."""
        if game_id not in self.games:
            return False

        session = self.games[game_id]
        if len(session['players']) >= 2:
            return False

        session['players'][player_id] = {
            'name': player_name,
            'ready': False,
            'connected': True
        }
        self.players[player_id] = game_id
        session['last_activity'] = datetime.now()
        
        logger.info(f"Jugador {player_id} añadido a partida {game_id}")
        return True

    def get_players_in_game(self, game_id: str) -> Dict[str, any]:
        """Obtiene los jugadores de una partida."""
        if game_id not in self.games:
            return {}
        return self.games[game_id]['players'].copy()

    def get_game_for_player(self, player_id: str) -> Optional[str]:
        """Obtiene el ID de la partida de un jugador."""
        return self.players.get(player_id)

    def mark_player_ready(self, game_id: str, player_id: str) -> bool:
        """Marca un jugador como listo."""
        if game_id not in self.games or player_id not in self.games[game_id]['players']:
            return False

        self.games[game_id]['players'][player_id]['ready'] = True
        self.games[game_id]['last_activity'] = datetime.now()
        return True

    def are_all_players_ready(self, game_id: str) -> bool:
        """Verifica si todos los jugadores están listos."""
        if game_id not in self.games:
            return False

        players = self.games[game_id]['players']
        if len(players) < 2:
            return False

        return all(p['ready'] for p in players.values())

    def mark_player_disconnected(self, player_id: str) -> Optional[str]:
        """Marca un jugador como desconectado."""
        game_id = self.players.get(player_id)
        if not game_id or game_id not in self.games:
            return None

        if player_id in self.games[game_id]['players']:
            self.games[game_id]['players'][player_id]['connected'] = False
            self.games[game_id]['last_activity'] = datetime.now()

        return game_id

    def mark_player_reconnected(self, player_id: str) -> bool:
        """Marca un jugador como reconectado."""
        game_id = self.players.get(player_id)
        if not game_id or game_id not in self.games:
            return False

        if player_id in self.games[game_id]['players']:
            self.games[game_id]['players'][player_id]['connected'] = True
            self.games[game_id]['last_activity'] = datetime.now()
            return True

        return False

    def remove_game(self, game_id: str) -> bool:
        """Elimina una partida y sus jugadores."""
        if game_id not in self.games:
            return False

        players = list(self.games[game_id]['players'].keys())
        for player_id in players:
            if player_id in self.players:
                del self.players[player_id]

        del self.games[game_id]
        logger.info(f"Partida eliminada: {game_id}")
        return True

    def cleanup_inactive_games(self) -> List[str]:
        """Elimina las partidas inactivas."""
        now = datetime.now()
        removed_games = []

        for game_id in list(self.games.keys()):
            session = self.games[game_id]
            if now - session['last_activity'] > self.game_timeout:
                self.remove_game(game_id)
                removed_games.append(game_id)
                logger.warning(f"Partida inactiva eliminada: {game_id}")

        return removed_games

    def get_game_statistics(self, game_id: str) -> Optional[Dict]:
        """Obtiene estadísticas de una partida."""
        if game_id not in self.games:
            return None

        session = self.games[game_id]
        game = session['game']

        return {
            'game_id': game_id,
            'state': game.state.name,
            'players': len(session['players']),
            'move_count': game.move_count,
            'current_turn': game.current_turn,
            'created_at': session['created_at'].isoformat(),
            'last_activity': session['last_activity'].isoformat(),
        }

    def get_all_games_statistics(self) -> List[Dict]:
        """Obtiene estadísticas de todas las partidas activas."""
        stats = []
        for game_id in self.games.keys():
            game_stats = self.get_game_statistics(game_id)
            if game_stats:
                stats.append(game_stats)
        return stats
