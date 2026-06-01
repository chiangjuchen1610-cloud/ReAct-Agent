const canvas = document.getElementById('gameCanvas');
const ctx = canvas.getContext('2d');
const scoreDisplay = document.getElementById('score');
const startButton = document.getElementById('startButton');

const gridSize = 20;
let snake = [{ x: 10 * gridSize, y: 10 * gridSize }];
let food = {};
let direction = 'right';
let score = 0;
let gameInterval;
let gameSpeed = 150; // Milliseconds
let gameRunning = false;

function generateFood() {
    food = {
        x: Math.floor(Math.random() * (canvas.width / gridSize)) * gridSize,
        y: Math.floor(Math.random() * (canvas.height / gridSize)) * gridSize
    };
}

function draw() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Draw food
    ctx.fillStyle = 'red';
    ctx.fillRect(food.x, food.y, gridSize, gridSize);

    // Draw snake
    ctx.fillStyle = 'lime';
    snake.forEach(segment => {
        ctx.fillRect(segment.x, segment.y, gridSize, gridSize);
    });
}

function update() {
    if (!gameRunning) return;

    // Move snake
    const head = { x: snake[0].x, y: snake[0].y };

    switch (direction) {
        case 'up':
            head.y -= gridSize;
            break;
        case 'down':
            head.y += gridSize;
            break;
        case 'left':
            head.x -= gridSize;
            break;
        case 'right':
            head.x += gridSize;
            break;
    }

    // Check for collisions with walls
    if (head.x < 0 || head.x >= canvas.width || head.y < 0 || head.y >= canvas.height) {
        endGame();
        return;
    }

    // Check for collision with self
    for (let i = 1; i < snake.length; i++) {
        if (head.x === snake[i].x && head.y === snake[i].y) {
            endGame();
            return;
        }
    }

    snake.unshift(head); // Add new head

    // Check if snake eats food
    if (head.x === food.x && head.y === food.y) {
        score++;
        scoreDisplay.textContent = `Score: ${score}`;
        generateFood(); // Generate new food
        // Optional: Increase speed gradually
        // gameSpeed = Math.max(50, gameSpeed - 5);
        // clearInterval(gameInterval);
        // gameInterval = setInterval(update, gameSpeed);
    } else {
        snake.pop(); // Remove tail if no food eaten
    }

    draw();
}

function changeDirection(event) {
    const keyPressed = event.key;
    const goingUp = direction === 'up';
    const goingDown = direction === 'down';
    const goingLeft = direction === 'left';
    const goingRight = direction === 'right';

    if (keyPressed === 'ArrowUp' && !goingDown) {
        direction = 'up';
    } else if (keyPressed === 'ArrowDown' && !goingUp) {
        direction = 'down';
    } else if (keyPressed === 'ArrowLeft' && !goingRight) {
        direction = 'left';
    } else if (keyPressed === 'ArrowRight' && !goingLeft) {
        direction = 'right';
    }
}

function startGame() {
    snake = [{ x: 10 * gridSize, y: 10 * gridSize }];
    direction = 'right';
    score = 0;
    scoreDisplay.textContent = `Score: ${score}`;
    gameSpeed = 150;
    gameRunning = true;
    generateFood();
    draw(); // Initial draw
    if (gameInterval) clearInterval(gameInterval);
    gameInterval = setInterval(update, gameSpeed);
    startButton.textContent = 'Restart Game';
}

function endGame() {
    gameRunning = false;
    clearInterval(gameInterval);
    alert(`Game Over! Your score: ${score}`);
    startButton.textContent = 'Start Game';
}

document.addEventListener('keydown', changeDirection);
startButton.addEventListener('click', startGame);

// Initial setup
draw();
