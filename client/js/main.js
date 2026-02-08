/**
 * Módulo principal del juego - Inicialización y manejo de eventos
 */

document.addEventListener('DOMContentLoaded', () => {
    initializeGame();
});

/**
 * Inicializa el juego y todos sus componentes
 */
function initializeGame() {
    console.log('Iniciando Batalla Naval...');
    
    // Configurar eventos de la pantalla de inicio
    setupStartScreen();
    
    // Configurar eventos de la pantalla de posicionamiento
    setupPlacementScreen();
    
    // Configurar eventos de la pantalla de juego
    setupGameScreen();
    
    // Configurar eventos de la pantalla de fin de juego
    setupGameOverScreen();
}

/**
 * Configura eventos de la pantalla de inicio
 */
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
                findMatchBtn.click();
            }
        });
    }
    
    if (findMatchBtn) {
        findMatchBtn.addEventListener('click', async () => {
            const name = nameInput.value.trim();
            if (name.length < 2) {
                alert('Por favor ingresa un nombre válido (mínimo 2 caracteres)');
                return;
            }
            
            GameState.setPlayerName(name);
            
            // Simular búsqueda de partida
            findMatchBtn.disabled = true;
            findMatchBtn.innerHTML = '<span class="btn-text">BUSCANDO...</span>';
            
            try {
                await API.findMatch(name);
                
                // Cambiar a pantalla de posicionamiento
                GameState.switchScreen('placement');
                Renderer.updatePlayerName(name);
                setupPlacementBoard();
                Renderer.renderShipsList(GameState.placement.ships);
            } catch (error) {
                console.error('Error al buscar partida:', error);
                alert('Error al buscar partida. Intenta de nuevo.');
            } finally {
                findMatchBtn.disabled = false;
                findMatchBtn.innerHTML = '<span class="btn-text">INICIAR BÚSQUEDA</span><span class="btn-icon">▶</span>';
            }
        });
    }
}

/**
 * Configura la pantalla de posicionamiento
 */
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

/**
 * Configura el tablero de posicionamiento
 */
function setupPlacementBoard() {
    Renderer.renderBoard('placement-board', GameState.boardSize, false);
    
    const board = document.getElementById('placement-board');
    const shipsList = document.getElementById('ships-list');
    
    // Eventos para seleccionar barcos
    if (shipsList) {
        shipsList.addEventListener('click', (e) => {
            const shipItem = e.target.closest('.ship-item');
            if (!shipItem || shipItem.classList.contains('placed')) return;
            
            const shipId = shipItem.dataset.shipId;
            
            // Deseleccionar otros barcos
            shipsList.querySelectorAll('.ship-item').forEach(item => {
                item.classList.remove('selected');
            });
            
            // Seleccionar este barco
            shipItem.classList.add('selected');
            GameState.selectShip(shipId);
            
            // Habilitar botón de rotar
            const rotateBtn = document.getElementById('btn-rotate-ship');
            if (rotateBtn) rotateBtn.disabled = false;
        });
    }
    
    // Eventos del tablero para posicionar barcos
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
                // Colocar el barco
                GameState.placeShip(ship.id, positions);
                Renderer.placeShipOnBoard('placement-board', positions);
                Renderer.renderShipsList(GameState.placement.ships);
                Renderer.clearShipPreview('placement-board');
                
                // Deseleccionar el barco
                GameState.selectShip(null);
                document.querySelectorAll('.ship-item').forEach(item => {
                    item.classList.remove('selected');
                });
                
                // Deshabilitar botón de rotar
                const rotateBtn = document.getElementById('btn-rotate-ship');
                if (rotateBtn) rotateBtn.disabled = true;
                
                // Verificar si todos los barcos están colocados
                if (GameState.allShipsPlaced()) {
                    const confirmBtn = document.getElementById('btn-confirm-placement');
                    if (confirmBtn) confirmBtn.disabled = false;
                }
            }
        });
    }
}

/**
 * Calcula las posiciones de un barco según su punto de inicio, longitud y orientación
 */
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
 * Maneja el posicionamiento aleatorio de barcos
 */
async function handleRandomPlacement() {
    const randomBtn = document.getElementById('btn-random-placement');
    if (!randomBtn) return;
    
    randomBtn.disabled = true;
    randomBtn.innerHTML = '<span>GENERANDO...</span>';
    
    try {
        // Limpiar posicionamiento anterior
        GameState.resetPlacement();
        Renderer.clearAllBoards();
        setupPlacementBoard();
        
        // Generar posicionamiento aleatorio
        const result = await API.generateRandomPlacement(GameState.boardSize);
        
        if (result.success) {
            // Colocar cada barco
            result.ships.forEach(ship => {
                const shipData = GameState.placement.ships.find(s => s.id === ship.id);
                if (shipData) {
                    GameState.placeShip(ship.id, ship.positions);
                    Renderer.placeShipOnBoard('placement-board', ship.positions);
                }
            });
            
            Renderer.renderShipsList(GameState.placement.ships);
            
            // Habilitar botón de confirmar
            const confirmBtn = document.getElementById('btn-confirm-placement');
            if (confirmBtn) confirmBtn.disabled = false;
        }
    } catch (error) {
        console.error('Error al generar posicionamiento aleatorio:', error);
        alert('Error al generar posicionamiento. Intenta de nuevo.');
    } finally {
        randomBtn.disabled = false;
        randomBtn.innerHTML = '<span>ALEATORIO</span>';
    }
}

/**
 * Maneja la rotación del barco seleccionado
 */
function handleRotateShip() {
    GameState.rotateShip();
    console.log(`Orientación cambiada a: ${GameState.placement.orientation}`);
}

/**
 * Maneja la confirmación del posicionamiento
 */
async function handleConfirmPlacement() {
    const confirmBtn = document.getElementById('btn-confirm-placement');
    if (!confirmBtn) return;
    
    confirmBtn.disabled = true;
    confirmBtn.innerHTML = '<span>CONFIRMANDO...</span>';
    
    try {
        await API.submitShipPlacement('match_id', GameState.placement.placedShips);
        
        // Cambiar a pantalla de juego
        GameState.switchScreen('game');
        setupGameBoards();
        GameState.startGameTimer();
        
        // Inicializar información del juego
        Renderer.updateTurnInfo(GameState.playerName, true);
        Renderer.updateMoveCount(0);
        Renderer.updateShipsRemaining(5, 5);
    } catch (error) {
        console.error('Error al confirmar posicionamiento:', error);
        alert('Error al confirmar posicionamiento. Intenta de nuevo.');
    } finally {
        confirmBtn.disabled = false;
        confirmBtn.innerHTML = '<span>CONFIRMAR DISPOSICIÓN</span>';
    }
}

/**
 * Configura los tableros de juego
 */
function setupGameBoards() {
    // Renderizar tableros
    Renderer.renderBoard('defense-board', GameState.boardSize, false);
    Renderer.renderBoard('attack-board', GameState.boardSize, true);
    
    // Inicializar estados de tableros
    GameState.initDefenseBoard();
    GameState.initAttackBoard();
    
    // Mostrar barcos en tablero de defensa
    GameState.placement.placedShips.forEach(ship => {
        ship.positions.forEach(pos => {
            Renderer.updateCell('defense-board', pos.x, pos.y, 'ship');
        });
    });
    
    // Configurar eventos del tablero de ataque
    const attackBoard = document.getElementById('attack-board');
    if (attackBoard) {
        attackBoard.addEventListener('click', handleAttackCell);
    }
}

/**
 * Configura la pantalla de juego
 */
function setupGameScreen() {
    // Los eventos se configuran dinámicamente cuando se entra a la pantalla
}

/**
 * Maneja el ataque a una celda
 */
async function handleAttackCell(e) {
    const cell = e.target.closest('.cell');
    if (!cell) return;
    
    // Verificar si ya fue atacada
    if (cell.classList.contains('hit') || cell.classList.contains('miss')) {
        return;
    }
    
    const x = parseInt(cell.dataset.x);
    const y = parseInt(cell.dataset.y);
    const coordinate = API.formatCoordinate(x, y);
    
    // Deshabilitar tablero temporalmente
    const attackBoard = document.getElementById('attack-board');
    attackBoard.style.pointerEvents = 'none';
    
    try {
        const result = await API.sendAttack('match_id', coordinate);
        
        if (result.success) {
            // Actualizar celda según resultado
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
                
                // Actualizar contador de barcos enemigos
                GameState.game.enemyShipsRemaining--;
                Renderer.updateShipsRemaining(
                    GameState.game.yourShipsRemaining,
                    GameState.game.enemyShipsRemaining
                );
            }
            
            Renderer.updateCell('attack-board', x, y, cellState);
            Renderer.animateAttack('attack-board', x, y, cellState !== 'miss');
            
            // Actualizar log y contador
            GameState.addCombatLog(logMessage, logType);
            Renderer.addLogEntry(logMessage, logType);
            
            GameState.game.moveCount++;
            Renderer.updateMoveCount(GameState.game.moveCount);
            
            // Verificar fin del juego
            if (result.gameFinished) {
                setTimeout(() => {
                    endGame(true);
                }, 1500);
            }
        }
    } catch (error) {
        console.error('Error al enviar ataque:', error);
        Renderer.addLogEntry('Error al enviar ataque', 'error');
    } finally {
        attackBoard.style.pointerEvents = 'auto';
    }
}

/**
 * Configura la pantalla de fin de juego
 */
function setupGameOverScreen() {
    const playAgainBtn = document.getElementById('btn-play-again');
    
    if (playAgainBtn) {
        playAgainBtn.addEventListener('click', () => {
            // Reiniciar el juego
            GameState.reset();
            Renderer.clearAllBoards();
            GameState.switchScreen('start');
            
            // Limpiar input de nombre
            const nameInput = document.getElementById('player-name');
            if (nameInput) nameInput.value = '';
        });
    }
}

/**
 * Finaliza el juego y muestra estadísticas
 */
function endGame(isVictory) {
    GameState.stopGameTimer();
    
    const winner = isVictory ? GameState.playerName : 'Oponente';
    const loser = isVictory ? 'Oponente' : GameState.playerName;
    
    // Calcular precisión (hits / total de ataques)
    const totalAttacks = GameState.game.moveCount;
    const hits = 5 * 5 - GameState.game.enemyShipsRemaining * 3; // Estimación
    const accuracy = totalAttacks > 0 ? Math.round((hits / totalAttacks) * 100) : 0;
    
    const stats = {
        totalMoves: GameState.game.moveCount,
        accuracy: accuracy,
        duration: GameState.getGameDuration()
    };
    
    Renderer.renderGameOver(winner, loser, stats);
    GameState.switchScreen('gameover');
}

/**
 * Utilidad: Convierte número a letra (0 -> A, 1 -> B, etc.)
 */
function numberToLetter(num) {
    return String.fromCharCode(65 + num);
}

// Exportar funciones para debugging
window.GameDebug = {
    state: GameState,
    renderer: Renderer,
    api: API,
    endGame: endGame
};

console.log('Batalla Naval inicializado correctamente');
