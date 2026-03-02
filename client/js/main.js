

document.addEventListener('DOMContentLoaded', async () => {
    console.log('=== BATALLA NAVAL INICIANDO (ARQUITECTURA REACTIVA) ===');
    
    try {
        // 1. Inicializar estado
        GameState.init();
        GameState.setupUnloadConfirmation();
        
        // 2. Conectar con servidor
        Renderer.showConnecting();
        await API.init();
        Renderer.clearLoadingScreen();
        
        // 3. Registrar handlers GLOBALES (escucha perpetua)
        setupGlobalMessageHandlers();
        setupGlobalEventListeners();
        
        // 4. Mostrar pantalla apropiada
        if (GameState.playerId && GameState.sessionId) {
            console.log('[MAIN] Sesión guardada encontrada, intentando reconectar');
            await handleSessionRestored();
        } else {
            GameState.switchScreen(GameState.SCREEN_START);
            setupStartScreen();
        }
        
        console.log('=== BATALLA NAVAL LISTA (CLIENTE REACTIVO) ===');
        
    } catch (error) {
        console.error('[MAIN] Error fatal:', error);
        showFatalError(`Error al inicializar: ${error.message}`);
    }
});

/**
 * Handlers GLOBALES que escuchan PERPETUAMENTE
 * El cliente NUNCA toma iniciativa, siempre responde a lo que el servidor dice
 */
function setupGlobalMessageHandlers() {
    
    API.on('game_state', (message) => {
        console.log('[HANDLERS] game_state recibido:', {code: message.code, state: message.state});
        console.log('Mensaje completo:', message);
        
        // Guardar nombres del mensaje
        if (message.playerName) GameState.playerName = message.playerName;
        if (message.opponentName) GameState.opponentName = message.opponentName;
        
        switch(message.code) {
            case 210: // WAITING_FOR_OPPONENT
                console.log('[HANDLERS] → Esperando oponente');
                Renderer.showWaitingForOpponent(GameState.playerName);
                break;
                
            case 211: // BOTH_PLAYERS_READY
                console.log('[HANDLERS] → Ambos jugadores listos, preparar para colocar barcos');
                Renderer.clearLoadingScreen();
                GameState.switchScreen(GameState.SCREEN_PLACEMENT);
                setupPlacementScreen();
                break;
                
            case 213: // WAITING_FOR_SHIPS (el otro jugador aún está colocando)
                console.log('[HANDLERS] → Barcos colocados, esperando al oponente');
                Renderer.showWaitingForShipPlacement();
                break;
                
            case 212: // GAME_STARTED (ambos colocaron, el juego comienza)
                console.log('[HANDLERS] → Juego iniciado, mostrar tableros');
                Renderer.clearLoadingScreen();
                GameState.switchScreen(GameState.SCREEN_GAME);
                setupGameScreen();
                
                if (message.currentTurn === GameState.playerId) {
                    Renderer.addLogEntry('¡Es tu turno!', 'info');
                } else {
                    Renderer.addLogEntry(`Turno de ${message.opponentName}`, 'info');
                }
                break;
                
            case 215: // YOUR_TURN (cambio de turno, ahora te toca)
                console.log('[HANDLERS] → Es tu turno');
                Renderer.addLogEntry('¡Es tu turno!', 'info');
                Renderer.enableAttackBoard(true);
                
                if (message.yourShipsRemaining !== undefined && message.enemyShipsRemaining !== undefined) {
                    Renderer.updateShipsRemaining(message.yourShipsRemaining, message.enemyShipsRemaining);
                }
                break;
                
            case 216: // WAITING_FOR_OPPONENT_TURN (se acabó tu turno)
                console.log('[HANDLERS] → Esperando turno del oponente');
                Renderer.addLogEntry(`Turno de ${message.opponentName}`, 'info');
                Renderer.enableAttackBoard(false);
                
                if (message.yourShipsRemaining !== undefined && message.enemyShipsRemaining !== undefined) {
                    Renderer.updateShipsRemaining(message.yourShipsRemaining, message.enemyShipsRemaining);
                }
                break;
                
            case 220: // GAME_OVER
                console.log('[HANDLERS] ', message.message);
                Renderer.clearLoadingScreen();
                endGame(message);
                break;
                
            case 230: // RECONNECTING
                console.log('[HANDLERS] → Estado 230: reconectando');
                Renderer.showReconnecting();
                Renderer.hideNotification();
                break;
                
            case 231: // RECONNECT_SUCCESS
                console.log('[HANDLERS] → Estado 231: reconexión exitosa, restaurando estado');
                restoreGameStateFromServer(message);
                Renderer.hideNotification();
                break;
                
            default:
                console.warn('[HANDLERS] Código desconocido:', message.code);
        }
    });
    
    
    API.on('attack_result', (message) => {
        console.log('[HANDLERS] attack_result recibido:', {x: message.x, y: message.y, outcome: message.outcome});
        
        const {x, y, outcome, shipSunk} = message;
        
        GameState.game.moveCount++;
        Renderer.updateMoveCount(GameState.game.moveCount);
        
        GameState.updateAttackCell(x, y, outcome.toLowerCase());
        
        localStorage.setItem('attackBoard', JSON.stringify(GameState.game.attackBoard));
        
        const cellState = outcome === 'MISS' ? 'miss' : outcome === 'HIT' ? 'hit' : 'sunk';
        Renderer.updateCell('attack-board', x, y, cellState);
        Renderer.animateAttack('attack-board', x, y, outcome === 'HIT' || outcome === 'SHIP_SUNK');
        switch(outcome) {
            case 'HIT':
                Renderer.addLogEntry(`¡Acierto en ${API.formatCoordinate(x, y)}!`, 'hit');
                break;
            case 'MISS':
                Renderer.addLogEntry(`Fallo en ${API.formatCoordinate(x, y)}`, 'miss');
                break;
            case 'SHIP_SUNK':
                Renderer.addLogEntry(`¡Barco hundido en ${API.formatCoordinate(x, y)}!`, 'sunk');
                break;
        }
        
        Renderer.enableAttackBoard(false);
        console.log('[HANDLERS] ✓ attack_result renderizado');
    });
    
  
    API.on('opponent_attack', (message) => {
        console.log('[HANDLERS] opponent_attack recibido:', {x: message.x, y: message.y, outcome: message.outcome, opponentName: message.opponentName});
        
        const {x, y, outcome, shipSunk, opponentName} = message;
        
        GameState.updateDefenseCell(x, y, outcome.toLowerCase());
        
        localStorage.setItem('defenseBoard', JSON.stringify(GameState.game.defenseBoard));
        
        const cellState = outcome === 'MISS' ? 'miss' : outcome === 'HIT' ? 'hit' : 'sunk';
        Renderer.updateCell('defense-board', x, y, cellState);
        Renderer.animateAttack('defense-board', x, y, outcome === 'HIT' || outcome === 'SHIP_SUNK');
        
        switch(outcome) {
            case 'HIT':
                Renderer.addLogEntry(`¡${opponentName || 'Oponente'} golpeó en ${API.formatCoordinate(x, y)}!`, 'warning');
                break;
            case 'MISS':
                Renderer.addLogEntry(`${opponentName || 'Oponente'} falló en ${API.formatCoordinate(x, y)}`, 'info');
                break;
            case 'SHIP_SUNK':
                Renderer.addLogEntry(`¡${opponentName || 'Oponente'} hundió un barco en ${API.formatCoordinate(x, y)}!`, 'danger');
                break;
        }
        
        console.log('[HANDLERS] ✓ opponent_attack renderizado');
    });
    
    
    API.on('notification', (message) => {
        console.log('[HANDLERS] notification:', message.message, 'code:', message.code);
        Renderer.addLogEntry(message.message, 'notification');
        
        // Mostrar modal para notificaciones críticas (desconexión)
        if (message.code === 450) {  // OPPONENT_DISCONNECTED
            if (GameState.currentScreen  !== GameState.SCREEN_GAMEOVER){
                Renderer.showNotification(
                    '⚠️ ATENCIÓN',
                    message.message,
                    null,
                    null,
                    true  // Escapable
                );
            }
        }
        else if (message.code === 451) {  // RECONNECTED (Usuario o rival)
            Renderer.hideNotification();
            Renderer.addLogEntry('Tu oponente se ha reconectado', 'success');
        }
    });
    
   
    API.on('error', (message) => {
        console.error('[HANDLERS] error del servidor:', message.message);
        Renderer.addLogEntry(`Error: ${message.message}`, 'error');
    });
}

function setupGlobalEventListeners() {
    // Desconexión del WebSocket
    document.addEventListener('websocket-disconnected', () => {
        console.log('[LISTENERS] WebSocket desconectado');
        
        // Si estás en juego o esperando algo, mostrar notificación Modal bloqueante
        if (GameState.currentScreen === GameState.SCREEN_GAME || 
            GameState.currentScreen === GameState.SCREEN_PLACEMENT ||
            GameState.currentScreen === GameState.SCREEN_WAITING_OPPONENT ||
            GameState.currentScreen === GameState.SCREEN_WAITING_PLACEMENT) {
            
            Renderer.showNotification(
                '⚠️ CONEXIÓN PERDIDA',
                'Se perdió la conexión con el servidor. Intentando reconectar automáticamente...',
                'ENTENDIDO',
                null,
                false  // No escapable
            );
            Renderer.addLogEntry('Conexión perdida con el servidor', 'error');
        }
    });
    
    // Reconexión del WebSocket
    document.addEventListener('websocket-reconnected', () => {
        console.log('[LISTENERS] WebSocket reconectado');
        // Cerrar automáticamente el modal de desconexión
        Renderer.hideNotification();
        Renderer.addLogEntry('Reconectado con el servidor', 'success');
    });
    
    // Sesión restaurada
    document.addEventListener('session-restored', async (e) => {
        const {playerId, sessionId} = e.detail;
        console.log('[LISTENERS] Sesión restaurada:', {playerId, sessionId});
        await handleSessionRestored();
    });
    
    // Sesión expirada
    document.addEventListener('session-expired', (e) => {
        const {reason} = e.detail;
        console.log('[LISTENERS] Sesión expirada:', reason);
        handleSessionExpired(reason);
    });
}


function setupStartScreen() {
    const nameInput = document.getElementById('player-name');
    const joinBtn = document.getElementById('btn-find-match');
    
    if (!nameInput || !joinBtn) {
        console.error('[SETUP] Elementos del inicio no encontrados');
        return;
    }
    
    nameInput.value = '';
    
    nameInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') handleJoinGame();
    });
    
    joinBtn.addEventListener('click', handleJoinGame);
}

async function handleJoinGame() {
    const nameInput = document.getElementById('player-name');
    const joinBtn = document.getElementById('btn-find-match');
    
    const playerName = nameInput.value.trim();
    
    if (playerName.length < 2) {
        showError('El nombre debe tener al menos 2 caracteres');
        return;
    }
    
    joinBtn.disabled = true;
    joinBtn.innerHTML = '<span>BUSCANDO...</span>';
    
    try {
        const result = await API.joinGame(playerName);
        console.log('[MAIN] joinGame resultado:', result);
        
        if (result.success) {
            if(result.state == 'WAITING_FOR_PLAYERS'){
                Renderer.showWaitingForOpponent(playerName);
            }
        } else {
            showError('Error al unirse a la partida');
            joinBtn.disabled = false;
            joinBtn.innerHTML = 'BUSCAR PARTIDA';
        }
    } catch (error) {
        showError(error.message);
        joinBtn.disabled = false;
        joinBtn.innerHTML = 'BUSCAR PARTIDA';
    }
}



function setupPlacementScreen() {
    console.log('[SETUP] Configurando pantalla de colocación');
    
    GameState.resetPlacement();
    
    // Renderizar
    Renderer.renderBoard('placement-board', GameState.boardSize, false);
    Renderer.renderShipsList(GameState.placement.ships);
    
    const playerNameEl = document.getElementById('placement-player-name');
    if (playerNameEl) playerNameEl.textContent = GameState.playerName;
    
    const board = document.getElementById('placement-board');
    const shipsList = document.getElementById('ships-list');
    const rotateBtn = document.getElementById('btn-rotate-ship');
    const randomBtn = document.getElementById('btn-random-placement');
    const confirmBtn = document.getElementById('btn-confirm-placement');
    
    if (!board || !shipsList) {
        console.error('[SETUP] Elementos de colocación no encontrados');
        return;
    }
    
    // Seleccionar barco
    shipsList.addEventListener('click', (e) => {
        const shipEl = e.target.closest('.ship-item');
        if (shipEl) {
            const shipId = shipEl.dataset.shipId;
            GameState.selectShip(shipId);
            document.querySelectorAll('.ship-item').forEach(s => s.classList.remove('selected'));
            shipEl.classList.add('selected');
        }
    });
    
    // Rotación
    if (rotateBtn) {
        rotateBtn.addEventListener('click', () => {
            GameState.rotateShip();
            Renderer.clearShipPreview('placement-board');
        });
    }
    
    // Preview
    board.addEventListener('mousemove', (e) => {
        const cell = e.target.closest('.cell');
        if (!cell) return;
        
        const selectedShip = GameState.getSelectedShip();
        if (!selectedShip) return;
        
        const x = parseInt(cell.dataset.x);
        const y = parseInt(cell.dataset.y);
        
        const positions = calculateShipPositions(
            x, y, selectedShip.length, GameState.placement.orientation
        );
        
        const isValid = API.isValidPlacement(
            positions, GameState.placement.placedShips, GameState.boardSize
        );
        
        Renderer.highlightShipPreview('placement-board', positions, isValid);
    });
    
    board.addEventListener('mouseleave', () => {
        Renderer.clearShipPreview('placement-board');
    });
    
    // Colocar barco
    board.addEventListener('click', (e) => {
        const cell = e.target.closest('.cell');
        if (!cell) return;
        
        const selectedShip = GameState.getSelectedShip();
        if (!selectedShip) {
            showError('Selecciona un barco primero');
            return;
        }
        
        const x = parseInt(cell.dataset.x);
        const y = parseInt(cell.dataset.y);
        
        const positions = calculateShipPositions(
            x, y, selectedShip.length, GameState.placement.orientation
        );
        
        if (!API.isValidPlacement(positions, GameState.placement.placedShips, GameState.boardSize)) {
            showWarning('No puedes colocar el barco ahí');
            return;
        }
        
        GameState.placeShip(selectedShip.id, positions);
        Renderer.placeShipOnBoard('placement-board', positions, selectedShip.type);
        Renderer.renderShipsList(GameState.placement.ships);
        
        GameState.selectShip(null);
        document.querySelectorAll('.ship-item').forEach(s => s.classList.remove('selected'));
        Renderer.clearShipPreview('placement-board');
    });
    
    // Posicionamiento aleatorio
    if (randomBtn) {
        const originalText = randomBtn.innerHTML;
        randomBtn.addEventListener('click', async () => {
            try {
                randomBtn.disabled = true;
                
                randomBtn.innerHTML = '<span>GENERANDO...</span>';
                
                const result = await API.generateRandomPlacement();
                
                if (result.success) {
                    Renderer.clearAllBoards();
                    GameState.resetPlacement();
                    
                    result.ships.forEach(ship => {
                        GameState.placement.placedShips.push(ship);
                        
                        const shipDef = GameState.placement.ships.find(s => s.type === ship.type);
                        if (shipDef) {
                            shipDef.placed = true;
                            shipDef.orientation = ship.orientation;
                        }
                        
                        Renderer.placeShipOnBoard('placement-board', ship.positions, ship.type);
                    });
                    
                    Renderer.renderShipsList(GameState.placement.ships);
                    
                    GameState.selectShip(null);
                    document.querySelectorAll('.ship-item').forEach(s => s.classList.remove('selected'));
                    Renderer.clearShipPreview('placement-board');
                    
                    showWarning(`✓ ${result.ships.length} barcos posicionados sin solapamientos`);
                }
            } catch (error) {
                showError(`Error generando disposición: ${error.message}`);
            } finally {
                randomBtn.disabled = false;
                randomBtn.innerHTML = originalText;
            }
        });
    }
    
    if (confirmBtn) {
        confirmBtn.addEventListener('click', handleConfirmPlacement);
    }
}

async function handleConfirmPlacement() {
    const confirmBtn = document.getElementById('btn-confirm-placement');
    
    if (!GameState.allShipsPlaced()) {
        showError('Debes colocar todos los barcos');
        return;
    }
    
    confirmBtn.disabled = true;
    confirmBtn.innerHTML = '<span>ENVIANDO...</span>';
    
    try {
        // Guardar barcos en localStorage para reconexión
        localStorage.setItem('placedShips', JSON.stringify(GameState.placement.placedShips));
        
        await API.submitShipPlacement(GameState.placement.placedShips);
        // El servidor responderá con game_state, que disparará el handler
    } catch (error) {
        showError(error.message);
        confirmBtn.disabled = false;
        confirmBtn.innerHTML = 'CONFIRMAR POSICIONAMIENTO';
    }
}


function setupGameScreen() {
    console.log('[SETUP] Configurando pantalla de juego');
    
    if (!GameState.game.defenseBoard || GameState.game.defenseBoard.length === 0) {
        GameState.game.defenseBoard = Array(GameState.boardSize).fill(null).map(() => 
            Array(GameState.boardSize).fill('empty')
        );
    }
    
    if (!GameState.game.attackBoard || GameState.game.attackBoard.length === 0) {
        GameState.game.attackBoard = Array(GameState.boardSize).fill(null).map(() => 
            Array(GameState.boardSize).fill('empty')
        );
    }
    
    Renderer.renderBoard('defense-board', GameState.boardSize, false);
    Renderer.renderBoard('attack-board', GameState.boardSize, true);
    
    const playerNameEl = document.getElementById('game-player-name');
    const opponentNameEl = document.getElementById('game-opponent-name');
    if (playerNameEl) playerNameEl.textContent = GameState.playerName;
    if (opponentNameEl) opponentNameEl.textContent = GameState.opponentName;
    
    GameState.placement.placedShips.forEach(ship => {
        Renderer.placeShipOnBoard('defense-board', ship.positions, ship.type);
    });
    
    const savedDefenseBoard = localStorage.getItem('defenseBoard');
    if (savedDefenseBoard) {
        try {
            GameState.game.defenseBoard = JSON.parse(savedDefenseBoard);
            for (let y = 0; y < GameState.boardSize; y++) {
                for (let x = 0; x < GameState.boardSize; x++) {
                    const cellState = GameState.game.defenseBoard[y][x];
                    if (cellState !== 'empty') {
                        Renderer.updateCell('defense-board', x, y, cellState);
                    }
                }
            }
        } catch (e) {
            console.warn('[SETUP] Error al restaurar defenseBoard:', e);
        }
    }
    
    const savedAttackBoard = localStorage.getItem('attackBoard');
    if (savedAttackBoard) {
        try {
            GameState.game.attackBoard = JSON.parse(savedAttackBoard);
            // Renderizar los ataques realizados
            for (let y = 0; y < GameState.boardSize; y++) {
                for (let x = 0; x < GameState.boardSize; x++) {
                    const cellState = GameState.game.attackBoard[y][x];
                    if (cellState !== 'empty') {
                        Renderer.updateCell('attack-board', x, y, cellState);
                    }
                }
            }
        } catch (e) {
            console.warn('[SETUP] Error al restaurar attackBoard:', e);
        }
    }
    
    const attackBoard = document.getElementById('attack-board');
    if (attackBoard) {
        attackBoard.replaceWith(attackBoard.cloneNode(true));
        const newAttackBoard = document.getElementById('attack-board');
        if (newAttackBoard) {
            newAttackBoard.addEventListener('click', handleAttackClick);
        }
    }
    
    //No implementado aun
    const surrenderBtn = document.getElementById('btn-surrender');
    if (surrenderBtn) {
        surrenderBtn.addEventListener('click', handleSurrender);
    }
    
    const combatLog = document.getElementById('combat-log');
    if (combatLog) {
        const savedLog = localStorage.getItem('combatLog');
        if (savedLog) {
            Renderer.loadCombatLog();
        } else {
            combatLog.innerHTML = '';
        }
    }
    
    Renderer.addLogEntry(' ¡Juego iniciado!', 'info');
    
    console.log('[SETUP] ✓ Pantalla de juego configurada');
}

async function handleAttackClick(e) {
    const cell = e.target.closest('.cell');
    if (!cell) return;
    
    
    const x = parseInt(cell.dataset.x);
    const y = parseInt(cell.dataset.y);
    
    // Evitar repetir ataque a la misma celda localmente
    if (cell.classList.contains('hit') || cell.classList.contains('miss') || cell.classList.contains('sunk')) {
        showWarning('Ya atacaste esa casilla');
        return;
    }
    
    const attackBoard = document.getElementById('attack-board');
    attackBoard.style.pointerEvents = 'none';
    
    try {
        const result = await API.sendAttack({x, y});
    } catch (error) {
        showError(error.message);
    } finally {
        attackBoard.style.pointerEvents = 'auto';
    }
}

//No implementado aun
async function handleSurrender() {
    if (!confirm('¿Estás seguro de que quieres rendirte? Perderás la partida.')) {
        return;
    }
    
    const surrenderBtn = document.getElementById('btn-surrender');
    surrenderBtn.disabled = true;
    surrenderBtn.innerHTML = '<span>ENVIANDO...</span>';
    
    try {
        await API.surrender();
    } catch (error) {
        showError(`Error en rendición: ${error.message}`);
        surrenderBtn.disabled = false;
        surrenderBtn.innerHTML = '<span>RENDIRSE</span>';
    }
}


function endGame(server_message) {
    const isVictory = server_message.winner === server_message.playerId;
    const stats = server_message.statistics || {};
    const reason = server_message.reason || 'normal';
    
    console.log('[MAIN] Fin de juego, victoria:', isVictory, ', razón:', reason);

    let notificationTitle = '¡JUEGO TERMINADO!';
    let notificationMsg = '';
    let pop_notification = true;
    
    switch(reason) {
        case 'surrender':
            notificationTitle = isVictory ? '¡VICTORIA!' : 'DERROTA';
            notificationMsg = isVictory ? 
                `${server_message.opponentName} se rindió. ¡Ganaste!` :
                `Te has rendido. ${server_message.opponentName} gana.`;
            break;
        case 'opponent_timeout':
            notificationTitle = '¡VICTORIA POR TIMEOUT!';
            notificationMsg = `Tu oponente no se reconectó a tiempo. ¡Ganaste por timeout!`;
            break;
        case 'reconnect_timeout':
            notificationTitle = 'DERROTA POR TIMEOUT';
            notificationMsg = `No te reconectaste a tiempo. Has perdido la partida.`;
            break;
        case 'opponent_disconnected':
            notificationTitle = isVictory ? '¡VICTORIA!' : 'DERROTA';
            notificationMsg = isVictory ?
                `${server_message.opponentName} se desconectó. Ganaste.` :
                `Te desconectaste. ${server_message.opponentName} gana.`;
            break;
        default: 
            pop_notification = false;
            showGameOverStats(server_message, isVictory, stats);

    }
    
    if (pop_notification) {
        Renderer.showNotification(
            notificationTitle,
            notificationMsg,
            escapable = false
        );
    }
}

function showGameOverStats(server_message, isVictory, stats) {
    localStorage.removeItem('playerId');
    localStorage.removeItem('sessionId');
    localStorage.removeItem('placedShips');
    localStorage.removeItem('combatLog');
    localStorage.removeItem('defenseBoard');
    localStorage.removeItem('attackBoard');
    sessionStorage.clear();

    GameState.switchScreen(GameState.SCREEN_GAMEOVER);

    const title         = document.getElementById('gameover-title');
    const subtitle      = document.getElementById('gameover-subtitle');
    const winnerName    = document.getElementById('winner-name');
    const totalMovesEl  = document.getElementById('total-moves');
    const accuracyEl    = document.getElementById('accuracy');
    const ships_remaining    = document.getElementById('ships-remaining');

    if (title) {
        title.textContent = isVictory ? '¡VICTORIA!' : 'DERROTA';
        title.className   = isVictory ? 'gameover-title victory' : 'gameover-title defeat';
    }

    if (subtitle) {
        subtitle.textContent = isVictory ?
            `¡Has hundido todos los barcos de ${server_message.opponentName}!` :
            `¡${server_message.opponentName} ha hundido todos tus barcos!`;
    }

    if (winnerName) {
        winnerName.textContent = isVictory ? server_message.playerName : server_message.opponentName;
    }

    if (totalMovesEl) {
        totalMovesEl.textContent = stats.total_moves != null ? stats.total_moves : '0';
    }
    if (accuracyEl) {
        const acc = typeof stats.accuracy === 'number' ? stats.accuracy : 0;
        accuracyEl.textContent = `${(acc * 100).toFixed(2)}%`;
    }
    if (ships_remaining) {
        // el objeto stats puede traer duration o no
        ships_remaining.textContent = stats.ships_remaining || 'Sin Sobrevivientes...';
    }

    Renderer.addLogEntry(
        isVictory ? '¡Ganaste la partida!' : 'Perdiste la partida',
        isVictory ? 'success' : 'danger'
    );

    const playAgainBtn = document.getElementById('btn-play-again');
    if (playAgainBtn) {
        playAgainBtn.onclick = () => {
            console.log('[MAIN] Jugando de nuevo...');
            GameState.clear();
            window.location.reload();
        };
    }

    const attackBoard = document.getElementById('attack-board');
    if (attackBoard) {
        attackBoard.style.pointerEvents = 'none';
        attackBoard.style.opacity        = '0.5';
    }

    setupGameOverScreen();
}

function setupGameOverScreen() {
    const playAgainBtn = document.getElementById('btn-play-again');
    if (playAgainBtn) {
        playAgainBtn.addEventListener('click', () => {
            GameState.clear();
            window.location.reload();
        });
    }
}

async function handleSessionRestored() {
    console.log('[MAIN] Restaurando sesión');
    Renderer.showReconnecting();
    
    try {
        // Enviar solicitud de reconexión
        // El servidor responderá con game_state code 231
        // El handler global se encargará de restaurar el estado
        const result = await API.reconnectGame(GameState.sessionId);
        if (result.success) {
            console.log('[MAIN] ✓ Reconexión completada, esperando handler global...');
            // El handler de game_state code 231 se encargará del resto
        }
    } catch (error) {
        console.error('[MAIN] Error reconectando:', error);
        // Limpiar TODO si la reconexión falla
        localStorage.removeItem('playerId');
        localStorage.removeItem('sessionId');
        localStorage.removeItem('placedShips');
        localStorage.removeItem('combatLog');
        localStorage.removeItem('defenseBoard');
        localStorage.removeItem('attackBoard');
        sessionStorage.clear();
        handleSessionExpired('reconnect_failed');
    }
}

/**
 * Restaura el estado del juego después de una reconexión exitosa (code 231)
 */
function restoreGameStateFromServer(message) {
    try {
        console.log('[MAIN] Restaurando estado completo desde servidor');
        
        // Guardar datos básicos
        if (message.playerName) GameState.playerName = message.playerName;
        if (message.opponentName) GameState.opponentName = message.opponentName;
        
        const serverState = message.state;
        
        // Actualizar estado del juego
        GameState.updateGameState(serverState.game_state);
        GameState.updateGameInfo({
            currentTurn: serverState.current_turn,
            yourId: serverState.your_id,
            opponentId: serverState.opponent_id,
            moveCount: serverState.move_count || 0,
            yourShipsRemaining: serverState.your_ships_sunk ? 
                (5 - serverState.your_ships_sunk) : 5,
            enemyShipsRemaining: serverState.opponent_ships_sunk ? 
                (5 - serverState.opponent_ships_sunk) : 5
        });
        
        // Restaurar barcos colocados desde localStorage
        const savedShips = localStorage.getItem('placedShips');
        if (savedShips) {
            try {
                GameState.placement.placedShips = JSON.parse(savedShips);
                console.log('[MAIN] ✓ Barcos restaurados desde localStorage:', GameState.placement.placedShips.length);
            } catch (e) {
                console.warn('[MAIN] Error al restaurar barcos:', e);
            }
        }
        
        // Restaurar tablero contrario si está disponible
        if (serverState.opponent_board) {
            console.log('[MAIN] Restaurando tablero contrario desde servidor');
            GameState.game.attackBoard = convertServerBoardToArray(
                serverState.opponent_board, 
                GameState.boardSize
            );
        }
        
        // Limpiar pantalla de reconexión
        Renderer.clearLoadingScreen();
        
        // Determinar pantalla apropiada según estado del juego
        switch(serverState.game_state) {
            case GameState.SERVER_STATE_PLACING_SHIPS:
                console.log('[MAIN] Restaurando a pantalla de colocación');
                GameState.switchScreen(GameState.SCREEN_PLACEMENT);
                setupPlacementScreen();
                
                // Restaurar barcos renderizados
                if (GameState.placement.placedShips.length > 0) {
                    GameState.placement.placedShips.forEach(ship => {
                        Renderer.placeShipOnBoard('placement-board', ship.positions, ship.type);
                        const shipDef = GameState.placement.ships.find(s => s.type === ship.type);
                        if (shipDef) shipDef.placed = true;
                    });
                    Renderer.renderShipsList(GameState.placement.ships);
                }
                break;
                
            case GameState.SERVER_STATE_IN_PROGRESS:
                console.log('[MAIN] Restaurando a pantalla de juego en progreso');
                GameState.switchScreen(GameState.SCREEN_GAME);
                setupGameScreen();
                
                // Restaurar estado de tablero de ataque renderizado
                if (GameState.game.attackBoard && GameState.game.attackBoard.length > 0) {
                    for (let y = 0; y < GameState.boardSize; y++) {
                        for (let x = 0; x < GameState.boardSize; x++) {
                            const cellState = GameState.game.attackBoard[y][x];
                            if (cellState !== 'empty') {
                                Renderer.updateCell('attack-board', x, y, cellState);
                            }
                        }
                    }
                }
                
                // Actualizar estado de turno
                if (serverState.current_turn === GameState.playerId) {
                    Renderer.enableAttackBoard(true);
                    Renderer.addLogEntry('¡Es tu turno!', 'success');
                } else {
                    Renderer.enableAttackBoard(false);
                    Renderer.showWaitingForOpponentTurn(GameState.opponentName);
                }
                break;
                
            case GameState.SERVER_STATE_FINISHED:
                console.log('[MAIN] Restaurando a pantalla de fin de juego');
                const isVictory = serverState.winner === GameState.playerId;
                endGame(isVictory, {
                    totalMoves: serverState.move_count,
                    accuracy: 0,
                    duration: '--:--'
                });
                break;
                
            default:
                console.warn('[MAIN] Estado desconocido:', serverState.game_state);
                GameState.switchScreen(GameState.SCREEN_GAME);
        }
        
        console.log('[MAIN] ✓ Estado restaurado exitosamente');
    } catch (error) {
        console.error('[MAIN] Error restaurando estado:', error);
        handleSessionExpired('restore_failed');
    }
}

/**
 * Convierte el formato de tablero del servidor al formato del cliente
 * El servidor envía: {Coordinate(x, y): 'empty'|'hit'|'miss'|'sunk'}
 * El cliente necesita: [][] siendo [y][x]
 */
function convertServerBoardToArray(serverBoard, boardSize = 10) {
    const boardArray = Array(boardSize).fill(null).map(() => 
        Array(boardSize).fill('empty')
    );
    
    // Iterar sobre las claves del objeto del servidor
    for (const key in serverBoard) {
        if (serverBoard.hasOwnProperty(key)) {
            const value = serverBoard[key];
            
            // Las claves tienen formato "Coordinate(x, y)"
            // Parsear la coordenada
            const match = key.match(/Coordinate\((\d+),\s*(\d+)\)/);
            if (match) {
                const x = parseInt(match[1], 10);
                const y = parseInt(match[2], 10);
                
                // Mapear valores del servidor al formato del cliente
                let cellState = 'empty';
                if (value === 'hit') cellState = 'hit';
                else if (value === 'miss') cellState = 'miss';
                else if (value === 'sunk') cellState = 'sunk';
                else if (value === 'ship') cellState = 'ship';
                
                boardArray[y][x] = cellState;
            }
        }
    }
    
    return boardArray;
}

function handleSessionExpired(reason) {
    console.log('[MAIN] Sesión expirada:', reason);
    GameState.clear();
    Renderer.clearLoadingScreen();
    
    const message = reason === 'reconnect_timeout' 
        ? 'No pudimos reconectar en el tiempo permitido. La partida fue cancelada.'
        : 'Tu sesión ha expirado.';
    
    Renderer.showNotification(
        'SESIÓN EXPIRADA',
        message,
        'RECARGAR',
        () => window.location.reload()
    );
}



function calculateShipPositions(startX, startY, length, orientation) {
    const positions = [];
    if (orientation === 'HORIZONTAL') {
        for (let i = 0; i < length; i++) {
            positions.push({x: startX + i, y: startY});
        }
    } else {
        for (let i = 0; i < length; i++) {
            positions.push({x: startX, y: startY + i});
        }
    }
    return positions;
}

function showError(message) {
    console.error('[UI]', message);
    const errorDiv = document.getElementById('error-message');
    if (errorDiv) {
        errorDiv.textContent = message;
        errorDiv.style.display = 'block';
        setTimeout(() => {
            errorDiv.style.display = 'none';
        }, 5000);
    }
}

function showWarning(message) {
    console.warn('[UI]', message);
    showError(message);
}

function showFatalError(message) {
    console.error('[FATAL]', message);
    Renderer.clearLoadingScreen();
    const container = document.body;
    const errorDiv = document.createElement('div');
    errorDiv.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(139, 0, 0, 0.9);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 10000;
        color: white;
        font-family: Arial, sans-serif;
        text-align: center;
    `;
    errorDiv.innerHTML = `
        <div style="max-width: 400px;">
            <h1>Error Fatal</h1>
            <p>${message}</p>
            <p style="margin-top: 20px; font-size: 14px;">La página se recargará automáticamente...</p>
        </div>
    `;
    container.appendChild(errorDiv);
    
    setTimeout(() => {
        window.location.reload();
    }, 5000);
}

console.log('[MAIN] Módulo main.js (REACTIVO) cargado');
