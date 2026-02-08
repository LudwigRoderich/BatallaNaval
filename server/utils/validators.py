"""
Validadores para entrada de datos.
"""

from typing import Dict, Tuple, List
import re


class Validators:
    """Conjunto de funciones para validar entrada."""

    @staticmethod
    def validate_player_name(name: str) -> Tuple[bool, str]:
        """Valida el nombre de un jugador."""
        if not name or not isinstance(name, str):
            return False, "El nombre debe ser una cadena de texto"
        
        name = name.strip()
        
        if len(name) < 2:
            return False, "El nombre debe tener al menos 2 caracteres"
        
        if len(name) > 30:
            return False, "El nombre no puede exceder 30 caracteres"
        
        if not re.match(r'^[a-zA-Z0-9_\s\-áéíóúñÁÉÍÓÚÑ]+$', name):
            return False, "El nombre contiene caracteres no válidos"
        
        return True, ""

    @staticmethod
    def validate_coordinate(coord: Dict) -> Tuple[bool, str]:
        """Valida una coordenada."""
        if not isinstance(coord, dict):
            return False, "La coordenada debe ser un diccionario"
        
        if 'x' not in coord or 'y' not in coord:
            return False, "La coordenada debe tener campos 'x' y 'y'"
        
        x, y = coord.get('x'), coord.get('y')
        
        if not isinstance(x, int) or not isinstance(y, int):
            return False, "Las coordenadas deben ser números enteros"
        
        if not (0 <= x < 10) or not (0 <= y < 10):
            return False, "Las coordenadas están fuera del rango válido (0-9)"
        
        return True, ""

    @staticmethod
    def validate_ship_placement(ship_data: Dict) -> Tuple[bool, str]:
        """Valida la colocación de un barco."""
        if not isinstance(ship_data, dict):
            return False, "El datos del barco debe ser un diccionario"
        
        required_fields = ['type', 'start', 'orientation']
        for field in required_fields:
            if field not in ship_data:
                return False, f"Falta el campo obligatorio: {field}"
        
        # Validar tipo de barco
        valid_types = ['AIRCRAFT_CARRIER', 'BATTLESHIP', 'CRUISER', 'DESTROYER', 'SUBMARINE']
        if ship_data['type'] not in valid_types:
            return False, f"Tipo de barco inválido: {ship_data['type']}"
        
        # Validar coordenada de inicio
        is_valid, msg = Validators.validate_coordinate(ship_data['start'])
        if not is_valid:
            return False, f"Coordenada de inicio inválida: {msg}"
        
        # Validar orientación
        if ship_data['orientation'] not in ['horizontal', 'vertical']:
            return False, "La orientación debe ser 'horizontal' o 'vertical'"
        
        return True, ""

    @staticmethod
    def validate_ships_list(ships: List) -> Tuple[bool, str]:
        """Valida una lista de barcos."""
        if not isinstance(ships, list):
            return False, "Los barcos deben ser una lista"
        
        if len(ships) != 5:
            return False, f"Deben haber exactamente 5 barcos, se recibieron {len(ships)}"
        
        for i, ship in enumerate(ships):
            is_valid, msg = Validators.validate_ship_placement(ship)
            if not is_valid:
                return False, f"Barco {i+1}: {msg}"
        
        return True, ""
