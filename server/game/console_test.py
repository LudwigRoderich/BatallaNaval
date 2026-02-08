import random
import numpy as np
from .ship import Ship, Coordinate
from .board import Board
from .player import Player
from .game import Game
from .results import GameOverResult, AttackResult
from .enums import CellState, AttackOutcome, GameState, ShipType, ShipOrientation
from .errors import (
    BattleshipGameError,
    InvalidCoordinateError,
    ShipPlacementError,
    ShipOverlapError,
    InvalidShipError,
    GameStateError,
    PlayerError,
    InvalidAttackError
)
def generar_barco_aleatorio(ship_id: str, ship_type: ShipType, board_size: int, orientation: ShipOrientation) -> Ship:
    import random

    length = ship_type.length
    positions = set()

    if orientation == ShipOrientation.HORIZONTAL:
        x_start = random.randint(0, board_size - length)
        y = random.randint(0, board_size - 1)
        for i in range(length):
            positions.add(Coordinate(x_start + i, y))
    else:  # VERTICAL
        x = random.randint(0, board_size - 1)
        y_start = random.randint(0, board_size - length)
        for i in range(length):
            positions.add(Coordinate(x, y_start + i))

    return Ship(ship_id=ship_id, ship_type=ship_type, positions=positions, orientation=orientation)

def imprimir_tablero(board: Board) -> None:
    size = board._size
    print("  " + " ".join(str(i) for i in range(size)))
    for y in range(size):
        row = []
        for x in range(size):
            coord = Coordinate(x, y)
            cell = board._cells.get(coord, CellState.EMPTY)
            if cell == CellState.EMPTY:
                row.append(".")
            elif cell == CellState.SHIP:
                row.append("S")
            elif cell == CellState.HIT:
                row.append("X")
            elif cell == CellState.MISS:
                row.append("O")
        print(f"{y} " + " ".join(row))

def realizar_ataque(game: Game, attacker_id: str, coord: Coordinate | None = None) -> AttackResult:
    size = game._board_size
    if not coord:
        x = random.randint(0, size - 1)
        y = random.randint(0, size - 1)
        coord = Coordinate(x, y)
    return game.attack(attacker_id, coord)

player1 = Player("Alice")
player2 = Player("Bob")
player3 = Player("Justin")

game = Game()
game.add_player(player_id=player1.player_id)
game.add_player(player_id=player2.player_id)
game.start()
board_size = game._board_size


for player in [player1, player2]:
    for i, ship_type in enumerate(ShipType):
        orientation = random.choice(list(ShipOrientation))
        ship = generar_barco_aleatorio(
            ship_id=f"{player.player_id}_ship_{i+1}",
            ship_type=ship_type,
            board_size=10,
            orientation=orientation
        )
        game.place_ship(player.player_id, ship)

    print(f"\nTablero de {player.player_id}:")
    #imprimir_tablero(player._board)
    imprimir_tablero(game._players[player.player_id]._board)

game.finish_ship_placement()

contador_ataques = 0
ataques_player1 = np.zeros((board_size, board_size), dtype=bool)
ataques_player2 = np.zeros((board_size, board_size), dtype=bool)

while not game.is_finished():
    attacker = player1 if game._current_turn and player1.player_id == game._current_turn else player2
    defender = player2 if attacker == player1 else player1
    
    coords_disponibles = np.argwhere(ataques_player1==False if attacker == player1 else ataques_player2==False)
    if len(coords_disponibles) == 0:
        print(f"No quedan coordenadas disponibles para {attacker.player_id}. Terminando la prueba.")
        break
    x, y = random.choice(coords_disponibles)
    coord = Coordinate(x, y)
    result = realizar_ataque(game, attacker.player_id, coord)
    if attacker == player1:
        ataques_player1[x, y] = True
    else:
        ataques_player2[x, y] = True

    print(f"\nTurno de {attacker.player_id}. Número de ataques realizados: {contador_ataques}")
    print(f"{attacker.player_id} atacó: {result.outcome.name} en {result.attacked_coordinate}\n")
    print(f"\nTablero de {defender.player_id} después del ataque:")
    imprimir_tablero(game._players[defender.player_id]._board)
    contador_ataques +=1
    if contador_ataques >= 200:
        print("Demasiados ataques, terminando la prueba.")
        break
print(f"\nJuego terminado en {contador_ataques} ataques")
print(game.get_game_result())


# game.place_ship(player_id=player1.player_id, ship=generar_barco_aleatorio(
#     ship_id="extra_ship",
#     ship_type=random.choice(list(ShipType)),
#     board_size=10, 
#     orientation=random.choice(list(ShipOrientation))
# ))