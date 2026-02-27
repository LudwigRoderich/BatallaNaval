/**
 * API.js - Refactorizado para Arquitectura Reactiva
 * 
 * Cambios principales:
 * 1. NO validar localmente (todo lo valida el servidor)
 * 2. Enviar requests y esperar respuestas
 * 3. Los handlers de respuesta son MÍ NIMOS (solo renderizar)
 */

console.log('[API] Módulo API cargado (REACTIVO)');

const API = {
    get wsURL() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.hostname;
        const port = 8080;
        return `${protocol}//${host}:${port}`;
    },
    
    get httpURL() {
        return `http://${window.location.hostname}:8000`;
    },
    
    ws: null,
    messageHandlers: {},
    reconnectAttempts: 0,
    maxReconnectAttempts: 5,
    reconnectDelay: 3000,
    
    /**
     * Inicialización: Health check + WS + Ping
     * El cliente se conecta y espera instrucciones del servidor
     */
    async init() {
        console.log('[API] Inicializando cliente reactivo...');
        
        try {
            // Verificar salud del servidor HTTP
            const healthResponse = await fetch(`${this.httpURL}/api/health`);
            if (!healthResponse.ok) throw new Error('Servidor HTTP no responde');
            console.log('[API] ✓ Servidor HTTP activo');
            
            // Conectar WebSocket
            await this._connectWebSocket();
            console.log('[API] ✓ WebSocket conectado');
            
            // Hacer ping
            await this._sendPing();
            console.log('[API] ✓ Ping exitoso');
            
            // Verificar sesión
            this._checkSavedSession();
            
            return true;
        } catch (error) {
            console.error('[API] Error en inicialización:', error);
            throw error;
        }
    },
    
    _connectWebSocket() {
        return new Promise((resolve, reject) => {
            try {
                this.ws = new WebSocket(this.wsURL);
                
                this.ws.addEventListener('open', () => {
                    console.log('[API] ✓ Conexión WebSocket establecida');
                    this.reconnectAttempts = 0;
                    resolve();
                });
                
                this.ws.addEventListener('message', (event) => {
                    this._handleMessage(event.data);
                });
                
                this.ws.addEventListener('close', () => {
                    console.log('[API] WebSocket cerrado');
                    this._attemptReconnect();
                });
                
                this.ws.addEventListener('error', (error) => {
                    console.error('[API] Error WebSocket:', error);
                    reject(error);
                });
                
                const timeout = setTimeout(() => {
                    reject(new Error('Timeout conectando WebSocket'));
                }, 5000);
                
                this.ws.addEventListener('open', () => clearTimeout(timeout));
                
            } catch (error) {
                reject(error);
            }
        });
    },
    
    async _sendPing() {
        return new Promise((resolve, reject) => {
            const timeout = setTimeout(() => {
                reject(new Error('Timeout en ping'));
            }, 5000);
            
            const handler = (message) => {
                if (message.type === 'pong') {
                    clearTimeout(timeout);
                    this.removeHandler('pong', handler);
                    resolve();
                }
            };
            
            this.on('pong', handler);
            this.send({type: 'ping'});
        });
    },
    
    _checkSavedSession() {
        const playerId = localStorage.getItem('playerId');
        const sessionId = localStorage.getItem('sessionId');
        
        if (playerId && sessionId) {
            console.log('[API] Sesión guardada encontrada');
            const event = new CustomEvent('session-restored', {
                detail: {playerId, sessionId}
            });
            document.dispatchEvent(event);
        }
    },
    
    _attemptReconnect() {
        const event = new CustomEvent('websocket-disconnected');
        document.dispatchEvent(event);
        
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            console.log(`[API] Intentando reconectar (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);
            
            setTimeout(() => {
                this._connectWebSocket()
                    .then(() => {
                        console.log('[API] ✓ Reconectado');
                        const event = new CustomEvent('websocket-reconnected');
                        document.dispatchEvent(event);
                    })
                    .catch(() => {
                        this._attemptReconnect();
                    });
            }, this.reconnectDelay);
        } else {
            console.error('[API] Máximo de intentos de reconexión alcanzado');
        }
    },
    
    send(message) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            console.log('[API] Enviando:', message.type);
            this.ws.send(JSON.stringify(message));
        } else {
            console.error('[API] WebSocket no está conectado');
        }
    },
    
    _handleMessage(data) {
        try {
            const message = JSON.parse(data);
            console.log('[API] Mensaje recibido:', message.type);
            
            // Ejecutar handlers registrados
            if (this.messageHandlers[message.type]) {
                const handlers = this.messageHandlers[message.type];
                if (Array.isArray(handlers)) {
                    handlers.forEach(handler => handler(message));
                } else {
                    handlers(message);
                }
            }
        } catch (error) {
            console.error('[API] Error procesando mensaje:', error);
        }
    },
    
    on(messageType, handler) {
        if (!this.messageHandlers[messageType]) {
            this.messageHandlers[messageType] = [];
        }
        if (Array.isArray(this.messageHandlers[messageType])) {
            this.messageHandlers[messageType].push(handler);
        } else {
            this.messageHandlers[messageType] = [this.messageHandlers[messageType], handler];
        }
    },
    
    removeHandler(messageType, handler) {
        if (this.messageHandlers[messageType]) {
            if (Array.isArray(this.messageHandlers[messageType])) {
                this.messageHandlers[messageType] = this.messageHandlers[messageType].filter(h => h !== handler);
            }
        }
    },
    
    // ==============================================
    // MÉTODOS DE JUEGO (cliente envía, servidor valida)
    // ==============================================
    
    /**
     * Unirse a una partida
     * El servidor responderá con game_state tipo 210/211
     */
    async joinGame(playerName) {
        console.log(`[API] Uniéndose a partida como: ${playerName}`);
        
        return new Promise((resolve, reject) => {
            const timeout = setTimeout(() => {
                reject(new Error('Timeout esperando respuesta'));
            }, 30000);
            
            const handler = (message) => {
                console.log('[API] Mensaje recibido por el handler join game: ', message)
                if (message.type === 'game_state' && 
                    (message.code === 210 || message.code === 211)) { //210: esperando oponente, 211: ambos listos
                    
                    clearTimeout(timeout);
                    this.removeHandler('game_state', handler);
                    
                    // Guardar IDs
                    if (message.playerId) {
                        localStorage.setItem('playerId', message.playerId);
                    }
                    if (message.gameId) {
                        localStorage.setItem('sessionId', message.gameId);
                    }
                    
                    resolve({
                        success: true,
                        playerId: message.playerId,
                        sessionId: message.gameId,
                        state: message.state
                    });
                } else if (message.type === 'error') {
                    clearTimeout(timeout);
                    this.removeHandler('game_state', handler);
                    reject(new Error(message.message));
                }
            };
            
            this.on('game_state', handler);
            this.send({
                type: 'join_game',
                playerName: playerName
            });
        });
    },
    
    /**
     * Reconectarse a una partida
     */
    async reconnectGame(sessionId) {
        const playerId = localStorage.getItem('playerId');
        console.log(`[API] Reconectando a partida: ${sessionId}`);
        
        return new Promise((resolve, reject) => {
            const timeout = setTimeout(() => {
                reject(new Error('Timeout en reconexión'));
            }, 5000);
            
            let resolved = false;
            
            const handler = (message) => {
                if (resolved) return;
                
                // Reconexión exitosa (código 231)
                if (message.type === 'game_state' && message.code === 231) {
                    resolved = true;
                    clearTimeout(timeout);
                    this.removeHandler('game_state', handler);
                    
                    console.log('[API] ✓ Reconexión exitosa');
                    resolve({
                        success: true,
                        gameState: message
                    });
                }
                // La sesión expiró (código 220 o game_over)
                else if (message.type === 'game_state' && message.code === 220) {
                    resolved = true;
                    clearTimeout(timeout);
                    this.removeHandler('game_state', handler);
                    
                    const event = new CustomEvent('session-expired', {
                        detail: {reason: message.reason}
                    });
                    document.dispatchEvent(event);
                    
                    reject(new Error('Sesión expirada'));
                }
                else if (message.type === 'game_over') {
                    resolved = true;
                    clearTimeout(timeout);
                    this.removeHandler('game_state', handler);
                    
                    console.log('[API] Sesión expirada (game_over recibido)');
                    const event = new CustomEvent('session-expired', {
                        detail: {reason: 'game_over'}
                    });
                    document.dispatchEvent(event);
                    
                    reject(new Error('Sesión expirada'));
                }
                // Error
                else if (message.type === 'error') {
                    resolved = true;
                    clearTimeout(timeout);
                    this.removeHandler('game_state', handler);
                    reject(new Error(message.message));
                }
            };
            
            this.on('game_state', handler);
            
            this.send({
                type: 'reconnect',
                gameId: sessionId,
                playerId: playerId
            });
        });
    },
    
    /**
     * Enviar colocación de barcos
     * El servidor valida TODO y responde con game_state
     */
    async submitShipPlacement(ships) {
        const sessionId = localStorage.getItem('sessionId');
        const playerId = localStorage.getItem('playerId');
        
        console.log('[API] Enviando disposición de barcos');
        
        return new Promise((resolve, reject) => {
            const timeout = setTimeout(() => {
                reject(new Error('Timeout esperando confirmación'));
            }, 15000);
            
            const handler = (message) => {
                if (message.type === 'game_state' && 
                    (message.code === 213 || message.code === 212)) {
                    
                    clearTimeout(timeout);
                    this.removeHandler('game_state', handler);
                    
                    resolve({
                        success: true,
                        gameState: message
                    });
                } else if (message.type === 'error') {
                    clearTimeout(timeout);
                    this.removeHandler('game_state', handler);
                    reject(new Error(message.message));
                }
            };
            
            this.on('game_state', handler);
            
            const shipsData = ships.map(ship => ({
                type: ship.type,
                positions: ship.positions,
                orientation: ship.orientation
            }));
            
            this.send({
                type: 'place_ships',
                gameId: sessionId,
                playerId: playerId,
                ships: shipsData
            });
        });
    },
    
    /**
     * Enviar ataque
     * El servidor responde con attack_result
     */
    async sendAttack(coordinate) {
        const sessionId = localStorage.getItem('sessionId');
        const playerId = localStorage.getItem('playerId');
        
        console.log(`[API] Enviando ataque a: ${JSON.stringify(coordinate)}`);
        
        return new Promise((resolve, reject) => {
            const timeout = setTimeout(() => {
                reject(new Error('Timeout esperando resultado'));
            }, 10000);
            
            let resolved = false;
            
            const handler = (message) => {
                if (resolved) return;
                
                if (message.type === 'attack_result') {
                    resolved = true;
                    clearTimeout(timeout);
                    this.removeHandler('attack_result', handler);
                    
                    resolve({
                        success: true,
                        outcome: message.outcome,
                        coordinate: message.coordinate
                    });
                } else if (message.type === 'error') {
                    resolved = true;
                    clearTimeout(timeout);
                    this.removeHandler('attack_result', handler);
                    reject(new Error(message.message));
                }
            };
            
            this.on('attack_result', handler);
            
            this.send({
                type: 'attack',
                gameId: sessionId,
                playerId: playerId,
                coordinate: coordinate
            });
        });
    },
    
    /**
     * Rendirse
     */
    async surrender() {
        const sessionId = localStorage.getItem('sessionId');
        const playerId = localStorage.getItem('playerId');
        
        console.log('[API] Enviando rendición');
        
        return new Promise((resolve, reject) => {
            const timeout = setTimeout(() => {
                reject(new Error('Timeout en rendición'));
            }, 5000);
            
            const handler = (message) => {
                if (message.type === 'game_state' && message.code === 220) {
                    clearTimeout(timeout);
                    this.removeHandler('game_state', handler);
                    
                    resolve({
                        success: true,
                        winner: message.winner
                    });
                } else if (message.type === 'error') {
                    clearTimeout(timeout);
                    this.removeHandler('game_state', handler);
                    reject(new Error(message.message));
                }
            };
            
            this.on('game_state', handler);
            
            this.send({
                type: 'surrender',
                gameId: sessionId,
                playerId: playerId
            });
        });
    },
    
    /**
     * Generar posicionamiento aleatorio (desde el servidor)
     * El servidor garantiza que NO haya solapamientos
     */
    async generateRandomPlacement(boardSize = 10) {
        console.log(`[API] Solicitando disposición aleatoria al servidor`);
        
        return new Promise((resolve, reject) => {
            const timeout = setTimeout(() => {
                reject(new Error('Timeout esperando disposición aleatoria'));
            }, 10000);
            
            const handler = (message) => {
                if (message.type === 'random_placement' && message.code === 250) {
                    clearTimeout(timeout);
                    this.removeHandler('random_placement', handler);
                    
                    resolve({
                        success: true,
                        ships: message.ships
                    });
                } else if (message.type === 'error') {
                    clearTimeout(timeout);
                    this.removeHandler('random_placement', handler);
                    reject(new Error(message.message));
                }
            };
            
            this.on('random_placement', handler);
            
            this.send({
                type: 'generate_random_placement',
                boardSize: boardSize
            });
        });
    },
    
    /**
     * Validaciones locales MÍNIMAS (solo para UI)
     * El servidor hace las validaciones REALES
     */
    isValidPlacement(positions, existingShips, boardSize) {
        // Solo validar límites para UI feedback
        for (const pos of positions) {
            if (pos.x < 0 || pos.x >= boardSize || pos.y < 0 || pos.y >= boardSize) {
                return false;
            }
        }
        
        // Validar colisiones para UI feedback
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
     * Conversión de coordenadas
     */
    parseCoordinate(coord) {
        const match = coord.match(/^([A-J])(\d+)$/i);
        if (!match) return null;
        
        const x = match[1].toUpperCase().charCodeAt(0) - 65;
        const y = parseInt(match[2]) - 1;
        
        return {x, y};
    },
    
    formatCoordinate(x, y) {
        const letter = String.fromCharCode(65 + x);
        const number = y + 1;
        return `${letter}${number}`;
    }
};

if (typeof module !== 'undefined' && module.exports) {
    module.exports = API;
}
