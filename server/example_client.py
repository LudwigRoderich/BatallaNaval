"""
Ejemplo de uso del servidor de Batalla Naval.
Demuestra cómo los clientes se conectan y juegan.
"""

import asyncio
import websockets
import json


async def test_game_flow():
    """Simula un flujo de juego completo."""
    
    # Conectar dos clientes
    uri = "ws://localhost:8080"
    
    print("=== INICIANDO TEST DE FLUJO DE JUEGO ===\n")
    
    # Cliente 1
    async with websockets.connect(uri) as ws1:
        print("[CLIENTE 1] Conectado")
        
        # Enviar solicitud de unión
        join_msg = {
            "type": "join_game",
            "playerId": "player_001",
            "playerName": "Jugador 1"
        }
        await ws1.send(json.dumps(join_msg))
        
        response = await ws1.recv()
        msg = json.loads(response)
        print(f"[CLIENTE 1] Respuesta: {msg['message']}")
        game_id = msg.get('gameId')
        
        # Cliente 2 (en otro contexto, pero simulado aquí)
        async with websockets.connect(uri) as ws2:
            print("[CLIENTE 2] Conectado")
            
            # Enviar solicitud de unión
            join_msg2 = {
                "type": "join_game",
                "playerId": "player_002",
                "playerName": "Jugador 2"
            }
            await ws2.send(json.dumps(join_msg2))
            
            response = await ws2.recv()
            msg2 = json.loads(response)
            print(f"[CLIENTE 2] Respuesta: {msg2['message']}")
            
            # Ambos clientes reciben confirmación de que el oponente llegó
            if ws1.open:
                response = await ws1.recv()
                msg = json.loads(response)
                print(f"[CLIENTE 1] Oponente conectado: {msg['message']}")
            
            print("\n=== FASE DE COLOCACIÓN DE BARCOS ===\n")
            
            # Cliente 1 coloca barcos
            ships1 = [
                {
                    "type": "AIRCRAFT_CARRIER",
                    "start": {"x": 0, "y": 0},
                    "orientation": "horizontal"
                },
                {
                    "type": "BATTLESHIP",
                    "start": {"x": 0, "y": 1},
                    "orientation": "horizontal"
                },
                {
                    "type": "CRUISER",
                    "start": {"x": 0, "y": 2},
                    "orientation": "horizontal"
                },
                {
                    "type": "DESTROYER",
                    "start": {"x": 0, "y": 3},
                    "orientation": "horizontal"
                },
                {
                    "type": "SUBMARINE",
                    "start": {"x": 0, "y": 4},
                    "orientation": "horizontal"
                },
            ]
            
            place_ships_msg = {
                "type": "place_ships",
                "gameId": game_id,
                "playerId": "player_001",
                "ships": ships1
            }
            
            await ws1.send(json.dumps(place_ships_msg))
            response = await ws1.recv()
            msg = json.loads(response)
            print(f"[CLIENTE 1] Barcos colocados: {msg['message']}")
            
            # Cliente 2 coloca barcos
            ships2 = [
                {
                    "type": "AIRCRAFT_CARRIER",
                    "start": {"x": 5, "y": 5},
                    "orientation": "vertical"
                },
                {
                    "type": "BATTLESHIP",
                    "start": {"x": 6, "y": 5},
                    "orientation": "vertical"
                },
                {
                    "type": "CRUISER",
                    "start": {"x": 7, "y": 5},
                    "orientation": "vertical"
                },
                {
                    "type": "DESTROYER",
                    "start": {"x": 8, "y": 5},
                    "orientation": "vertical"
                },
                {
                    "type": "SUBMARINE",
                    "start": {"x": 9, "y": 5},
                    "orientation": "vertical"
                },
            ]
            
            place_ships_msg2 = {
                "type": "place_ships",
                "gameId": game_id,
                "playerId": "player_002",
                "ships": ships2
            }
            
            await ws2.send(json.dumps(place_ships_msg2))
            response = await ws2.recv()
            msg2 = json.loads(response)
            print(f"[CLIENTE 2] Barcos colocados: {msg2['message']}")
            
            # Ambos reciben confirmación de juego iniciado
            if ws1.open:
                response = await ws1.recv()
                msg = json.loads(response)
                print(f"[CLIENTE 1] {msg['message']}")
            
            if ws2.open:
                response = await ws2.recv()
                msg2 = json.loads(response)
                print(f"[CLIENTE 2] {msg2['message']}")
            
            print("\n=== FASE DE ATAQUE ===\n")
            
            # Cliente 1 ataca
            attack_msg = {
                "type": "attack",
                "gameId": game_id,
                "playerId": "player_001",
                "coordinate": {"x": 5, "y": 5}
            }
            
            await ws1.send(json.dumps(attack_msg))
            
            # Recibir resultado
            response = await ws1.recv()
            msg = json.loads(response)
            print(f"[CLIENTE 1] Ataque a (5,5): {msg.get('outcome', 'MISS')}")
            
            # Cliente 2 ve el ataque
            if ws2.open:
                response = await ws2.recv()
                msg2 = json.loads(response)
                print(f"[CLIENTE 2] Tu oponente atacó (5,5): {msg2.get('outcome', 'MISS')}")
            
            print("\n=== TEST COMPLETADO ===")


if __name__ == '__main__':
    asyncio.run(test_game_flow())
