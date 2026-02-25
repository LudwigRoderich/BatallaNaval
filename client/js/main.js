/**
 * Módulo principal del juego - Inicialización y manejo de eventos
 * Arquitectura revisada para correcta sincronización cliente-servidor
 */

// ============================================
// INICIALIZACIÓN GLOBAL
// ============================================

document.addEventListener('DOMContentLoaded', async () => {
    console.log('=== BATALLA NAVAL INICIANDO ===');
    
    try {
        // 1. Inicializar estado (restaura sesión si existe)
        GameState.init();
        GameState.setupUnloadConfirmation();
        
        // 2. Conectar con servidor (health + ws + ping)
        Renderer.showConnecting();
        await API.init();
        Renderer.clearLoadingScreen();
        
        // 3. Registrar handlers globales
        setupGlobalMessageHandlers();
        setupGlobalEventListeners();
        
        // 4. Mostrar pantalla apropiada
        if (GameState.playerId && GameState.sessionId) {
            // Hay sesión guardada, intentar reconectar
            console.log('[MAIN] Sesión guardada encontrada');
            await handleSessionRestored();
        } else {
            // Nueva sesión
            GameState.switchScreen(GameState.SCREEN_START);
            setupStartScreen();
        }
        
        console.log('=== BATALLA NAVAL LISTA ===');
        
    } catch (error) {
        console.error('[MAIN] Error fatal:', error);
        showFatalError(`Error al inicializar: ${error.message}`);
    }
});

// ============================================
// HANDLERS GLOBALES DE MENSAJES DEL SERVIDOR
// ============================================

function setupGlobalMessageHandlers() {
    // Respuestas de game_state
    API.on('game_state', (message) => {
        console.log('[MAIN] Game state recibido:', message.code);
        
        // Guardar nombres si están disponibles
        if (message.playerName) {
            GameState.playerName = message.playerName;
            console.log('[MAIN] Nombre del jugador:', message.playerName);
        }
        if (message.opponentName) {
            GameState.opponentName = message.opponentName;
            console.log('[MAIN] Nombre del oponente:', message.opponentName);
        }
        
        // Actualizar game_state en el cliente
        if (message.code === 210) {
            // WAITING_FOR_OPPONENT
            console.log('[MAIN] Esperando oponente...');
            GameState.updateGameState(GameState.SERVER_STATE_WAITING_FOR_PLAYERS);
            if (GameState.currentScreen === GameState.SCREEN_START) {
                Renderer.showWaitingForOpponent(GameState.playerName);
            }
        } else if (message.code === 211 || message.code === 213) {
            // BOTH_PLAYERS_READY o PLACING_SHIPS
            console.log('[MAIN] Iniciando posicionamiento...');
            GameState.updateGameState(GameState.SERVER_STATE_PLACING_SHIPS);
            if (GameState.currentScreen !== GameState.SCREEN_PLACEMENT) {
                Renderer.clearLoadingScreen();
                GameState.switchScreen(GameState.SCREEN_PLACEMENT);
                setupPlacementFlow();
            }
        } else if (message.code === 212 || message.code === 215) {
            // GAME_STARTED o YOUR_TURN
            console.log('[MAIN] Juego iniciado');
            GameState.updateGameState(GameState.SERVER_STATE_IN_PROGRESS);
            if (message.currentTurn) {
                GameState.game.currentTurn = message.currentTurn;
                console.log('[MAIN] Turno actual:', message.currentTurn === GameState.playerId ? 'TÚ' : 'OPONENTE');
            }
            if (GameState.currentScreen === GameState.SCREEN_PLACEMENT || 
                GameState.currentScreen === GameState.SCREEN_WAITING_PLACEMENT) {
                Renderer.clearLoadingScreen();
                GameState.switchScreen(GameState.SCREEN_GAME);
                setupGameFlow();
            }
        } else if (message.code === 220) {
            // GAME_OVER
            console.log('[MAIN] Juego terminado. Ganador:', message.winner);
            GameState.updateGameState(GameState.SERVER_STATE_FINISHED);
            
            // Si clearSession está indicado, la sesión expiró
            if (message.clearSession) {
                console.warn('[MAIN] Sesión debe ser limpiada:', message.reason);
                handleSessionExpired(message.reason || 'session_expired');
            } else {
                // Fin normal del juego
                endGame(message.winner === GameState.playerId);
            }
        } else if (message.code === 216) {
            // WAITING_FOR_OPPONENT_TURN
            console.log('[MAIN] Esperando turno del oponente');
            Renderer.showWaitingForOpponentTurn(GameState.opponentName);
        }
    });
    
    // Notificaciones de oponente
    API.on('notification', (message) => {
        console.log('[MAIN] Notificación:', message.message);
        Renderer.addLogEntry(message.message, 'notification');
    });
    
    // Errores
    API.on('error', (message) => {
        console.error('[MAIN] Error del servidor:', message.message);
        showError(message.message || 'Error desconocido');
    });
}

function setupGlobalEventListeners() {
    // Desconexión del WebSocket
    document.addEventListener('websocket-disconnected', () => {
        console.warn('[MAIN] WebSocket desconectado');
        Renderer.showDisconnected();
    });
    
    // Reconexión del WebSocket
    document.addEventListener('websocket-reconnected', () => {
        console.log('[MAIN] WebSocket reconectado');
        Renderer.clearLoadingScreen();
        
        // Intentar reconectar a sesión si existe
        if (GameState.playerId && GameState.sessionId) {
            console.log('[MAIN] Reconectando a sesión existente...');
            API.reconnectGame(GameState.sessionId).catch(err => {
                console.error('[MAIN] Error reconectando:', err);
                handleSessionLost();
            });
        }
    });
    
    // Cambios de game_state
    document.addEventListener('game-state-changed', (e) => {
        console.log('[MAIN] Game state cambió a:', e.detail.gameState);
    });
    
    // Sesión restaurada desde localStorage
    document.addEventListener('session-restored', async (e) => {
        await handleSessionRestored();
    });
    
    // Sesión expirada con timeout
    document.addEventListener('session-expired', (e) => {
        console.warn('[MAIN] Sesión expirada por timeout:', e.detail.reason);
        Renderer.clearLoadingScreen();
        handleSessionExpired(e.detail.reason);
    });
}

// ============================================
// PANTALLA DE INICIO
// ============================================

function setupStartScreen() {
    const nameInput = document.getElementById('player-name');
    const joinBtn = document.getElementById('btn-find-match');
    
    if (!nameInput || !joinBtn) {
        console.error('[MAIN] Elementos de pantalla de inicio no encontrados');
        return;
    }
    
    // Limpiar valores previos
    nameInput.value = '';
    
    nameInput.addEventListener('input', (e) => {
        const name = e.target.value.trim();
        joinBtn.disabled = name.length < 2;
    });
    
    nameInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && nameInput.value.trim().length >= 2) {
            joinBtn.click();
        }
    });
    
    joinBtn.addEventListener('click', handleJoinGame);
}

async function handleJoinGame() {
    const nameInput = document.getElementById('player-name');
    const joinBtn = document.getElementById('btn-find-match');
    
    const playerName = nameInput.value.trim();
    
    if (playerName.length < 2) {
        showError('Nombre inválido (mínimo 2 caracteres)');
        return;
    }
    
    joinBtn.disabled = true;
    const originalText = joinBtn.innerHTML;
    joinBtn.innerHTML = '<span>BUSCANDO...</span>';
    Renderer.showWaitingForOpponent(playerName);
    
    try {
        console.log(`[MAIN] Uniendo a partida como: ${playerName}`);
        
        const result = await API.joinGame(playerName);
        
        GameState.playerName = playerName;
        GameState.playerId = result.playerId;
        GameState.sessionId = result.sessionId;
        
        console.log('[MAIN] ✓ Unido a partida');
        console.log(`   PlayerId: ${result.playerId}`);
        console.log(`   SessionId: ${result.sessionId}`);
        
        // El servidor enviará game_state con siguiente estado
        
    } catch (error) {
        console.error('[MAIN] Error uniéndose:', error);
        showError(`Error: ${error.message}`);
        Renderer.clearLoadingScreen();
        GameState.switchScreen(GameState.SCREEN_START);
        joinBtn.disabled = false;
        joinBtn.innerHTML = originalText;
    }
}

// ============================================
// FLUJO DE POSICIONAMIENTO
// ============================================

function setupPlacementFlow() {
    GameState.resetPlacement();
    GameState.switchScreen(GameState.SCREEN_PLACEMENT);
    setupPlacementUI();
}

function setupPlacementUI() {
    // Actualizar nombre del jugador en pantalla
    const playerNameEl = document.getElementById('placement-player-name');
    if (playerNameEl) {
        playerNameEl.textContent = GameState.playerName;
    }
    
    // Renderizar tablero
    Renderer.renderBoard('placement-board', GameState.boardSize, false);
    Renderer.renderShipsList(GameState.placement.ships);
    
    const board = document.getElementById('placement-board');
    const shipsList = document.getElementById('ships-list');
    const randomBtn = document.getElementById('btn-random-placement');
    const rotateBtn = document.getElementById('btn-rotate-ship');
    const confirmBtn = document.getElementById('btn-confirm-placement');
    
    if (!board || !shipsList) return;
    
    // Seleccionar barco
    shipsList.addEventListener('click', (e) => {
        const shipItem = e.target.closest('.ship-item');
        if (!shipItem || shipItem.classList.contains('placed')) return;
        
        const shipId = shipItem.dataset.shipId;
        
        document.querySelectorAll('.ship-item').forEach(item => {
            item.classList.remove('selected');
        });
        
        shipItem.classList.add('selected');
        GameState.selectShip(shipId);
    });
    
    // Rotación
    if (rotateBtn) {
        rotateBtn.addEventListener('click', () => {
            GameState.rotateShip();
            console.log(`[MAIN] Barco rotado a: ${GameState.placement.orientation}`);
        });
    }
    
    // Preview del tablero
    board.addEventListener('mousemove', (e) => {
        const cell = e.target.closest('.cell');
        if (!cell) return;
        
        const ship = GameState.getSelectedShip();
        if (!ship || ship.placed) {
            Renderer.clearShipPreview('placement-board');
            return;
        }
        
        const x = parseInt(cell.dataset.x);
        const y = parseInt(cell.dataset.y);
        const positions = calculateShipPositions(x, y, ship.length, ship.orientation);
        const isValid = API.isValidPlacement(positions, GameState.placement.placedShips, GameState.boardSize);

        Renderer.highlightShipPreview('placement-board', positions, isValid);
    });
    
    board.addEventListener('mouseleave', () => {
        Renderer.clearShipPreview('placement-board');
    });
    
    // Colocar barco
    board.addEventListener('click', (e) => {
        const cell = e.target.closest('.cell');
        if (!cell) return;
        
        const ship = GameState.getSelectedShip();
        if (!ship || ship.placed) return;
        
        const x = parseInt(cell.dataset.x);
        const y = parseInt(cell.dataset.y);
        const positions = calculateShipPositions(x, y, ship.length, ship.orientation);
        const isValid = API.isValidPlacement(positions, GameState.placement.placedShips, GameState.boardSize);
        
        if (!isValid) {
            showError('Posición inválida para el barco');
            return;
        }
        
        GameState.placeShip(ship.id, positions);
        Renderer.placeShipOnBoard('placement-board', positions, ship.type);
        Renderer.renderShipsList(GameState.placement.ships);
        Renderer.clearShipPreview('placement-board');
        
        GameState.selectShip(null);
        document.querySelectorAll('.ship-item').forEach(item => {
            item.classList.remove('selected');
        });
        
        if (GameState.allShipsPlaced() && confirmBtn) {
            confirmBtn.disabled = false;
        }
    });
    
    // Posicionamiento aleatorio
    if (randomBtn) {
        randomBtn.addEventListener('click', async () => {
            randomBtn.disabled = true;
            randomBtn.innerHTML = '<span>GENERANDO...</span>';
            
            try {
                GameState.resetPlacement();
                Renderer.clearAllBoards();
                Renderer.renderBoard('placement-board', GameState.boardSize, false);
                
                const result = await API.generateRandomPlacement(GameState.boardSize);
                
                if (result.success) {
                    result.ships.forEach(ship => {
                        const shipData = GameState.placement.ships.find(s => s.id === ship.id);
                        if (shipData) {
                            // Actualizar orientación del barco con la generada aleatoriamente
                            shipData.orientation = ship.orientation;
                            GameState.placeShip(ship.id, ship.positions);
                            Renderer.placeShipOnBoard('placement-board', ship.positions, ship.type);
                        }
                    });
                    
                    Renderer.renderShipsList(GameState.placement.ships);
                    
                    if (confirmBtn) confirmBtn.disabled = false;
                }
            } catch (error) {
                showError('Error generando posicionamiento');
            } finally {
                randomBtn.disabled = false;
                randomBtn.innerHTML = '<span>ALEATORIO</span>';
            }
        });
    }
    
    // Confirmar posicionamiento
    if (confirmBtn) {
        confirmBtn.addEventListener('click', handleConfirmPlacement);
    }
}

async function handleConfirmPlacement() {
    const confirmBtn = document.getElementById('btn-confirm-placement');
    if (!confirmBtn) return;
    
    if (!GameState.allShipsPlaced()) {
        showError('Debes colocar todos los barcos primero');
        return;
    }
    
    confirmBtn.disabled = true;
    const originalText = confirmBtn.innerHTML;
    confirmBtn.innerHTML = '<span>ENVIANDO...</span>';
    
    try {
        console.log('[MAIN] Enviando posicionamiento de barcos...');
        console.log('Barcos a enviar:', GameState.placement.placedShips);
        await API.submitShipPlacement(GameState.placement.placedShips);
        
        console.log('[MAIN] ✓ Barcos colocados');
        Renderer.showWaitingForShipPlacement();
        
    } catch (error) {
        console.error('[MAIN] Error enviando barcos:', error);
        showError(`Error: ${error.message}`);
        confirmBtn.disabled = false;
        confirmBtn.innerHTML = originalText;
    }
}

// ============================================
// FLUJO DE JUEGO
// ============================================

function setupGameFlow() {
    console.log('[MAIN] Configurando flujo de juego...');
    
    // Inicializar tableros
    GameState.initDefenseBoard = () => {
        GameState.game.defenseBoard = Array(GameState.boardSize).fill(null).map(() => 
            Array(GameState.boardSize).fill('empty')
        );
    };
    
    GameState.initAttackBoard = () => {
        GameState.game.attackBoard = Array(GameState.boardSize).fill(null).map(() => 
            Array(GameState.boardSize).fill('empty')
        );
    };
    
    GameState.initDefenseBoard();
    GameState.initAttackBoard();
    
    // Renderizar tableros
    Renderer.renderBoard('defense-board', GameState.boardSize, false);
    Renderer.renderBoard('attack-board', GameState.boardSize, true);
    
    // Actualizar nombres del juego
    const playerNameEl = document.getElementById('game-player-name');
    const opponentNameEl = document.getElementById('game-opponent-name');
    if (playerNameEl) playerNameEl.textContent = GameState.playerName || '-';
    if (opponentNameEl) opponentNameEl.textContent = GameState.opponentName || '-';
    
    // Mostrar barcos propios
    GameState.placement.placedShips.forEach(ship => {
        ship.positions.forEach(pos => {
            Renderer.updateCell('defense-board', pos.x, pos.y, 'ship', ship.type);
        });
    });
    
    // Event listener para ataques
    const attackBoard = document.getElementById('attack-board');
    if (attackBoard) {
        attackBoard.addEventListener('click', handleAttackClick);
        console.log('[MAIN] Listeners de ataque registrados');
    }
    
    GameState.startGameTimer();
    Renderer.addLogEntry('¡Juego iniciado!', 'info');
    console.log('[MAIN] ✓ Flujo de juego configurado');
}

async function handleAttackClick(e) {
    const cell = e.target.closest('.cell');
    if (!cell) return;
    
    console.log('[MAIN] Clic en celda de ataque');
    
    // Verificar que sea turno del jugador
    if (GameState.game.currentTurn !== GameState.playerId) {
        console.warn('[MAIN] No es tu turno');
        showError('No es tu turno');
        return;
    }
    
    if (cell.classList.contains('hit') || cell.classList.contains('miss') || cell.classList.contains('sunk')) {
        console.warn('[MAIN] Celda ya atacada');
        return;
    }
    
    const x = parseInt(cell.dataset.x);
    const y = parseInt(cell.dataset.y);
    const coordinate = { x, y };
    
    const board = document.getElementById('attack-board');
    board.style.pointerEvents = 'none';
    
    try {
        console.log(`[MAIN] Atacando coordenada: (${x}, ${y})`);
        
        const result = await API.sendAttack(coordinate);
        console.log('[MAIN] Resultado de ataque:', result.outcome);
        
        if (result.success) {
            let cellState = 'miss';
            let logMessage = `Reporta agua en ${API.formatCoordinate(x, y)}`;
            let logType = 'miss';
            
            if (result.outcome === 'HIT') {
                cellState = 'hit';
                logMessage = `¡IMPACTO! en ${API.formatCoordinate(x, y)}`;
                logType = 'hit';
                console.log('[MAIN] ¡Impacto confirmado!');
            } else if (result.outcome === 'SHIP_SUNK') {
                cellState = 'sunk';
                logMessage = `¡BARCO HUNDIDO! en ${API.formatCoordinate(x, y)}`;
                logType = 'sunk';
                GameState.game.enemyShipsRemaining--;
                console.log('[MAIN] ¡Barco hundido!', 'Barcos restantes:', GameState.game.enemyShipsRemaining);
            }
            
            Renderer.updateCell('attack-board', x, y, cellState);
            Renderer.addLogEntry(logMessage, logType);
            GameState.addCombatLog(logMessage, logType);
            
            GameState.game.moveCount++;
            Renderer.updateMoveCount(GameState.game.moveCount);
            
            if (result.gameFinished) {
                setTimeout(() => {
                    endGame(result.winner === GameState.playerId);
                }, 1500);
            } else {
                // El servidor enviará game_state con nuevo turno
                Renderer.showWaitingForOpponentTurn(GameState.opponentName);
            }
        }
    } catch (error) {
        console.error('[MAIN] Error atacando:', error);
        showError(`Error en ataque: ${error.message}`);
    } finally {
        board.style.pointerEvents = 'auto';
    }
}

// ============================================
// FIN DE JUEGO
// ============================================

function endGame(isVictory) {
    GameState.stopGameTimer();
    
    const stats = {
        totalMoves: GameState.game.moveCount,
        accuracy: 0, // TODO: Calcular desde el servidor
        duration: GameState.getGameDuration()
    };
    
    const winner = isVictory ? GameState.playerName : GameState.opponentName || 'Oponente';
    const loser = isVictory ? GameState.opponentName || 'Oponente' : GameState.playerName;
    
    Renderer.renderGameOver(winner, loser, stats);
    GameState.switchScreen(GameState.SCREEN_GAMEOVER);
    
    setupGameOverScreen();
}

function setupGameOverScreen() {
    const playAgainBtn = document.getElementById('btn-play-again');
    
    if (playAgainBtn) {
        playAgainBtn.addEventListener('click', () => {
            GameState.clear();
            Renderer.clearAllBoards();
            GameState.switchScreen(GameState.SCREEN_START);
            setupStartScreen();
        });
    }
}

// ============================================
// MANEJO DE RECONEXIÓN Y SESIÓN
// ============================================

async function handleSessionRestored() {
    console.log('[MAIN] Restaurando sesión guardada...');
    Renderer.showReconnecting();
    
    try {
        const result = await API.reconnectGame(GameState.sessionId);
        Renderer.clearLoadingScreen();
        
        console.log('[MAIN] ✓ Reconectado a sesión');
        
        // Sincronizar estado con servidor (el handler de game_state manejará el resto)
        
    } catch (error) {
        console.error('[MAIN] Error restaurando sesión:', error);
        Renderer.clearLoadingScreen();
        handleSessionLost();
    }
}

function handleSessionLost() {
    console.log('[MAIN] Sesión perdida, volviendo a inicio');
    GameState.clear();
    GameState.switchScreen(GameState.SCREEN_START);
    setupStartScreen();
    showWarning('Se perdió la conexión. Por favor, inicia sesión de nuevo.');
}

function handleSessionExpired(reason) {
    console.log('[MAIN] Sesión expirada por:', reason);
    GameState.clear();
    GameState.switchScreen(GameState.SCREEN_START);
    setupStartScreen();
    
    let message = 'La sesión ha expirado.';
    if (reason === 'opponent_timeout') {
        message = 'Tu oponente no se reconectó a tiempo. Volviendo al inicio.';
    } else if (reason === 'reconnect_timeout') {
        message = 'Se agotó el tiempo para reconectarse. Volviendo al inicio.';
    } else if (reason === 'session_expired') {
        message = 'La sesión no existe o ha expirado. Por favor, inicia una nueva partida.';
    }
    
    showWarning(message);
}

// ============================================
// UTILIDADES
// ============================================

function calculateShipPositions(startX, startY, length, orientation) {
    const positions = [];
    
    for (let i = 0; i < length; i++) {
        if (orientation === 'HORIZONTAL') {
            positions.push({ x: startX + i, y: startY });
        } else {
            positions.push({ x: startX, y: startY + i });
        }
    }
    
    return positions;
}

function showError(message) {
    console.error('[ERROR]', message);
    // TODO: Mejorar con toast/modal UI
    alert(message);
}

function showWarning(message) {
    console.warn('[WARNING]', message);
}

function showFatalError(message) {
    console.error('[FATAL]', message);
    document.body.innerHTML = `
        <div style="
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            background: linear-gradient(135deg, #0a1628 0%, #162033 100%);
            color: white;
            font-family: monospace;
            padding: 20px;
        ">
            <div style="text-align: center;">
                <h1 style="color: #e63946; margin-bottom: 10px;">ERROR FATAL</h1>
                <p>${message}</p>
                <p style="margin-top: 20px; color: #aaa; font-size: 12px;">Recarga la página para reintentar</p>
            </div>
        </div>
    `;
}

console.log('[MAIN] Módulo main.js cargado');
