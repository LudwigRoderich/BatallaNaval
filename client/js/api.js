/**
 * Módulo API para comunicación con el servidor
 * WebSocket para Batalla Naval
 */

console.log('[API] Módulo API cargado');
const API = {
    get wsURL() {
        // Usar el hostname actual del navegador
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.hostname;
        const port = 8080; // Puerto fijo del WebSocket
        
        return `${protocol}//${host}:${port}`;
    },
    ws: null,
    messageHandlers: {},
    reconnectAttempts: 0,
    maxReconnectAttempts: 5,
    reconnectDelay: 3000,
    
    /**
     * Inicializa la conexión WebSocket
     */
    init() {
        console.log('[API] Inicializando conexión WebSocket...');
        return new Promise((resolve, reject) => {
            try {
                this.ws = new WebSocket(this.wsURL);
                
                this.ws.addEventListener('open', () => {
                    console.log('[API] Conectado al servidor WebSocket');
                    this.reconnectAttempts = 0;
                    resolve();
                });
                
                this.ws.addEventListener('message', (event) => {
                    this._handleMessage(event.data);
                });
                
                this.ws.addEventListener('close', () => {
                    console.log('[API] Desconectado del servidor');
                    this._attemptReconnect();
                });
                
                this.ws.addEventListener('error', (error) => {
                    console.error('[API] Error WebSocket:', error);
                    reject(error);
                });
            } catch (error) {
                console.error('[API] Error inicializando WebSocket:', error);
                reject(error);
            }
        });
    },
    
    /**
     * Intenta reconectar al servidor
     */
    _attemptReconnect() {
        // Disparar evento de desconexión
        const event = new CustomEvent('websocket-disconnected');
        document.dispatchEvent(event);
        
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            console.log(`[API] Intentando reconectar (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);
            
            setTimeout(() => {
                this.init().then(() => {
                    const event = new CustomEvent('websocket-reconnected');
                    document.dispatchEvent(event);
                }).catch(() => {
                    this._attemptReconnect();
                });
            }, this.reconnectDelay);
        } else {
            console.error('[API] Máximo de intentos de reconexión alcanzado');
        }
    },
    
    /**
     * Envía un mensaje al servidor
     */
    send(message) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(message));
        } else {
            console.error('[API] WebSocket no está conectado');
        }
    },
    
    /**
     * Maneja mensajes recibidos del servidor
     */
    _handleMessage(data) {
        try {
            const message = JSON.parse(data);
            console.log('[API] Mensaje recibido:', message);
            
            // Ejecutar handlers registrados
            if (this.messageHandlers[message.type]) {
                this.messageHandlers[message.type](message);
            }
        } catch (error) {
            console.error('[API] Error procesando mensaje:', error);
        }
    },
    
    /**
     * Registra un handler para un tipo de mensaje
     */
    on(messageType, handler) {
        this.messageHandlers[messageType] = handler;
    },
    
    /**
     * Busca una partida para el jugador
     */
    async findMatch(playerName) {
        console.log(`[API] Buscando partida para: ${playerName}`);
        
        return new Promise((resolve, reject) => {
            const timeout = setTimeout(() => {
                reject(new Error('Timeout esperando respuesta del servidor'));
            }, 30000);
            
            // Handler temporal para esta solicitud
            const handler = (message) => {
                clearTimeout(timeout);
                
                if (message.code === 210 || message.code === 211) {
                    // Guardar datos de la partida
                    GameState.matchId = message.gameId;
                    GameState.playerId = message.playerId;
                    
                    resolve({
                        success: true,
                        matchId: message.gameId,
                        message: message.message
                    });
                } else if (message.type === 'error') {
                    reject(new Error(message.message));
                }
            };
            
            this.on('game_state', handler);
            
            // Enviar solicitud de unión
            this.send({
                type: 'join_game',
                playerId: 'player_' + Date.now(),
                playerName: playerName
            });
        });
    },
    
    /**
     * Envía la disposición de barcos al servidor
     */
    async submitShipPlacement(matchId, ships) {
        console.log('[API] Enviando disposición de barcos:', ships);
        
        return new Promise((resolve, reject) => {
            const timeout = setTimeout(() => {
                reject(new Error('Timeout esperando confirmación de barcos'));
            }, 10000);
            
            const handler = (message) => {
                clearTimeout(timeout);
                
                if (message.code === 200 || message.code === 212) {
                    resolve({
                        success: true,
                        message: message.message
                    });
                } else if (message.type === 'error') {
                    reject(new Error(message.message));
                }
            };
            
            this.on('game_state', handler);
            
            // Convertir ships al formato esperado
            const shipsData = ships.map(ship => ({
                type: ship.type,
                start: ship.positions[0],
                orientation: ship.orientation
            }));
            
            this.send({
                type: 'place_ships',
                gameId: GameState.matchId,
                playerId: GameState.playerId,
                ships: shipsData
            });
        });
    },
    
    /**
     * Envía un ataque al servidor
     */
    async sendAttack(matchId, coordinate) {
        console.log(`[API] Enviando ataque a: ${coordinate}`);
        
        return new Promise((resolve, reject) => {
            const timeout = setTimeout(() => {
                reject(new Error('Timeout esperando resultado del ataque'));
            }, 10000);
            
            const handler = (message) => {
                clearTimeout(timeout);
                
                if (message.type === 'attack_result' || message.type === 'opponent_move') {
                    resolve({
                        success: true,
                        outcome: message.outcome.toUpperCase(),
                        coordinate: message.coordinate,
                        gameFinished: false
                    });
                } else if (message.type === 'game_over') {
                    resolve({
                        success: true,
                        outcome: 'GAME_OVER',
                        coordinate: message.coordinate,
                        gameFinished: true,
                        winner: message.winner
                    });
                } else if (message.type === 'error') {
                    reject(new Error(message.message));
                }
            };
            
            // Usar handler único para attack_result
            if (!this.messageHandlers['attack_result']) {
                this.on('attack_result', handler);
            }
            
            this.send({
                type: 'attack',
                gameId: GameState.matchId,
                playerId: GameState.playerId,
                coordinate: coordinate
            });
        });
    },
    
    /**
     * Obtiene el estado actual del juego
     */
    async getGameState(matchId) {
        console.log('[API] Obteniendo estado del juego');
        
        return new Promise((resolve) => {
            // El estado se actualiza automáticamente a través de WebSocket
            resolve({
                success: true,
                currentTurn: GameState.currentTurn,
                moveCount: 0,
                yourShipsRemaining: 5,
                enemyShipsRemaining: 5
            });
        });
    },
    
    /**
     * Genera posicionamiento aleatorio de barcos
     */
    async generateRandomPlacement(boardSize = 10) {
        console.log('[API] Generando posicionamiento aleatorio');
        // TODO: Implementar conexión real con el servidor
        // Por ahora, generar localmente
        
        const ships = GameState.placement.ships.map(ship => {
            const orientation = Math.random() > 0.5 ? 'horizontal' : 'vertical';
            const positions = this._generateRandomPositions(ship.length, orientation, boardSize);
            
            return {
                id: ship.id,
                type: ship.type,
                positions: positions,
                orientation: orientation
            };
        });
        
        return new Promise((resolve) => {
            setTimeout(() => {
                resolve({
                    success: true,
                    ships: ships
                });
            }, 500);
        });
    },
    
    /**
     * Genera posiciones aleatorias para un barco
     * (Función auxiliar temporal)
     */
    _generateRandomPositions(length, orientation, boardSize) {
        const positions = [];
        
        let startX, startY;
        if (orientation === 'horizontal') {
            startX = Math.floor(Math.random() * (boardSize - length));
            startY = Math.floor(Math.random() * boardSize);
            
            for (let i = 0; i < length; i++) {
                positions.push({ x: startX + i, y: startY });
            }
        } else {
            startX = Math.floor(Math.random() * boardSize);
            startY = Math.floor(Math.random() * (boardSize - length));
            
            for (let i = 0; i < length; i++) {
                positions.push({ x: startX, y: startY + i });
            }
        }
        
        return positions;
    },
    
    /**
     * Verifica si las posiciones de un barco son válidas
     */
    isValidPlacement(positions, existingShips, boardSize) {
        // Verificar límites del tablero
        for (const pos of positions) {
            if (pos.x < 0 || pos.x >= boardSize || pos.y < 0 || pos.y >= boardSize) {
                return false;
            }
        }
        
        // Verificar colisiones con barcos existentes
        for (const existingShip of existingShips) {
            for (const existingPos of existingShip.positions) {
                for (const newPos of positions) {
                    if (existingPos.x === newPos.x && existingPos.y === newPos.y) {
                        return false;
                    }
                }
            }
        }
        
        return true;
    },
    
    /**
     * Convierte coordenadas de notación (A1, B5) a índices numéricos
     */
    parseCoordinate(coord) {
        // Formato esperado: "A1", "J10", etc.
        const match = coord.match(/^([A-J])(\d+)$/i);
        if (!match) return null;
        
        const x = match[1].toUpperCase().charCodeAt(0) - 65; // A=0, B=1, etc.
        const y = parseInt(match[2]) - 1; // 1=0, 2=1, etc.
        
        return { x, y };
    },
    
    /**
     * Convierte índices numéricos a notación de coordenadas
     */
    formatCoordinate(x, y) {
        const letter = String.fromCharCode(65 + x); // 0=A, 1=B, etc.
        const number = y + 1; // 0=1, 1=2, etc.
        return `${letter}${number}`;
    }
};

// Exportar para uso en otros módulos
if (typeof module !== 'undefined' && module.exports) {
    module.exports = API;
}
