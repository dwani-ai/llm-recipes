import os
import base64
import io
import time
import pygame
from openai import OpenAI
import chess
import chess.engine

def get_openai_client(model: str) -> OpenAI:
    valid_models = ["gemma3"]
    if model not in valid_models:
        raise ValueError(f"Invalid model: {model}")

    base_url = os.getenv("DWANI_API_BASE_URL")
    if not base_url:
        raise RuntimeError("DWANI_API_BASE_URL environment variable is not set")

    return OpenAI(api_key="http", base_url=base_url)

# Configuration
os.environ['SDL_VIDEO_WINDOW_POS'] = "100,100"
STOCKFISH_PATH = "/usr/games/stockfish"
MODE = 1  # 1: Vision-only each turn | 2: Track full game state
THINK_TIME_OPP = 2.0
BOARD_SIZE = 800
SQUARE_SIZE = BOARD_SIZE // 8
DEBUG_DIR = "debug_images"
os.makedirs(DEBUG_DIR, exist_ok=True)

# Initialize Pygame
pygame.init()
screen = pygame.display.set_mode((BOARD_SIZE, BOARD_SIZE))
pygame.display.set_caption("Local Chess: Vision Bot (White) vs Stockfish (Black)")
clock = pygame.time.Clock()
font = pygame.font.SysFont("dejavusans", int(SQUARE_SIZE * 0.8))

# Unicode pieces
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
PIECE_COLOR = (0, 0, 0)  # Black text for all pieces

# Stockfish
engine = chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH)
engine.configure({"Threads": 4, "Hash": 2048})

def draw_board(screen, board):
    for row in range(8):
        for col in range(8):
            color = LIGHT_SQUARE if (row + col) % 2 == 0 else DARK_SQUARE
            rect = pygame.Rect(col * SQUARE_SIZE, row * SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE)
            pygame.draw.rect(screen, color, rect)
    
    for row in range(8):
        chess_rank = 7 - row
        for col in range(8):
            square = chess.square(col, chess_rank)
            piece = board.piece_at(square)
            if piece:
                sym = PIECES[piece.piece_type][piece.color]
                text_surf = font.render(sym, True, PIECE_COLOR)
                text_rect = text_surf.get_rect(center=(
                    col * SQUARE_SIZE + SQUARE_SIZE // 2,
                    row * SQUARE_SIZE + SQUARE_SIZE // 2
                ))
                screen.blit(text_surf, text_rect)
    
    pygame.display.flip()

def get_board_screenshot_b64(screen):
    img_buffer = io.BytesIO()
    pygame.image.save(screen, img_buffer, "PNG")
    img_buffer.seek(0)
    return base64.b64encode(img_buffer.read()).decode("utf-8")

def get_placement_from_screenshot(b64_image, turn_number):
    """Improved prompt for Qwen3-VL-8B (gemma3)"""
    model_name = "gemma3"  # This is your Qwen3-VL-8B vision model
    client = get_openai_client(model_name)

    vision_prompt = """Analyze this chessboard image carefully. The board is oriented with White at the bottom (rank 1 at bottom, rank 8 at top) and Black at the top. Identify every piece on each square, row by row from top (rank 8) to bottom (rank 1).

Use standard FEN notation for piece placement:
- Uppercase for White: P (pawn), N (knight), B (bishop), R (rook), Q (queen), K (king)
- Lowercase for Black: p, n, b, r, q, k
- Numbers (1-8) for consecutive empty squares
- Rows separated by /

Examine the image closely: look at the Unicode symbols (♔♕♖♗♘♙ for White, ♚♛♜♝♞♟ for Black), their exact positions, and any moved or captured pieces. Do not assume the starting position — detect the current layout accurately.

Output ONLY the piece placement part (8 rows separated by /). No explanations, no full FEN, no quotes, no extra text."""

    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": vision_prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64_image}"}}
                ]
            }
        ],
        max_tokens=100,
        temperature=0.0
    )

    print(f"\n--- Vision Model Logging (Turn {turn_number}) ---")
    content = response.choices[0].message.content.strip()
    print("Raw output:", repr(content))
    print("--- End Logging ---\n")

    if '/' not in content or len(content.split('/')) != 8:
        raise ValueError(f"Invalid placement format: {content}")

    return content

def get_move_from_openai(current_board):
    """Get move from text model — prefer gemma3 if it's better at chess"""
    model_name = "gemma3"  # Change to "gemma3" if gemma3 is unavailable or weaker
    client = get_openai_client(model_name)
    
    fen = current_board.fen()
    prompt = f"""You are a strong chess player. The current position is:

{fen}

White to move. Think carefully and output ONLY the best move in UCI format (e.g., e7e8q for promotion with queen). No explanation, no extra text."""

    for attempt in range(5):  # Increased retries
        response = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=10,
            temperature=0.2  # Slight temperature for better exploration
        )
        move_str = response.choices[0].message.content.strip()
        print(f"OpenAI suggested: {move_str}")

        try:
            move = chess.Move.from_uci(move_str)
            if move in current_board.legal_moves:
                return move
            else:
                print(f"Illegal move {move_str}, retrying...")
        except ValueError:
            print(f"Invalid UCI format: {move_str}, retrying...")

    raise ValueError("Failed to get valid move after multiple attempts.")

# Game loop
game_board = chess.Board()
our_turn = True
turn_counter = 1

print("Starting game: Vision Bot (White) vs Stockfish (Black)")
print("Mode:", "Vision-only per turn" if MODE == 1 else "Full history tracking")

try:
    while not game_board.is_game_over():
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                raise KeyboardInterrupt

        draw_board(screen, game_board)
        time.sleep(0.6)  # Ensure render is complete

        if our_turn:
            print(f"\nTurn {turn_counter} - Our move (White)")
            b64_image = get_board_screenshot_b64(screen)
            debug_path = os.path.join(DEBUG_DIR, f"turn_{turn_counter}_white.png")
            with open(debug_path, 'wb') as f:
                f.write(base64.b64decode(b64_image))
            print(f"Screenshot saved: {debug_path}")

            placement = get_placement_from_screenshot(b64_image, turn_counter)
            print("Parsed placement:", placement)
            print("Actual placement :", game_board.board_fen())

            expected = game_board.board_fen()
            if placement != expected:
                print("Vision mismatch! Retrying once...")
                placement = get_placement_from_screenshot(b64_image, turn_counter)
                if placement != expected:
                    print("Retry failed — falling back to internal state.")
                    current_board = game_board
                else:
                    print("Retry successful.")
                    fen = f"{placement} {'w' if our_turn else 'b'} KQkq - 0 1"
                    current_board = chess.Board(fen)
            else:
                print("Vision parse correct.")
                if MODE == 1:
                    fen = f"{placement} w KQkq - 0 1"
                    current_board = chess.Board(fen)
                else:
                    current_board = game_board

            print("Thinking about move...")
            move = get_move_from_openai(current_board)
            print(f"Playing: {move.uci()}")
            game_board.push(move)
            turn_counter += 1

        else:
            print("\nStockfish (Black) thinking...")
            result = engine.play(game_board, chess.engine.Limit(time=THINK_TIME_OPP))
            move = result.move
            print(f"Stockfish plays: {move.uci()}")
            game_board.push(move)

        our_turn = not our_turn
        clock.tick(30)

    print("\nGame Over!")
    print("Result:", game_board.result())
    print("Final FEN:", game_board.fen())

except KeyboardInterrupt:
    print("\nGame stopped by user.")
finally:
    engine.quit()
    pygame.quit()