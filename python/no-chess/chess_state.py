import os
import time
import pygame
import chess
import chess.engine
import re
from openai import OpenAI

# ====================== CONFIG ======================
DWANI_API_BASE_URL = os.getenv("DWANI_API_BASE_URL")
if not DWANI_API_BASE_URL:
    raise RuntimeError("Please set DWANI_API_BASE_URL environment variable")

STOCKFISH_PATH = "/usr/games/stockfish"
GEMMA_MODEL = "gemma3"
THINK_TIME_STOCKFISH = 2.0
MAX_RETRIES = 15

BOARD_SIZE = 800
SQUARE_SIZE = BOARD_SIZE // 8
FPS = 30

LIGHT_SQUARE = (240, 217, 181)
DARK_SQUARE = (181, 136, 99)
TEXT_COLOR = (0, 0, 0)

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

# Pygame setup
pygame.init()
screen = pygame.display.set_mode((BOARD_SIZE, BOARD_SIZE))
pygame.display.set_caption("gemma3 (White) vs Stockfish (Black)")
clock = pygame.time.Clock()
font = pygame.font.SysFont("dejavusans", int(SQUARE_SIZE * 0.8))

def draw_board(screen, board: chess.Board):
    for row in range(8):
        for col in range(8):
            color = LIGHT_SQUARE if (row + col) % 2 == 0 else DARK_SQUARE
            pygame.draw.rect(screen, color, (col * SQUARE_SIZE, row * SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE))

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

    # SYSTEM MESSAGE — this is the key to better behavior
    system_prompt = (
        "You are a chess engine playing as White. "
        "You always analyze the current position carefully. "
        "You never repeat the same move if it is illegal. "
        "You respond ONLY with a valid UCI move — nothing else. "
        "No words, no explanations, no punctuation, no quotes. "
        "Just the move like: e2e4 or g1f3 or e7e8q."
    )

    user_prompt = f"Current position (FEN): {fen}\nYour move as White:"

    for attempt in range(1, MAX_RETRIES + 1):
        temperature = 0.7 + (attempt - 1) * 0.05  # Slight increase if stuck

        try:
            response = client.chat.completions.create(
                model=GEMMA_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_prompt}
                ],
                max_tokens=10,
                temperature=temperature,
                top_p=0.9,
            )
            output = response.choices[0].message.content.strip()
            print(f"  gemma3 attempt {attempt} (temp={temperature:.2f}): {output!r}")

            # Extract UCI move
            matches = re.findall(r'[a-h][1-8][a-h][1-8][qrbn]?', output.lower())
            for uci in matches:
                try:
                    move = chess.Move.from_uci(uci)
                    if move in board.legal_moves:
                        print(f"  → Accepted: {move.uci()}")
                        return move
                except:
                    continue

            print("    → No legal move found, retrying...")

        except Exception as e:
            print(f"    → API error: {e}")

    raise RuntimeError(f"gemma3 failed to make a legal move after {MAX_RETRIES} attempts.")

# =================== GAME SETUP ===================
board = chess.Board()
engine = chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH)
engine.configure({"Threads": 4, "Hash": 2048})

turn_number = 1
running = True

print("Starting game: gemma3 (White) vs Stockfish (Black)")
print("Using strong system prompt for better move quality.\n")

draw_board(screen, board)
time.sleep(2)

# =================== MAIN LOOP ===================
try:
    while running and not board.is_game_over():
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        if board.turn == chess.WHITE:
            print(f"\nTurn {turn_number} | gemma3 (White) thinking...")
            move = get_move_from_gemma3(board)
            board.push(move)
            print(f"gemma3 played: {move.uci()}")
        else:
            print(f"\nTurn {turn_number} | Stockfish (Black) thinking...")
            result = engine.play(board, chess.engine.Limit(time=THINK_TIME_STOCKFISH))
            move = result.move
            board.push(move)
            print(f"Stockfish played: {move.uci()}")

        turn_number += 1
        draw_board(screen, board)
        time.sleep(1.2)
        clock.tick(FPS)

    # Game Over
    if board.is_game_over():
        print("\n" + "="*60)
        print("GAME OVER")
        print("="*60)
        result = board.result()
        if result == "1-0":
            print("gemma3 wins! Incredible!")
        elif result == "0-1":
            print("Stockfish wins — as expected.")
        else:
            print("Draw! Well fought.")
        print(f"Result: {result}")

        draw_board(screen, board)
        time.sleep(20)

except KeyboardInterrupt:
    print("\nGame stopped.")
except Exception as e:
    print(f"\nError: {e}")
finally:
    engine.quit()
    pygame.quit()