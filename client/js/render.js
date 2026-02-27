/**
 * Módulo para renderizar elementos visuales del juego
 */

const Renderer = {
    
    /**
     * Renderiza un tablero de juego
     */
    renderBoard(containerId, size = 10, interactive = false) {
        const container = document.getElementById(containerId);
        if (!container) return;
        
        container.innerHTML = '';
        container.style.gridTemplateColumns = `repeat(${size}, 1fr)`;
        container.style.gridTemplateRows = `repeat(${size}, 1fr)`;
        
        // Crear celdas
        for (let y = 0; y < size; y++) {
            for (let x = 0; x < size; x++) {
                const cell = document.createElement('div');
                cell.className = 'cell';
                cell.dataset.x = x;
                cell.dataset.y = y;
                container.appendChild(cell);
            }
        }
        
        // Renderizar coordenadas
        this.renderCoordinates(container.parentElement, size);
    },
    
    /**
     * Renderiza las coordenadas del tablero (A-J, 1-10)
     */
    renderCoordinates(boardContainer, size = 10) {
        const coordsContainer = boardContainer.querySelector('.board-coordinates');
        if (!coordsContainer) return;
        
        const rowCoords = coordsContainer.querySelector('.coord-row');
        const colCoords = coordsContainer.querySelector('.coord-col');
        
        if (rowCoords) {
            rowCoords.innerHTML = '';
            for (let i = 0; i < size; i++) {
                const label = document.createElement('div');
                label.className = 'coord-label';
                label.textContent = String.fromCharCode(65 + i); // A, B, C...
                rowCoords.appendChild(label);
            }
        }
        
        if (colCoords) {
            colCoords.innerHTML = '';
            for (let i = 0; i < size; i++) {
                const label = document.createElement('div');
                label.className = 'coord-label';
                label.textContent = i + 1;
                colCoords.appendChild(label);
            }
        }
    },
    
    /**
     * Actualiza el estado de una celda específica
     */
    updateCell(boardId, x, y, state, shipType = null) {
        const board = document.getElementById(boardId);
        if (!board) return;
        
        const cell = board.querySelector(`[data-x="${x}"][data-y="${y}"]`);
        if (!cell) return;
        
        // Remover estados anteriores
        cell.classList.remove('empty', 'ship', 'hit', 'miss', 'sunk');
        
        // Remover clases de tipo de barco
        cell.classList.remove(
            'aircraft-carrier', 'battleship', 'cruiser', 'destroyer', 'submarine'
        );
        
        // Añadir nuevo estado
        cell.classList.add(state);
        
        // Si es un barco, añadir clase del tipo
        if (shipType && state === 'ship') {
            // Convertir AIRCRAFT_CARRIER a aircraft-carrier para la clase CSS
            const shipClass = shipType.toLowerCase().replace(/_/g, '-');
            cell.classList.add(shipClass);
        }
    },
    
    /**
     * Renderiza la lista de barcos para posicionamiento
     */
    renderShipsList(ships) {
        const container = document.getElementById('ships-list');
        if (!container) return;
        
        container.innerHTML = '';
        
        ships.forEach(ship => {
            const shipItem = document.createElement('div');
            shipItem.className = 'ship-item';
            shipItem.dataset.shipId = ship.id;
            
            // Agregar clase para colorear según el tipo de barco
            const shipTypeClass = ship.type.toLowerCase();
            shipItem.classList.add(shipTypeClass);
            
            if (ship.placed) {
                shipItem.classList.add('placed');
            }
            
            // Icono del barco (segmentos)
            const shipIcon = document.createElement('div');
            shipIcon.className = 'ship-icon';
            for (let i = 0; i < ship.length; i++) {
                const segment = document.createElement('div');
                segment.className = 'ship-segment';
                shipIcon.appendChild(segment);
            }
            
            // Información del barco
            const shipInfo = document.createElement('div');
            shipInfo.className = 'ship-info';
            shipInfo.innerHTML = `
                <div class="ship-name">${ship.name}</div>
                <div class="ship-length">${ship.length} casillas</div>
            `;
            
            shipItem.appendChild(shipIcon);
            shipItem.appendChild(shipInfo);
            container.appendChild(shipItem);
        });
    },
    
    /**
     * Resalta las posiciones donde se colocaría un barco
     */
    highlightShipPreview(boardId, positions, valid = true) {
        const board = document.getElementById(boardId);
        if (!board) return;
        
        // Limpiar preview anterior
        board.querySelectorAll('.cell').forEach(cell => {
            cell.style.backgroundColor = '';
            cell.style.borderColor = '';
        });
        
        // Mostrar nuevo preview
        positions.forEach(pos => {
            const cell = board.querySelector(`[data-x="${pos.x}"][data-y="${pos.y}"]`);
            if (cell) {
                if (valid) {
                    cell.style.backgroundColor = 'rgba(6, 255, 165, 0.3)';
                    cell.style.borderColor = 'var(--sonar-green)';
                } else {
                    cell.style.backgroundColor = 'rgba(230, 57, 70, 0.3)';
                    cell.style.borderColor = 'var(--danger-red)';
                }
            }
        });
    },
    
    /**
     * Limpia el preview de posicionamiento de barco
     */
    clearShipPreview(boardId) {
        const board = document.getElementById(boardId);
        if (!board) return;
        
        board.querySelectorAll('.cell').forEach(cell => {
            if (!cell.classList.contains('ship')) {
                cell.style.backgroundColor = '';
                cell.style.borderColor = '';
            }
        });
    },
    
    /**
     * Coloca un barco en el tablero visualmente
     */
    placeShipOnBoard(boardId, positions, shipType = null) {
        positions.forEach(pos => {
            this.updateCell(boardId, pos.x, pos.y, 'ship', shipType);
        });
    },
    
    /**
     * Añade una entrada al log de combate
     */
    addLogEntry(message, type = 'info') {
        const logContainer = document.getElementById('combat-log');
        if (!logContainer) return;
        
        const entry = document.createElement('div');
        entry.className = `log-entry ${type}`;
        entry.textContent = message;
        
        logContainer.appendChild(entry);
        logContainer.scrollTop = logContainer.scrollHeight;
        
        // Guardar en localStorage
        this.saveCombatLog();
    },
    
    /**
     * Carga el log de combate desde localStorage
     */
    loadCombatLog() {
        const savedLog = localStorage.getItem('combatLog');
        if (!savedLog) return;
        
        try {
            const logEntries = JSON.parse(savedLog);
            const logContainer = document.getElementById('combat-log');
            if (!logContainer) return;
            
            logContainer.innerHTML = '';
            
            logEntries.forEach(entry => {
                const div = document.createElement('div');
                div.className = `log-entry ${entry.type}`;
                div.textContent = entry.message;
                logContainer.appendChild(div);
            });
            
            logContainer.scrollTop = logContainer.scrollHeight;
        } catch (error) {
            console.error('[Renderer] Error cargando log:', error);
        }
    },
    
    /**
     * Guarda el log de combate en localStorage
     */
    saveCombatLog() {
        const logContainer = document.getElementById('combat-log');
        if (!logContainer) return;
        
        const entries = [];
        logContainer.querySelectorAll('.log-entry').forEach(entry => {
            const typeMatch = entry.className.match(/log-entry (\w+)/);
            const type = typeMatch ? typeMatch[1] : 'info';
            entries.push({
                message: entry.textContent,
                type: type
            });
        });
        
        localStorage.setItem('combatLog', JSON.stringify(entries));
    },
    
    /**
     * Limpia el log de combate en localStorage
     */
    clearCombatLog() {
        localStorage.removeItem('combatLog');
    },
    
    /**
     * Actualiza la información del turno actual
     */
    updateTurnInfo(playerName, isYourTurn) {
        const turnElement = document.getElementById('current-turn');
        if (turnElement) {
            turnElement.textContent = isYourTurn ? 'TU TURNO' : playerName;
            turnElement.style.color = isYourTurn ? 'var(--sonar-green)' : 'var(--warning-orange)';
        }
    },
    
    /**
     * Actualiza el contador de movimientos
     */
    updateMoveCount(count) {
        const moveElement = document.getElementById('move-count');
        if (moveElement) {
            moveElement.textContent = count;
        }
    },
    
    /**
     * Actualiza los barcos restantes
     */
    updateShipsRemaining(yourShips, enemyShips) {
        const yourElement = document.getElementById('your-ships-remaining');
        const enemyElement = document.getElementById('enemy-ships-remaining');
        
        if (yourElement) yourElement.textContent = yourShips;
        if (enemyElement) enemyElement.textContent = enemyShips;
    },
    
    /**
     * Renderiza la pantalla de fin de juego
     */
    renderGameOver(winner, loser, stats) {
        const title = document.getElementById('gameover-title');
        const subtitle = document.getElementById('gameover-subtitle');
        const winnerName = document.getElementById('winner-name');
        const totalMoves = document.getElementById('total-moves');
        const accuracy = document.getElementById('accuracy');
        const duration = document.getElementById('ships-remaining');
        
        const isVictory = winner === GameState.playerName;
        
        if (title) {
            title.textContent = isVictory ? 'VICTORIA' : 'DERROTA';
            title.className = isVictory ? 'gameover-title' : 'gameover-title defeat';
        }
        
        if (subtitle) {
            subtitle.textContent = isVictory ? 'MISIÓN COMPLETADA' : 'MISIÓN FALLIDA';
        }
        
        if (winnerName) winnerName.textContent = winner;
        if (totalMoves) totalMoves.textContent = stats.totalMoves || 0;
        if (accuracy) accuracy.textContent = `${stats.accuracy || 0}%`;
        if (duration) duration.textContent = stats.duration || '--:--';
    },
    
    /**
     * Actualiza el nombre del jugador en pantallas
     */
    updatePlayerName(name) {
        const elements = document.querySelectorAll('#placement-player-name');
        elements.forEach(el => {
            el.textContent = name;
        });
    },
    
    /**
     * Animación de ataque en celda
     */
    animateAttack(boardId, x, y, isHit) {
        const board = document.getElementById(boardId);
        if (!board) return;
        
        const cell = board.querySelector(`[data-x="${x}"][data-y="${y}"]`);
        if (!cell) return;
        
        // Crear efecto de impacto
        const impact = document.createElement('div');
        impact.style.position = 'absolute';
        impact.style.inset = '0';
        impact.style.backgroundColor = isHit ? 'var(--danger-red)' : 'var(--ocean-medium)';
        impact.style.opacity = '0.8';
        impact.style.animation = 'hitPulse 0.5s ease';
        
        cell.style.position = 'relative';
        cell.appendChild(impact);
        
        setTimeout(() => {
            impact.remove();
        }, 30);
    },
    
    
    /**
     * Muestra pantalla de conexión
     */
    showConnecting() {
        console.log('[RENDER] Mostrando pantalla de conexión');
        this.clearLoadingScreen();
        const loading = this._createLoadingScreen(
            'Conectando...',
            'Estableciendo conexión con el servidor'
        );
        document.body.appendChild(loading);
    },
    
    /**
     * Muestra pantalla de espera de oponente
     */
    showWaitingForOpponent(playerName) {
        console.log('[RENDER] Esperando oponente...');
        this.clearLoadingScreen();
        const loading = this._createLoadingScreen(
            'Esperando oponente...',
            `Hola ${playerName}, esperando a que otro jugador se una a la partida`
        );
        document.body.appendChild(loading);
    },
    
    /**
     * Muestra pantalla de espera de posicionamiento
     */
    showWaitingForShipPlacement() {
        console.log('[RENDER] Esperando posicionamiento del oponente');
        this.clearLoadingScreen();
        const loading = this._createLoadingScreen(
            'Esperando posicionamiento...',
            'Tu oponente está colocando sus barcos'
        );
        document.body.appendChild(loading);
    },
    
    /**
     * Muestra pantalla de espera de turno del oponente
     */
    showWaitingForOpponentTurn(opponentName) {
        console.log('[RENDER] Turno del oponente');
        this.clearLoadingScreen();
        const loading = this._createLoadingScreen(
            'Turno del oponente',
            `Aguardando movimiento de ${opponentName}...`
        );
        document.body.appendChild(loading);
    },
    
    /**
     * Muestra pantalla de reconexión
     */
    showReconnecting() {
        console.log('[RENDER] Reconectando...');
        this.clearLoadingScreen();
        const loading = this._createLoadingScreen(
            'Reconectando...',
            'Reestableciendo conexión con el servidor'
        );
        document.body.appendChild(loading);
    },
    
    /**
     * Muestra pantalla de desconexión
     */
    showDisconnected() {
        console.log('[RENDER] ❌ Desconectado');
        this.clearLoadingScreen();
        const loading = this._createLoadingScreen(
            '❌ Desconectado',
            'Se perdió la conexión del servidor. Reconectando automáticamente...',
            true
        );
        document.body.appendChild(loading);
    },
    
    /**
     * Crea elemento de pantalla de carga
     */
    _createLoadingScreen(title, message, isError = false) {
        const container = document.createElement('div');
        container.id = 'loading-screen';
        container.className = isError ? 'loading-screen error' : 'loading-screen';
        
        const content = document.createElement('div');
        content.className = 'loading-content';
        
        const titleEl = document.createElement('h2');
        titleEl.textContent = title;
        
        const messageEl = document.createElement('p');
        messageEl.textContent = message;
        
        const spinner = document.createElement('div');
        spinner.className = 'loading-spinner';
        
        content.appendChild(spinner);
        content.appendChild(titleEl);
        content.appendChild(messageEl);
        container.appendChild(content);
        
        return container;
    },
    
    /**
     * Limpia la pantalla de carga
     */
    clearLoadingScreen() {
        const loadingScreen = document.getElementById('loading-screen');
        if (loadingScreen) {
            console.log('[RENDER] Limpiando pantalla de carga');
            loadingScreen.remove();
        }
    },
    
    /**
     * Muestra/oculta el estado de carga
     */
    toggleLoading(show, message = 'Cargando...') {
        if (show) {
            this.showConnecting();
        } else {
            this.clearLoadingScreen();
        }
    },
    
    /**
     * Limpia todos los tableros
     */
    clearAllBoards() {
        ['placement-board', 'defense-board', 'attack-board'].forEach(boardId => {
            const board = document.getElementById(boardId);
            if (board) {
                board.querySelectorAll('.cell').forEach(cell => {
                    cell.className = 'cell';
                    cell.style.backgroundColor = '';
                    cell.style.borderColor = '';
                });
            }
        });
    },
    
    /**
     * Habilita/deshabilita el tablero de ataque
     * Client reactivo: solo renderiza, nunca decide lógica
     */
    enableAttackBoard(enabled) {
        const board = document.getElementById('attack-board');
        if (board) {
            board.style.pointerEvents = enabled ? 'auto' : 'none';
            board.style.opacity = enabled ? '1' : '0.5';
            
            const turnEl = document.getElementById('current-turn');
            if (turnEl) {
                if (enabled) {
                    turnEl.textContent = '¡Es tu turno!';
                    turnEl.style.color = '#4CAF50';
                } else {
                    turnEl.textContent = 'Esperando turno...';
                    turnEl.style.color = '#FF9800';
                }
            }
        }
    },

    /**
     * Muestra pantalla de espera durante colocación de barcos
     */
    showWaitingForShipPlacement() {
        console.log('[RENDER] Mostrando pantalla de espera de barcos');
        this.clearLoadingScreen();
        const loading = this._createLoadingScreen(
            'Esperando al oponente...',
            'Tu oponente está colocando sus barcos'
        );
        document.body.appendChild(loading);
    },
    
    /**
     * Muestra pantalla de espera del turno del oponente
     */
    showWaitingForOpponentTurn(opponentName) {
        const turnEl = document.getElementById('current-turn');
        if (turnEl) {
            turnEl.textContent = `Turno de ${opponentName}`;
            turnEl.style.color = '#FF9800';
        }
        Renderer.enableAttackBoard(false);
    },
    
    /**
     * Muestra una notificación modal
     */
    showNotification(title, message, actionText = null, actionCallback = null, escapable = false) {
        const modal = document.getElementById('notification-modal');
        const titleEl = document.getElementById('modal-title');
        const messageEl = document.getElementById('modal-message');
        const closeBtn = document.getElementById('modal-btn-close');
        const actionBtn = document.getElementById('modal-btn-action');
        const actionBtnText = document.getElementById('modal-btn-action-text');
        
        if (!modal) return;
        
        // Configurar contenido
        titleEl.textContent = title;
        messageEl.textContent = message;
        
        // Limpiar listeners anteriores
        closeBtn.replaceWith(closeBtn.cloneNode(true));
        actionBtn.replaceWith(actionBtn.cloneNode(true));
        
        const newCloseBtn = document.getElementById('modal-btn-close');
        const newActionBtn = document.getElementById('modal-btn-action');
        
        // Si NO es escapable, ocultar el botón cerrar
        if (!escapable) {
            newCloseBtn.style.display = 'none';
        } else {
            newCloseBtn.style.display = 'block';
            // Cerrar modal
            newCloseBtn.addEventListener('click', () => {
                this.hideNotification();
            });
        }
        
        // Botón de acción (si existe)
        if (actionText && actionCallback) {
            actionBtnText.textContent = actionText;
            newActionBtn.style.display = 'block';
            newActionBtn.addEventListener('click', () => {
                if (escapable) {
                    this.hideNotification();
                }
                actionCallback();
            });
        } else {
            newActionBtn.style.display = 'none';
        }
        
        // Mostrar modal
        modal.classList.remove('hidden');
    },
    
    /**
     * Oculta la notificación modal
     */
    hideNotification() {
        const modal = document.getElementById('notification-modal');
        if (modal) {
            modal.classList.add('hidden');
        }
    },
    
    /**
     * Actualiza el contador de movimientos
     */
    updateMoveCount(count) {
        const moveCountEl = document.getElementById('move-count');
        if (moveCountEl) {
            moveCountEl.textContent = count;
        }
    },
    
    /**
     * Actualiza los contadores de barcos restantes
     */
    updateShipsRemaining(yourShips, enemyShips) {
        const yourEl = document.getElementById('your-ships-remaining');
        const enemyEl = document.getElementById('enemy-ships-remaining');
        
        if (yourEl) {
            yourEl.textContent = yourShips;
            // Cambiar color si quedan pocos
            if (yourShips <= 2) {
                yourEl.style.color = 'var(--danger-red)';
            } else if (yourShips <= 4) {
                yourEl.style.color = 'var(--warning-orange)';
            } else {
                yourEl.style.color = 'var(--sonar-green)';
            }
        }
        
        if (enemyEl) {
            enemyEl.textContent = enemyShips;
            // Cambiar color si quedan pocos
            if (enemyShips <= 2) {
                enemyEl.style.color = 'var(--sonar-green)';
            } else if (enemyShips <= 4) {
                enemyEl.style.color = 'var(--warning-orange)';
            } else {
                enemyEl.style.color = 'var(--neutral-gray)';
            }
        }
    }
};

// Exportar para uso en otros módulos
if (typeof module !== 'undefined' && module.exports) {
    module.exports = Renderer;
}
