import os
import base64
import io
import time
import pygame
from openai import OpenAI
import chess
import chess.engine


def get_openai_client(model: str) -> OpenAI:
    valid_models = ["gemma3", "gpt-oss"]
    if model not in valid_models:
        raise ValueError(f"Invalid model: {model}")

    base_url = os.getenv("DWANI_API_BASE_URL")
    if not base_url:
        raise RuntimeError("DWANI_API_BASE_URL environment variable is not set")

    return OpenAI(api_key="http", base_url=base_url)

# Configuration
os.environ['SDL_VIDEO_WINDOW_POS'] = "100,100"  # Fixed window position
OPENAI_API_KEY = "your-openai-api-key-here"
STOCKFISH_PATH = "/usr/games/stockfish"  # Default Ubuntu path after 'sudo apt install stockfish'
MODE = 1  # 1: Only current knowledge (parse screenshot each turn, defaults for FEN extras)
         # 2: Previous moves (track full game state internally)
THINK_TIME_OUR = 1.0  # Seconds for our engine
THINK_TIME_OPP = 2.0  # Seconds for opponent (perfect play)
BOARD_SIZE = 800
SQUARE_SIZE = BOARD_SIZE // 8

# Initialize
pygame.init()
screen = pygame.display.set_mode((BOARD_SIZE, BOARD_SIZE))
pygame.display.set_caption("Local Chess: Vision Bot (White) vs Stockfish (Black)")
clock = pygame.time.Clock()
font = pygame.font.SysFont("dejavusans", int(SQUARE_SIZE * 0.8))  # Use system font with Unicode chess support

# Unicode pieces (white uppercase-style, black lowercase-style)
PIECES = {
    chess.PAWN:    {chess.WHITE: '♙', chess.BLACK: '♟'},
    chess.KNIGHT:  {chess.WHITE: '♘', chess.BLACK: '♞'},
    chess.BISHOP:  {chess.WHITE: '♗', chess.BLACK: '♝'},
    chess.ROOK:    {chess.WHITE: '♖', chess.BLACK: '♜'},
    chess.QUEEN:   {chess.WHITE: '♕', chess.BLACK: '♛'},
    chess.KING:    {chess.WHITE: '♔', chess.BLACK: '♚'},
}

# Colors
LIGHT_SQUARE = (240, 217, 181)
DARK_SQUARE = (181, 136, 99)
WHITE_PIECE_COLOR = (30, 30, 30)  # Dark for visibility
BLACK_PIECE_COLOR = (30, 30, 30)  # Same for now

# OpenAI
openai_client = OpenAI(api_key=OPENAI_API_KEY)

# Stockfish engine (shared)
engine = chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH)
engine.configure({"Threads": 4, "Hash": 2048})  # Optional: tune for your machine

def draw_board(screen, board):
    # Draw squares
    for row in range(8):
        for col in range(8):
            color = LIGHT_SQUARE if (row + col) % 2 == 0 else DARK_SQUARE
            rect = pygame.Rect(col * SQUARE_SIZE, row * SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE)
            pygame.draw.rect(screen, color, rect)
    
    # Draw pieces (white at bottom: row 0 = rank 8, row 7 = rank 1)
    for row in range(8):
        chess_rank = 7 - row
        for col in range(8):
            square = chess.square(col, chess_rank)
            piece = board.piece_at(square)
            if piece:
                sym = PIECES[piece.piece_type][piece.color]
                piece_color = WHITE_PIECE_COLOR if piece.color == chess.WHITE else BLACK_PIECE_COLOR
                text_surf = font.render(sym, True, piece_color)
                text_rect = text_surf.get_rect(center=(col * SQUARE_SIZE + SQUARE_SIZE // 2,
                                                      row * SQUARE_SIZE + SQUARE_SIZE // 2))
                screen.blit(text_surf, text_rect)
    
    pygame.display.flip()

def get_board_screenshot_b64(screen):
    """Capture exact board PNG from Pygame surface (no window borders)"""
    img_buffer = io.BytesIO()
    pygame.image.save(screen, img_buffer, "PNG")
    img_buffer.seek(0)
    return base64.b64encode(img_buffer.read()).decode("utf-8")

def get_placement_from_screenshot(b64_image):
    """Parse piece placement from board screenshot using OpenAI Vision"""

    model_name="gemma3"
    client = get_openai_client(model_name)

    response = client.chat.completions.create(
        model=model_name,
            messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "This is a screenshot of a chessboard (white pieces at bottom). Output ONLY the piece placement part of FEN: 8 rows separated by / (e.g., rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR). Uppercase=White, lowercase=Black, numbers=empty squares. No extra text."
                    },
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64_image}"}}
                ]
            }
        ],
        max_tokens=100,
        temperature=0.1
    )
    placement = response.choices[0].message.content.strip()
    if '/' not in placement or len(placement.split('/')) != 8:
        raise ValueError("Invalid placement parsed")
    return placement

# Game setup: We (White, vision-bot) vs Opponent (Black, perfect Stockfish)
game_board = chess.Board()
our_turn = True  # White to move first

print("Starting game: Vision Bot (White) vs Stockfish (Black)")
print("Mode:", "Current knowledge only" if MODE == 1 else "Full history")
print("Press Ctrl+C or close window to stop.")

try:
    while not game_board.is_game_over():
        # Handle events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                raise KeyboardInterrupt

        # Draw current board
        draw_board(screen, game_board)

        if our_turn:
            # Our turn (always White)
            print("\nOur turn (White)...")
            b64_image = get_board_screenshot_b64(screen)
            placement = get_placement_from_screenshot(b64_image)
            print("Parsed placement:", placement)

            if MODE == 1:
                # Mode 1: Current knowledge only - defaults for castling/en passant/etc.
                fen = f"{placement} w KQkq - 0 1"
                current_board = chess.Board(fen)
                print("Mode 1 FEN:", fen)
            else:
                # Mode 2: Full history
                current_board = game_board
                print("Mode 2: Using full board state")

            # Compute and play move
            print("Thinking...")
            result = engine.play(current_board, chess.engine.Limit(time=THINK_TIME_OUR))
            move = result.move
            print("Our move:", move)
            game_board.push(move)
            print("Board after our move:\n", game_board)

        else:
            # Opponent turn (Black, perfect)
            print("\nOpponent turn (Black)...")
            print("Thinking...")
            result = engine.play(game_board, chess.engine.Limit(time=THINK_TIME_OPP))
            move = result.move
            print("Opponent move:", move)
            game_board.push(move)
            print("Board after opponent move:\n", game_board)

        our_turn = not our_turn
        clock.tick(30)  # Limit FPS

    # Game over
    print("\nGame Over!")
    print(game_board.result())
    print("Final FEN:", game_board.fen())

except KeyboardInterrupt:
    print("\nStopped by user.")

finally:
    engine.quit()
    pygame.quit()