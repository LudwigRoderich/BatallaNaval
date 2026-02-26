/**
 * Módulo para gestionar el estado de la interfaz y sesión del juego
 */

const GameState = {
    // ============================================================
    // CONSTANTES DE ESTADO
    // ============================================================
    
    // Estados de pantalla
    SCREEN_START: 'start',
    SCREEN_PLACEMENT: 'placement',
    SCREEN_GAME: 'game',
    SCREEN_GAMEOVER: 'gameover',
    SCREEN_CONNECTING: 'connecting',
    SCREEN_WAITING_OPPONENT: 'waiting_opponent',
    SCREEN_WAITING_PLACEMENT: 'waiting_placement',
    SCREEN_WAITING_TURN: 'waiting_turn',
    SCREEN_RECONNECTING: 'reconnecting',
    
    // Estados del servidor
    SERVER_STATE_WAITING_FOR_PLAYERS: 'WAITING_FOR_PLAYERS',
    SERVER_STATE_PLACING_SHIPS: 'PLACING_SHIPS',
    SERVER_STATE_IN_PROGRESS: 'IN_PROGRESS',
    SERVER_STATE_FINISHED: 'FINISHED',
    
    // ============================================================
    // ESTADO PERSISTENT (localStorage)
    // ============================================================
    
    // IDs de sesión (DEBE estar en localStorage)
    get playerId() {
        return localStorage.getItem('playerId');
    },
    set playerId(value) {
        if (value) localStorage.setItem('playerId', value);
        else localStorage.removeItem('playerId');
    },
    
    get sessionId() {
        return localStorage.getItem('sessionId');
    },
    set sessionId(value) {
        if (value) localStorage.setItem('sessionId', value);
        else localStorage.removeItem('sessionId');
    },
    
    // ============================================================
    // ESTADO SESSION (sessionStorage)
    // ============================================================
    
    // Pantalla actual
    get currentScreen() {
        return sessionStorage.getItem('currentScreen') || this.SCREEN_START;
    },
    set currentScreen(value) {
        sessionStorage.setItem('currentScreen', value);
    },
    
    // Game state del servidor
    get gameState() {
        return sessionStorage.getItem('gameState') || this.SERVER_STATE_WAITING_FOR_PLAYERS;
    },
    set gameState(value) {
        sessionStorage.setItem('gameState', value);
    },
    
    // Datos del jugador
    get playerName() {
        return sessionStorage.getItem('playerName') || 'Comandante';
    },
    set playerName(value) {
        sessionStorage.setItem('playerName', value);
    },
    
    get opponentName() {
        return sessionStorage.getItem('opponentName') || '';
    },
    set opponentName(value) {
        sessionStorage.setItem('opponentName', value);
    },
    
    boardSize: 10,
    
    // ============================================================
    // DATOS EN MEMORIA (session)
    // ============================================================
    
    // Posicionamiento de barcos
    placement: {
        selectedShip: null,
        orientation: 'HORIZONTAL',
        placedShips: [],
        ships: [
            { id: 'carrier', name: 'Portaaviones', type: 'AIRCRAFT_CARRIER', length: 5, placed: false, orientation: 'HORIZONTAL'},
            { id: 'battleship', name: 'Acorazado', type: 'BATTLESHIP', length: 4, placed: false, orientation: 'HORIZONTAL' },
            { id: 'cruiser', name: 'Crucero', type: 'CRUISER', length: 3, placed: false, orientation: 'HORIZONTAL' },
            { id: 'destroyer', name: 'Destructor', type: 'DESTROYER', length: 3, placed: false, orientation: 'HORIZONTAL' },
            { id: 'submarine', name: 'Submarino', type: 'SUBMARINE', length: 2, placed: false, orientation: 'HORIZONTAL' }
        ]
    },
    
    // Estado del juego actual
    game: {
        currentTurn: '',
        yourId: '',
        opponentId: '',
        moveCount: 0,
        yourShipsRemaining: 5,
        enemyShipsRemaining: 5,
        defenseBoard: [],
        attackBoard: [],
        combatLog: []
    },
    
    //Temporizador de juego
    gameTimer: {
        startTime: null,
        endTime: null
    },
    
    // ============================================================
    // MÉTODOS PRINCIPALES
    // ============================================================
    
    /**
     * Inicializa el estado del juego
     * Se ejecuta una sola vez al cargar la aplicación
     */
    init() {
        console.log('[GameState] Inicializando estado...');
        
        // Limpiar datos de sesión
        sessionStorage.clear();
        
        // Verificar si hay sesión guardada en localStorage
        if (this.playerId && this.sessionId) {
            console.log('[GameState] ✓ Sesión guardada encontrada');
            // No limpiar localStorage!
        } else {
            // Nueva sesión
            localStorage.clear();
        }
        
        // Inicializar estado de sesión
        this.currentScreen = this.SCREEN_START;
        this.playerName = '';
        this.opponentName = '';
        this.gameState = this.SERVER_STATE_WAITING_FOR_PLAYERS;
        
        // Resetear posicionamiento
        this.resetPlacement();
        
        // Reiniciar juego
        this.game = {
            currentTurn: '',
            yourId: '',
            opponentId: '',
            moveCount: 0,
            yourShipsRemaining: 5,
            enemyShipsRemaining: 5,
            defenseBoard: [],
            attackBoard: [],
            combatLog: []
        };
        
        // Reiniciar temporizador
        this.gameTimer = {
            startTime: null,
            endTime: null
        };
        
        console.log('[GameState] ✓ Estado inicializado');
    },
    
    /**
     * Limpia todos los datos (logout)
     */
    clear() {
        console.log('[GameState] Limpiando estado...');
        localStorage.clear();
        sessionStorage.clear();
        this.init();
    },
    
    /**
     * Cambia a una pantalla específica
     */
    switchScreen(screenName) {
        console.log(`[GameState] Cambiando pantalla a: ${screenName}`);
        
        // Ocultar todas las pantallas
        document.querySelectorAll('.screen').forEach(screen => {
            screen.classList.remove('active');
        });
        
        // Mostrar la pantalla solicitada
        const targetScreen = document.getElementById(`screen-${screenName}`);
        if (targetScreen) {
            targetScreen.classList.add('active');
            this.currentScreen = screenName;
        } else {
            console.warn(`[GameState] Pantalla no encontrada: ${screenName}`);
        }
    },
    
    /**
     * Establece el nombre del jugador
     */
    setPlayerName(name) {
        this.playerName = name.trim();
    },
    
    /**
     * Actualiza el game_state desde el servidor
     */
    updateGameState(serverGameState) {
        console.log(`[GameState] Actualizando game_state: ${serverGameState}`);
        this.gameState = serverGameState;
        
        // Notificar que el estado cambió
        const event = new CustomEvent('game-state-changed', {
            detail: { gameState: serverGameState }
        });
        document.dispatchEvent(event);
    },
    
    /**
     * Actualiza info del juego actual
     */
    updateGameInfo(gameInfo) {
        if (gameInfo.currentTurn) this.game.currentTurn = gameInfo.currentTurn;
        if (gameInfo.yourId) this.game.yourId = gameInfo.yourId;
        if (gameInfo.opponentId) this.game.opponentId = gameInfo.opponentId;
        if (typeof gameInfo.moveCount === 'number') this.game.moveCount = gameInfo.moveCount;
        if (typeof gameInfo.yourShipsRemaining === 'number') this.game.yourShipsRemaining = gameInfo.yourShipsRemaining;
        if (typeof gameInfo.enemyShipsRemaining === 'number') this.game.enemyShipsRemaining = gameInfo.enemyShipsRemaining;
    },
    
    /**
     * Selecciona un barco para posicionar
     */
    selectShip(shipId) {
        this.placement.selectedShip = shipId;
    },
    
    /**
     * Rota la orientación del barco seleccionado
     */
    rotateShip() {
        if (!this.placement.selectedShip) return;
        
        const selectedShip = this.placement.ships.find(s => s.id === this.placement.selectedShip);
        if (selectedShip) {
            selectedShip.orientation = 
                selectedShip.orientation === 'HORIZONTAL' ? 'VERTICAL' : 'HORIZONTAL';
            
            // Actualizar también la orientación global para el siguiente barco
            this.placement.orientation = selectedShip.orientation;
        }
    },
    
    /**
     * Marca un barco como colocado
     */
    placeShip(shipId, positions) {
        const ship = this.placement.ships.find(s => s.id === shipId);
        if (ship) {
            ship.placed = true;
            this.placement.placedShips.push({
                ...ship,
                positions: positions,
                orientation: ship.orientation  // Usar la orientación del barco, no la global
            });
        }
    },
    
    /**
     * Verifica si todos los barcos han sido colocados
     */
    allShipsPlaced() {
        return this.placement.ships.every(ship => ship.placed);
    },
    
    /**
     * Reinicia el estado de posicionamiento
     */
    resetPlacement() {
        this.placement.selectedShip = null;
        this.placement.orientation = 'HORIZONTAL';
        this.placement.placedShips = [];
        this.placement.ships.forEach(ship => {
            ship.placed = false;
        });
    },
    
    /**
     * Obtiene el barco seleccionado actualmente
     */
    getSelectedShip() {
        if (!this.placement.selectedShip) return null;
        return this.placement.ships.find(s => s.id === this.placement.selectedShip);
    },
    
    /**
     * Añade una entrada al log de combate
     */
    addCombatLog(message, type = 'info') {
        this.game.combatLog.push({
            message,
            type,
            timestamp: new Date()
        });
    },
    
    /**
     * Actualiza el tablero de defensa
     */
    updateDefenseCell(x, y, state) {
        if (this.game.defenseBoard[y]) {
            this.game.defenseBoard[y][x] = state;
        }
    },
    
    /**
     * Actualiza el tablero de ataque
     */
    updateAttackCell(x, y, state) {
        if (this.game.attackBoard[y]) {
            this.game.attackBoard[y][x] = state;
        }
    },
    
    /**
     * Inicia el temporizador del juego
     */
    startGameTimer() {
        this.gameTimer.startTime = new Date();
    },
    
    /**
     * Detiene el temporizador del juego
     */
    stopGameTimer() {
        this.gameTimer.endTime = new Date();
    },
    
    /**
     * Obtiene la duración del juego en formato MM:SS
     */
    getGameDuration() {
        if (!this.gameTimer.startTime || !this.gameTimer.endTime) {
            return '--:--';
        }
        
        const duration = Math.floor((this.gameTimer.endTime - this.gameTimer.startTime) / 1000);
        const minutes = Math.floor(duration / 60);
        const seconds = duration % 60;
        
        return `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
    },
    
    /**
     * Pide confirmación antes de recargar
     */
    setupUnloadConfirmation() {
        window.addEventListener('beforeunload', (event) => {
            // Si hay una sesión activa y no es fin de juego
            if (this.sessionId && this.gameState !== this.SERVER_STATE_FINISHED) {
                event.preventDefault();
                event.returnValue = '¿Estás seguro? Desconectarás de la partida.';
                return '¿Estás seguro? Desconectarás de la partida.';
            }
        });
    }
};

// Exportar para uso en otros módulos
if (typeof module !== 'undefined' && module.exports) {
    module.exports = GameState;
}
