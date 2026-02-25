/**
 * Módulo API para comunicación con el servidor
 * WebSocket + HTTP para Batalla Naval
 */

console.log('[API] Módulo API cargado');

const API = {
    // Configuración de WebSocket
    get wsURL() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.hostname;
        const port = 8080; // Puerto dedicado para WebSocket
        console.log('[API] URL WebSocket:', `${protocol}//${host}:${port}`);
        return `${protocol}//${host}:${port}`;
    },
    
    get httpURL() {
        return `http://${window.location.hostname}:8000`; // Puerto dedicado para FastAPI/HTTP
    },
    
    ws: null,
    messageHandlers: {},
    reconnectAttempts: 0,
    maxReconnectAttempts: 5,
    reconnectDelay: 3000,
    
    /**
     * Inicialización completa: Health check + WS connect + ping
     */
    async init() {
        console.log('[API] Iniciando cliente...');
        
        try {
            // 1. Verificar health del servidor HTTP
            console.log('[API] Verificando salud del servidor HTTP...');
            const healthResponse = await fetch(`${this.httpURL}/api/health`);
            if (!healthResponse.ok) {
                throw new Error('Servidor HTTP no responde');
            }
            console.log('[API] ✓ Servidor HTTP activo');
            
            // 2. Conectar WebSocket
            console.log('[API] Conectando WebSocket...');
            await this._connectWebSocket();
            console.log('[API] ✓ WebSocket conectado');
            
            // 3. Hacer ping al servidor
            console.log('[API] Enviando ping al servidor...');
            await this._sendPing();
            console.log('[API] ✓ Ping exitoso');
            
            // 4. Verificar si hay sesión guardada
            this._checkSavedSession();
            
            return true;
        } catch (error) {
            console.error('[API] Error en inicialización:', error);
            throw error;
        }
    },
    
    /**
     * Conecta el WebSocket
     */
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
                
                // Timeout para conexión
                const timeout = setTimeout(() => {
                    reject(new Error('Timeout conectando WebSocket'));
                }, 5000);
                
                this.ws.addEventListener('open', () => clearTimeout(timeout));
                
            } catch (error) {
                reject(error);
            }
        });
    },
    
    /**
     * Envía un ping al servidor
     */
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
            this.send({
                type: 'ping'
            });
        });
    },
    
    /**
     * Verifica si hay sesión guardada y la restaura si es posible
     */
    _checkSavedSession() {
        const playerId = localStorage.getItem('playerId');
        const sessionId = localStorage.getItem('sessionId');
        
        if (playerId && sessionId) {
            console.log('[API] Sesión guardada encontrada, intentando reconectar...');
            
            // Notificar al juego que se intenta reconectar
            const event = new CustomEvent('session-restored', {
                detail: { playerId, sessionId }
            });
            document.dispatchEvent(event);
        }
    },
    
    /**
     * Intenta reconectar al servidor
     */
    _attemptReconnect() {
        const event = new CustomEvent('websocket-disconnected');
        document.dispatchEvent(event);
        
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            console.log(`[API] Intentando reconectar (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);
            
            setTimeout(() => {
                this._connectWebSocket()
                    .then(() => {
                        console.log('[API] ✓ Reconectado al servidor');
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
    
    /**
     * Envía un mensaje al servidor
     */
    send(message) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            console.log('[API] Enviando:', message.type);
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
    
    /**
     * Registra un handler para un tipo de mensaje
     * Soporta múltiples handlers para el mismo tipo
     */
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
    
    /**
     * Remueve un handler específico
     */
    removeHandler(messageType, handler) {
        if (this.messageHandlers[messageType]) {
            if (Array.isArray(this.messageHandlers[messageType])) {
                this.messageHandlers[messageType] = this.messageHandlers[messageType].filter(h => h !== handler);
            }
        }
    },
    
    /**
     * Se une a una partida con nombre de jugador
     */
    async joinGame(playerName) {
        console.log(`[API] Uniéndose a partida como: ${playerName}`);
        
        return new Promise((resolve, reject) => {
            const timeout = setTimeout(() => {
                reject(new Error('Timeout esperando respuesta de unión a partida'));
            }, 30000);
            
            const handler = (message) => {
                console.log('[API] Handler joinGame recibió mensaje:', message);
                // Aceptar cualquier respuesta de game_state que indique éxito
                if (message.code === 210 || message.code === 211 || message.code === 212 || message.code === 213) {
                    clearTimeout(timeout);
                    this.removeHandler('game_state', handler);
                    
                    console.log('[API] Game state recibido, guardando IDs...');
                    
                    // Guardar IDs en localStorage
                    if (message.playerId) {
                        localStorage.setItem('playerId', message.playerId);
                        console.log('[API] PlayerId guardado:', message.playerId);
                    }
                    if (message.gameId) {
                        localStorage.setItem('sessionId', message.gameId);
                        console.log('[API] SessionId guardado:', message.gameId);
                    }
                    
                    resolve({
                        success: true,
                        playerId: message.playerId,
                        sessionId: message.gameId,
                        gameState: message.code
                    });
                } else if (message.type === 'error') {
                    clearTimeout(timeout);
                    this.removeHandler('game_state', handler);
                    reject(new Error(message.message || 'Error al unirse a partida'));
                }
            };
            
            this.on('game_state', handler);
            
            // Enviar solicitud
            this.send({
                type: 'join_game',
                playerName: playerName
            });
        });
    },
    
    /**
     * Se reconecta a una partida existente
     */
    async reconnectGame(sessionId) {
        const playerId = localStorage.getItem('playerId');
        console.log(`[API] Reconectando a partida: ${sessionId}`);
        
        return new Promise((resolve, reject) => {
            const timeout = setTimeout(() => {
                reject(new Error('Timeout en reconexión'));
            }, 10000);
            
            let resolved = false;
            
            const handler = (message) => {
                if (resolved) return;
                
                // Mensaje de sesión expirada/cerrada
                if (message.type === 'game_over' && message.code === 220 && message.clearSession) {
                    resolved = true;
                    clearTimeout(timeout);
                    this.removeHandler('game_state', handler);
                    this.removeHandler('game_over', handler);
                    
                    // Señal para limpiar sesión
                    console.warn('[API] Sesión expirada, limpiando datos...');
                    const event = new CustomEvent('session-expired', {
                        detail: { reason: message.reason }
                    });
                    document.dispatchEvent(event);
                    
                    reject(new Error(message.message || 'Sesión expirada'));
                }
                
                else if (message.type === 'game_state' && message.gameId === sessionId) {
                    resolved = true;
                    clearTimeout(timeout);
                    this.removeHandler('game_state', handler);
                    
                    resolve({
                        success: true,
                        gameState: message
                    });
                } 
                else if (message.type === 'error' && message.clearSession) {
                    resolved = true;
                    clearTimeout(timeout);
                    this.removeHandler('game_state', handler);
                    reject(new Error(message.message || 'Error reconectando'));
                }
            };
            
            this.on('game_state', handler);
            this.on('game_over', handler);
            
            this.send({
                type: 'reconnect',
                gameId: sessionId,
                playerId: playerId
            });
        });
    },
    
    /**
     * Envía la disposición de barcos al servidor
     * Formato: Array de {type, positions, orientation}
     */
    async submitShipPlacement(ships) {
        const sessionId = localStorage.getItem('sessionId');
        const playerId = localStorage.getItem('playerId');
        
        console.log('[API] Enviando disposición de barcos');
        
        return new Promise((resolve, reject) => {
            const timeout = setTimeout(() => {
                reject(new Error('Timeout esperando confirmación de barcos'));
            }, 15000);
            
            const handler = (message) => {
                // Aceptar respuesta que indique ships colocados
                if (message.type === 'game_state' && 
                    (message.code === 212 || message.code === 213 || message.code === 215)) {
                    clearTimeout(timeout);
                    this.removeHandler('game_state', handler);
                    
                    resolve({
                        success: true,
                        gameState: message
                    });
                } else if (message.type === 'error') {
                    clearTimeout(timeout);
                    this.removeHandler('game_state', handler);
                    reject(new Error(message.message || 'Error colocando barcos'));
                }
            };
            
            this.on('game_state', handler);
            
            // Convertir formato de ships
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
     * Envía un ataque al servidor
     */
    async sendAttack(coordinate) {
        const sessionId = localStorage.getItem('sessionId');
        const playerId = localStorage.getItem('playerId');
        
        console.log(`[API] Enviando ataque a: ${JSON.stringify(coordinate)}`);
        
        return new Promise((resolve, reject) => {
            const timeout = setTimeout(() => {
                reject(new Error('Timeout esperando resultado del ataque'));
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
                } else if (message.type === 'game_state' && message.code === 220) {
                    // Fin de juego
                    resolved = true;
                    clearTimeout(timeout);
                    this.removeHandler('attack_result', handler);
                    
                    resolve({
                        success: true,
                        outcome: 'GAME_OVER',
                        gameFinished: true,
                        winner: message.winner
                    });
                } else if (message.type === 'error') {
                    resolved = true;
                    clearTimeout(timeout);
                    this.removeHandler('attack_result', handler);
                    reject(new Error(message.message || 'Error en ataque'));
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
     * Envía rendición al servidor
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
                    reject(new Error(message.message || 'Error en rendición'));
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
     * Genera posicionamiento aleatorio (validado por servidor luego)
     * Esta es una función local auxiliar
     */
    generateRandomPlacement(boardSize = 10) {
        const ships = GameState.placement.ships.map(ship => {
            const orientation = Math.random() > 0.5 ? 'HORIZONTAL' : 'VERTICAL';
            const positions = this._generateRandomPositions(ship.length, orientation, boardSize);
            
            return {
                id: ship.id,
                type: ship.type,
                positions: positions,
                orientation: orientation
            };
        });
        
        return Promise.resolve({
            success: true,
            ships: ships
        });
    },
    
    /**
     * Genera posiciones aleatorias para un barco
     */
    _generateRandomPositions(length, orientation, boardSize) {
        const positions = [];
        
        let startX, startY;
        if (orientation === 'HORIZONTAL') {
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
     * Validaciones locales básicas (el servidor hace la validación real)
     */
    isValidPlacement(positions, existingShips, boardSize) {
        // Verificar límites
        for (const pos of positions) {
            if (pos.x < 0 || pos.x >= boardSize || pos.y < 0 || pos.y >= boardSize) {
                return false;
            }
        }
        
        // Verificar colisiones básicas
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
     * Convierte entre notaciones de coordenadas
     */
    parseCoordinate(coord) {
        const match = coord.match(/^([A-J])(\d+)$/i);
        if (!match) return null;
        
        const x = match[1].toUpperCase().charCodeAt(0) - 65;
        const y = parseInt(match[2]) - 1;
        
        return { x, y };
    },
    
    formatCoordinate(x, y) {
        const letter = String.fromCharCode(65 + x);
        const number = y + 1;
        return `${letter}${number}`;
    }
};

// Exportar para módulos
if (typeof module !== 'undefined' && module.exports) {
    module.exports = API;
}