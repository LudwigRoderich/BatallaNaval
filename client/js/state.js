/**
 * Módulo para gestionar el estado de la interfaz del juego
 */

const GameState = {
    // Estados de pantalla
    SCREEN_START: 'start',
    SCREEN_PLACEMENT: 'placement',
    SCREEN_GAME: 'game',
    SCREEN_GAMEOVER: 'gameover',
    
    // Estado actual
    currentScreen: 'start',
    playerName: '',
    playerId: null,
    matchId: null,
    boardSize: 10,
    
    // Estado de posicionamiento
    placement: {
        selectedShip: null,
        orientation: 'horizontal',
        placedShips: [],
        ships: [
            { id: 'carrier', name: 'Portaaviones', type: 'AIRCRAFT_CARRIER', length: 5, placed: false, orientation: 'horizontal'},
            { id: 'battleship', name: 'Acorazado', type: 'BATTLESHIP', length: 4, placed: false, orientation: 'horizontal' },
            { id: 'cruiser', name: 'Crucero', type: 'CRUISER', length: 3, placed: false, orientation: 'horizontal' },
            { id: 'destroyer', name: 'Destructor', type: 'DESTROYER', length: 3, placed: false, orientation: 'horizontal' },
            { id: 'submarine', name: 'Submarino', type: 'SUBMARINE', length: 2, placed: false, orientation: 'horizontal' }
        ]
    },
    
    // Estado del juego
    game: {
        currentTurn: '',
        moveCount: 0,
        yourShipsRemaining: 5,
        enemyShipsRemaining: 5,
        defenseBoard: [],
        attackBoard: [],
        combatLog: []
    },
    
    // Temporizador de juego
    gameTimer: {
        startTime: null,
        endTime: null
    },
    
    /**
     * Inicializa el estado del juego
     * Se ejecuta una sola vez al cargar la aplicación
     */
    init() {
        console.log('[GameState] Inicializando estado...');
        
        // Resetear pantalla
        this.currentScreen = this.SCREEN_START;
        
        // Limpiar datos de jugador
        this.playerName = '';
        this.playerId = null;
        this.matchId = null;
        
        // Resetear posicionamiento
        this.resetPlacement();
        
        // Reiniciar juego
        this.game = {
            currentTurn: '',
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
        
        console.log('[GameState] ✓ Estado inicializado correctamente');
    },
    
    /**
     * Cambia a una pantalla específica
     */
    switchScreen(screenName) {
        // Ocultar todas las pantallas
        document.querySelectorAll('.screen').forEach(screen => {
            screen.classList.remove('active');
        });
        
        // Mostrar la pantalla solicitada
        const targetScreen = document.getElementById(`screen-${screenName}`);
        if (targetScreen) {
            targetScreen.classList.add('active');
            this.currentScreen = screenName;
        }
    },
    
    /**
     * Establece el nombre del jugador
     */
    setPlayerName(name) {
        this.playerName = name.trim();
    },
    
    /**
     * Inicializa el tablero de defensa
     */
    initDefenseBoard() {
        this.game.defenseBoard = Array(this.boardSize).fill(null).map(() => 
            Array(this.boardSize).fill('empty')
        );
    },
    
    /**
     * Inicializa el tablero de ataque
     */
    initAttackBoard() {
        this.game.attackBoard = Array(this.boardSize).fill(null).map(() => 
            Array(this.boardSize).fill('empty')
        );
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
        this.placement.orientation = 
            this.placement.orientation === 'horizontal' ? 'vertical' : 'horizontal';
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
                orientation: this.placement.orientation
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
        this.placement.orientation = 'horizontal';
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
     * Reinicia todo el estado del juego (al volver a inicio)
     */
    reset() {
        console.log('[GameState] Reseteando estado...');
        this.init();
        console.log('[GameState] ✓ Estado reseteado');
    }
};

// Exportar para uso en otros módulos
if (typeof module !== 'undefined' && module.exports) {
    module.exports = GameState;
}
