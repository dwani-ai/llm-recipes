import os
import time
import pygame
import chess
import chess.engine
from openai import OpenAI

# ====================== CONFIG ======================
DWANI_API_BASE_URL = os.getenv("DWANI_API_BASE_URL")
if not DWANI_API_BASE_URL:
    raise RuntimeError("Please set DWANI_API_BASE_URL environment variable")

STOCKFISH_PATH = "/usr/games/stockfish"      # Change if needed
GEMMA_MODEL = "gemma3"                        # Your model for White
THINK_TIME_STOCKFISH = 2.0
MAX_RETRIES = 10
TEMPERATURE = 0.6

BOARD_SIZE = 800
SQUARE_SIZE = BOARD_SIZE // 8
FPS = 30

# Colors
LIGHT_SQUARE = (240, 217, 181)
DARK_SQUARE = (181, 136, 99)
TEXT_COLOR = (0, 0, 0)

# Unicode chess symbols
PIECES = {
    chess.PAWN:   {chess.WHITE: '♙', chess.BLACK: '♟'},
    chess.KNIGHT: {chess.WHITE: '♘', chess.BLACK: '♞'},
    chess.BISHOP: {chess.WHITE: '♗', chess.BLACK: '♝'},
    chess.ROOK:   {chess.WHITE: '♖', chess.BLACK: '♜'},
    chess.QUEEN:  {chess.WHITE: '♕', chess.BLACK: '♛'},
    chess.KING:   {chess.WHITE: '♔', chess.BLACK: '♚'},
}
# ===================================================

def get_openai_client(model: str) -> OpenAI:
    return OpenAI(api_key="http", base_url=DWANI_API_BASE_URL)

# Initialize Pygame
pygame.init()
screen = pygame.display.set_mode((BOARD_SIZE, BOARD_SIZE))
pygame.display.set_caption("gemma3 (White) vs Stockfish (Black)")
clock = pygame.time.Clock()
font = pygame.font.SysFont("dejavusans", int(SQUARE_SIZE * 0.8))

def draw_board(screen, board: chess.Board):
    # Draw squares
    for row in range(8):
        for col in range(8):
            color = LIGHT_SQUARE if (row + col) % 2 == 0 else DARK_SQUARE
            pygame.draw.rect(screen, color, (col * SQUARE_SIZE, row * SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE))

    # Draw pieces (row 0 = rank 8, row 7 = rank 1 → White at bottom)
    for row in range(8):
        rank = 7 - row
        for col in range(8):
            square = chess.square(col, rank)
            piece = board.piece_at(square)
            if piece:
                symbol = PIECES[piece.piece_type][piece.color]
                text_surf = font.render(symbol, True, TEXT_COLOR)
                text_rect = text_surf.get_rect(center=(
                    col * SQUARE_SIZE + SQUARE_SIZE // 2,
                    row * SQUARE_SIZE + SQUARE_SIZE // 2
                ))
                screen.blit(text_surf, text_rect)

    pygame.display.flip()

def get_move_from_gemma3(board: chess.Board) -> chess.Move:
    client = get_openai_client(GEMMA_MODEL)
    fen = board.fen()

    prompt = f"""Current position (FEN):
{fen}

You are playing White. It's your turn.
Output ONLY a strong move in UCI format (e.g. e2e4, g1f3, e7e8q).
No text, no explanation, just the move."""

    import re
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.chat.completions.create(
                model=GEMMA_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=12,
                temperature=TEMPERATURE,
            )
            output = response.choices[0].message.content.strip().lower()
            print(f"  gemma3 attempt {attempt}: {output}")

            # Find all possible UCI patterns
            candidates = re.findall(r'[a-h][1-8][a-h][1-8][qrbn]?', output)
            for cand in candidates:
                try:
                    move = chess.Move.from_uci(cand)
                    if move in board.legal_moves:
                        print(f"  → Accepted move: {move.uci()}")
                        return move
                except:
                    continue

            print("    → No legal move found, retrying...")

        except Exception as e:
            print(f"    → Error: {e}")

    raise RuntimeError("gemma3 failed to produce a legal move after all retries.")

# =================== SETUP GAME ===================
board = chess.Board()
engine = chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH)
engine.configure({"Threads": 4, "Hash": 2048})

turn_number = 1
running = True

print("Starting game: gemma3 (White) vs Stockfish (Black)")
print("Watch the Pygame window for live board updates!\n")

draw_board(screen, board)
time.sleep(2)  # Let user see initial position

# =================== MAIN LOOP ===================
try:
    while running and not board.is_game_over():
        # Handle window close
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        if board.turn == chess.WHITE:
            # gemma3 plays White
            print(f"\nTurn {turn_number} | gemma3 (White) thinking...")
            move = get_move_from_gemma3(board)
            board.push(move)
            print(f"gemma3 played: {move.uci()}")
        else:
            # Stockfish plays Black
            print(f"\nTurn {turn_number} | Stockfish (Black) thinking...")
            result = engine.play(board, chess.engine.Limit(time=THINK_TIME_STOCKFISH))
            move = result.move
            board.push(move)
            print(f"Stockfish played: {move.uci()}")

        turn_number += 1

        # Update display
        draw_board(screen, board)
        time.sleep(1.0)  # Pause to see the move
        clock.tick(FPS)

    # Game over
    if board.is_game_over():
        print("\n" + "="*60)
        print("GAME OVER")
        print("="*60)
        result = board.result()
        if result == "1-0":
            print("gemma3 (White) wins! 🎉")
        elif result == "0-1":
            print("Stockfish wins. (Expected against a perfect engine 😅)")
        else:
            print("Draw!")
        print(f"Result: {result}")
        print(f"Final position:\n{board}")

        # Keep window open for a while
        draw_board(screen, board)
        time.sleep(10)

except KeyboardInterrupt:
    print("\nGame stopped by user.")
except Exception as e:
    print(f"\nError: {e}")
finally:
    engine.quit()
    pygame.quit()