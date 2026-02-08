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
    updateCell(boardId, x, y, state) {
        const board = document.getElementById(boardId);
        if (!board) return;
        
        const cell = board.querySelector(`[data-x="${x}"][data-y="${y}"]`);
        if (!cell) return;
        
        // Remover estados anteriores
        cell.classList.remove('empty', 'ship', 'hit', 'miss', 'sunk');
        
        // Añadir nuevo estado
        cell.classList.add(state);
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
    placeShipOnBoard(boardId, positions) {
        positions.forEach(pos => {
            this.updateCell(boardId, pos.x, pos.y, 'ship');
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
        const duration = document.getElementById('game-duration');
        
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
     * Muestra/oculta el estado de carga
     */
    toggleLoading(show, message = 'Cargando...') {
        // Placeholder para futura implementación de loading screen
        console.log(show ? `Loading: ${message}` : 'Loading complete');
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
    }
};

// Exportar para uso en otros módulos
if (typeof module !== 'undefined' && module.exports) {
    module.exports = Renderer;
}
