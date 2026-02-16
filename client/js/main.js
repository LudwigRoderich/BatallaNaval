/**
 * Módulo principal del juego - Inicialización y manejo de eventos
 * Este archivo orquesta todos los módulos
 */

// ============================================
// INICIALIZACIÓN GLOBAL
// ============================================

/**
 * Punto de entrada principal - ejecuta cuando el DOM está listo
 */
document.addEventListener('DOMContentLoaded', async () => {
    console.log('=== BATALLA NAVAL INICIANDO ===');
    
    try {
        // 1. Conectar con el servidor
        console.log('[MAIN] Conectando con servidor...');
        await API.init();
        console.log('[MAIN] ✓ Conexión WebSocket establecida');
        
        // 2. Inicializar estado del juego
        console.log('[MAIN] Inicializando estado del juego...');
        GameState.init();
        console.log('[MAIN] ✓ Estado inicializado');
        
        // 3. Configurar todos los eventos
        console.log('[MAIN] Configurando eventos...');
        setupAllEventListeners();
        console.log('[MAIN] ✓ Eventos configurados');
        
        // 4. Renderizar pantalla inicial
        console.log('[MAIN] Renderizando pantalla inicial...');
        GameState.switchScreen('start');
        console.log('[MAIN] ✓ Pantalla inicial renderizada');
        
        console.log('=== BATALLA NAVAL LISTA ===');
        
    } catch (error) {
        console.error('[MAIN] Error fatal en inicialización:', error);
        showFatalError('Error al conectar con el servidor. Recarga la página.');
    }
});

// ============================================
// FUNCIONES DE CONFIGURACIÓN CENTRAL
// ============================================

/**
 * Configura todos los event listeners del juego
 * Esta es la función que centraliza TODOS los eventos
 */
function setupAllEventListeners() {
    setupStartScreen();
    setupPlacementScreen();
    setupGameScreen();
    setupGameOverScreen();
    
    // Eventos globales
    setupGlobalEvents();
}

/**
 * Eventos globales que afectan todo el juego
 */
function setupGlobalEvents() {
    // Manejar desconexión del WebSocket
    document.addEventListener('websocket-disconnected', () => {
        console.warn('[MAIN] WebSocket desconectado');
        showWarning('Desconectado del servidor. Intentando reconectar...');
    });
    
    // Manejar reconexión
    document.addEventListener('websocket-reconnected', () => {
        console.log('[MAIN] WebSocket reconectado');
        showSuccess('Reconectado al servidor');
    });
    
    // Manejar errores del servidor
    API.on('error', (message) => {
        console.error('[MAIN] Error del servidor:', message);
        showError(message.message || 'Error desconocido');
    });
}

// ============================================
// PANTALLA DE INICIO
// ============================================

function setupStartScreen() {
    const nameInput = document.getElementById('player-name');
    const findMatchBtn = document.getElementById('btn-find-match');
    
    if (nameInput) {
        nameInput.addEventListener('input', (e) => {
            const name = e.target.value.trim();
            if (findMatchBtn) {
                findMatchBtn.disabled = name.length < 2;
            }
        });
        
        nameInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && nameInput.value.trim().length >= 2) {
                findMatchBtn?.click();
            }
        });
    }
    
    if (findMatchBtn) {
        findMatchBtn.addEventListener('click', handleFindMatch);
    }
}

async function handleFindMatch() {
    const nameInput = document.getElementById('player-name');
    const findMatchBtn = document.getElementById('btn-find-match');
    
    const name = nameInput.value.trim();
    if (name.length < 2) {
        showError('Nombre inválido (mínimo 2 caracteres)');
        return;
    }
    
    findMatchBtn.disabled = true;
    findMatchBtn.innerHTML = '<span class="btn-text">BUSCANDO...</span>';
    
    try {
        console.log(`[MAIN] Buscando partida para: ${name}`);
        
        // Llamar API para buscar partida
        const result = await API.findMatch(name);
        
        // Guardar datos en estado
        GameState.setPlayerName(name);
        
        // Cambiar a pantalla de posicionamiento
        GameState.switchScreen('placement');
        Renderer.updatePlayerName(name);
        setupPlacementBoard();
        Renderer.renderShipsList(GameState.placement.ships);
        
        console.log('[MAIN] ✓ Partida encontrada, lista de posicionamiento abierta');
        
    } catch (error) {
        console.error('[MAIN] Error al buscar partida:', error);
        showError('Error al buscar partida: ' + error.message);
    } finally {
        findMatchBtn.disabled = false;
        findMatchBtn.innerHTML = '<span class="btn-text">INICIAR BÚSQUEDA</span><span class="btn-icon">▶</span>';
    }
}

// ============================================
// PANTALLA DE POSICIONAMIENTO
// ============================================

function setupPlacementScreen() {
    const randomBtn = document.getElementById('btn-random-placement');
    const rotateBtn = document.getElementById('btn-rotate-ship');
    const confirmBtn = document.getElementById('btn-confirm-placement');
    
    if (randomBtn) {
        randomBtn.addEventListener('click', handleRandomPlacement);
    }
    
    if (rotateBtn) {
        rotateBtn.addEventListener('click', handleRotateShip);
    }
    
    if (confirmBtn) {
        confirmBtn.addEventListener('click', handleConfirmPlacement);
    }
}

function setupPlacementBoard() {
    Renderer.renderBoard('placement-board', GameState.boardSize, false);
    
    const board = document.getElementById('placement-board');
    const shipsList = document.getElementById('ships-list');
    
    // Seleccionar barcos
    if (shipsList) {
        shipsList.addEventListener('click', (e) => {
            const shipItem = e.target.closest('.ship-item');
            if (!shipItem || shipItem.classList.contains('placed')) return;
            
            const shipId = shipItem.dataset.shipId;
            
            shipsList.querySelectorAll('.ship-item').forEach(item => {
                item.classList.remove('selected');
            });
            
            shipItem.classList.add('selected');
            GameState.selectShip(shipId);
            
            const rotateBtn = document.getElementById('btn-rotate-ship');
            if (rotateBtn) rotateBtn.disabled = false;
        });
    }
    
    // Eventos del tablero
    if (board) {
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
            
            const positions = calculateShipPositions(x, y, ship.length, GameState.placement.orientation);
            const isValid = API.isValidPlacement(positions, GameState.placement.placedShips, GameState.boardSize);
            
            Renderer.highlightShipPreview('placement-board', positions, isValid);
        });
        
        board.addEventListener('mouseleave', () => {
            Renderer.clearShipPreview('placement-board');
        });
        
        board.addEventListener('click', (e) => {
            const cell = e.target.closest('.cell');
            if (!cell) return;
            
            const ship = GameState.getSelectedShip();
            if (!ship || ship.placed) return;
            
            const x = parseInt(cell.dataset.x);
            const y = parseInt(cell.dataset.y);
            
            const positions = calculateShipPositions(x, y, ship.length, GameState.placement.orientation);
            const isValid = API.isValidPlacement(positions, GameState.placement.placedShips, GameState.boardSize);
            
            if (isValid) {
                GameState.placeShip(ship.id, positions);
                Renderer.placeShipOnBoard('placement-board', positions);
                Renderer.renderShipsList(GameState.placement.ships);
                Renderer.clearShipPreview('placement-board');
                
                GameState.selectShip(null);
                document.querySelectorAll('.ship-item').forEach(item => {
                    item.classList.remove('selected');
                });
                
                const rotateBtn = document.getElementById('btn-rotate-ship');
                if (rotateBtn) rotateBtn.disabled = true;
                
                if (GameState.allShipsPlaced()) {
                    const confirmBtn = document.getElementById('btn-confirm-placement');
                    if (confirmBtn) confirmBtn.disabled = false;
                }
            }
        });
    }
}

async function handleRandomPlacement() {
    const randomBtn = document.getElementById('btn-random-placement');
    if (!randomBtn) return;
    
    randomBtn.disabled = true;
    randomBtn.innerHTML = '<span>GENERANDO...</span>';
    
    try {
        GameState.resetPlacement();
        Renderer.clearAllBoards();
        setupPlacementBoard();
        
        const result = await API.generateRandomPlacement(GameState.boardSize);
        
        if (result.success) {
            result.ships.forEach(ship => {
                const shipData = GameState.placement.ships.find(s => s.id === ship.id);
                if (shipData) {
                    GameState.placeShip(ship.id, ship.positions);
                    Renderer.placeShipOnBoard('placement-board', ship.positions);
                }
            });
            
            Renderer.renderShipsList(GameState.placement.ships);
            
            const confirmBtn = document.getElementById('btn-confirm-placement');
            if (confirmBtn) confirmBtn.disabled = false;
        }
    } catch (error) {
        console.error('[MAIN] Error generando posicionamiento:', error);
        showError('Error al generar posicionamiento');
    } finally {
        randomBtn.disabled = false;
        randomBtn.innerHTML = '<span>ALEATORIO</span>';
    }
}

function handleRotateShip() {
    GameState.rotateShip();
    console.log(`[MAIN] Barco rotado a: ${GameState.placement.orientation}`);
}

async function handleConfirmPlacement() {
    const confirmBtn = document.getElementById('btn-confirm-placement');
    if (!confirmBtn) return;
    
    confirmBtn.disabled = true;
    confirmBtn.innerHTML = '<span>CONFIRMANDO...</span>';
    
    try {
        await API.submitShipPlacement(GameState.matchId, GameState.placement.placedShips);
        
        GameState.switchScreen('game');
        setupGameBoards();
        GameState.startGameTimer();
        
        Renderer.updateTurnInfo(GameState.playerName, true);
        Renderer.updateMoveCount(0);
        Renderer.updateShipsRemaining(5, 5);
        
        console.log('[MAIN] ✓ Barcos confirmados, juego iniciado');
        
    } catch (error) {
        console.error('[MAIN] Error confirmando posicionamiento:', error);
        showError('Error al confirmar posicionamiento');
    } finally {
        confirmBtn.disabled = false;
        confirmBtn.innerHTML = '<span>CONFIRMAR DISPOSICIÓN</span>';
    }
}

// ============================================
// PANTALLA DE JUEGO
// ============================================

function setupGameScreen() {
    // Los eventos se configuran cuando se entra a la pantalla
}

function setupGameBoards() {
    Renderer.renderBoard('defense-board', GameState.boardSize, false);
    Renderer.renderBoard('attack-board', GameState.boardSize, true);
    
    GameState.initDefenseBoard();
    GameState.initAttackBoard();
    
    GameState.placement.placedShips.forEach(ship => {
        ship.positions.forEach(pos => {
            Renderer.updateCell('defense-board', pos.x, pos.y, 'ship');
        });
    });
    
    const attackBoard = document.getElementById('attack-board');
    if (attackBoard) {
        attackBoard.addEventListener('click', handleAttackCell);
    }
}

async function handleAttackCell(e) {
    const cell = e.target.closest('.cell');
    if (!cell) return;
    
    if (cell.classList.contains('hit') || cell.classList.contains('miss') || cell.classList.contains('sunk')) {
        return;
    }
    
    const x = parseInt(cell.dataset.x);
    const y = parseInt(cell.dataset.y);
    const coordinate = API.formatCoordinate(x, y);
    
    const attackBoard = document.getElementById('attack-board');
    attackBoard.style.pointerEvents = 'none';
    
    try {
        const result = await API.sendAttack(GameState.matchId, coordinate);
        
        if (result.success) {
            let cellState = 'miss';
            let logType = 'miss';
            let logMessage = `Atacaste ${coordinate}: Agua`;
            
            if (result.outcome === 'HIT') {
                cellState = 'hit';
                logType = 'hit';
                logMessage = `Atacaste ${coordinate}: ¡Impacto!`;
            } else if (result.outcome === 'SHIP_SUNK') {
                cellState = 'sunk';
                logType = 'sunk';
                logMessage = `Atacaste ${coordinate}: ¡BARCO HUNDIDO!`;
                
                GameState.game.enemyShipsRemaining--;
                Renderer.updateShipsRemaining(
                    GameState.game.yourShipsRemaining,
                    GameState.game.enemyShipsRemaining
                );
            }
            
            Renderer.updateCell('attack-board', x, y, cellState);
            Renderer.animateAttack('attack-board', x, y, cellState !== 'miss');
            
            GameState.addCombatLog(logMessage, logType);
            Renderer.addLogEntry(logMessage, logType);
            
            GameState.game.moveCount++;
            Renderer.updateMoveCount(GameState.game.moveCount);
            
            if (result.gameFinished) {
                setTimeout(() => {
                    endGame(result.winner === GameState.playerId);
                }, 1500);
            }
        }
    } catch (error) {
        console.error('[MAIN] Error en ataque:', error);
        Renderer.addLogEntry('Error al enviar ataque', 'error');
    } finally {
        attackBoard.style.pointerEvents = 'auto';
    }
}

// ============================================
// PANTALLA DE FIN DE JUEGO
// ============================================

function setupGameOverScreen() {
    const playAgainBtn = document.getElementById('btn-play-again');
    
    if (playAgainBtn) {
        playAgainBtn.addEventListener('click', () => {
            GameState.reset();
            Renderer.clearAllBoards();
            GameState.switchScreen('start');
            
            const nameInput = document.getElementById('player-name');
            if (nameInput) nameInput.value = '';
        });
    }
}

function endGame(isVictory) {
    GameState.stopGameTimer();
    
    const winner = isVictory ? GameState.playerName : 'Oponente';
    const loser = isVictory ? 'Oponente' : GameState.playerName;
    
    const totalAttacks = GameState.game.moveCount;
    const hits = 5 * 5 - GameState.game.enemyShipsRemaining * 3;
    const accuracy = totalAttacks > 0 ? Math.round((hits / totalAttacks) * 100) : 0;
    
    const stats = {
        totalMoves: GameState.game.moveCount,
        accuracy: accuracy,
        duration: GameState.getGameDuration()
    };
    
    Renderer.renderGameOver(winner, loser, stats);
    GameState.switchScreen('gameover');
}

// ============================================
// UTILIDADES
// ============================================

function calculateShipPositions(startX, startY, length, orientation) {
    const positions = [];
    
    for (let i = 0; i < length; i++) {
        if (orientation === 'horizontal') {
            positions.push({ x: startX + i, y: startY });
        } else {
            positions.push({ x: startX, y: startY + i });
        }
    }
    
    return positions;
}

/**
 * Muestra un error al usuario
 */
function showError(message) {
    console.error('[ERROR]', message);
    alert(message); // TODO: Mejorar con UI modal
}

/**
 * Muestra una advertencia al usuario
 */
function showWarning(message) {
    console.warn('[WARNING]', message);
    // TODO: Mejorar con UI modal
}

/**
 * Muestra un mensaje de éxito
 */
function showSuccess(message) {
    console.log('[SUCCESS]', message);
    // TODO: Mejorar con UI modal
}

/**
 * Muestra error fatal
 */
function showFatalError(message) {
    console.error('[FATAL]', message);
    document.body.innerHTML = `<div style="padding: 20px; color: red;"><h1>Error Fatal</h1><p>${message}</p></div>`;
}

console.log('[MAIN] Módulo main.js cargado');
