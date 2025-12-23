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
GEMMA_MODEL = "gemma3"  # Change to your thinking model if available

THINK_TIME_STOCKFISH = 2.0
MAX_RETRIES = 20

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

# ==================== PYGAME SETUP ====================
pygame.init()
screen = pygame.display.set_mode((BOARD_SIZE, BOARD_SIZE))
pygame.display.set_caption(f"{GEMMA_MODEL} (White) vs Stockfish (Black)")
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

# =============== GET CLEAN ASCII BOARD ===============
def get_ascii_board(board: chess.Board) -> str:
    """Generate numbered, clearly labeled ASCII board"""
    lines = str(board).split('\n')[:8]  # Only the 8 board lines
    
    formatted = []
    formatted.append("CURRENT BOARD POSITION")
    formatted.append("(White at bottom, Black at top | White to move)")
    formatted.append("")
    
    # Add rank numbers (8 to 1)
    for i, line in enumerate(lines):
        rank_num = 8 - i
        formatted.append(f"{rank_num} │ {line}")
    
    formatted.append("  └─────────────────────────────────")
    formatted.append("     a b c d e f g h")
    formatted.append("")
    formatted.append(f"FEN: {board.fen()}")
    formatted.append("")
    
    return '\n'.join(formatted)

# =============== THINK + RELIABLE MOVE ===============
def get_move_from_llm(board: chess.Board) -> chess.Move:
    client = get_openai_client(GEMMA_MODEL)
    
    ascii_board = get_ascii_board(board)
    
    # Strong candidate moves (common good openings + some development)
    candidates = ["e2e4", "d2d4", "g1f3", "c2c4", "b1c3", "g2g3", "e2e3", "d2d3"]
    # Filter to only legal ones
    good_moves = [m for m in candidates if chess.Move.from_uci(m) in board.legal_moves]
    # Fallback to top legal
    top_legal = list(board.legal_moves)[:15]
    all_good = good_moves + [m.uci() for m in top_legal if m.uci() not in good_moves]
    legal_str = ", ".join(all_good[:12])

    system_prompt = (
        "You are a strong chess player playing as White.\n"
        "The board is shown clearly below with rank numbers (8 at top, 1 at bottom) and file letters (a-h).\n"
        "Use ONLY this visual board — ignore any confusion about FEN.\n"
        "The position is always valid and standard.\n\n"
        "Analyze the position briefly:\n"
        "- Center control\n"
        "- Piece development\n"
        "- King safety\n\n"
        "Then choose the BEST move from the strong candidates listed.\n"
        "Strong opening moves include: e2e4, d2d4, g1f3, c2c4, b1c3.\n\n"
        "At the end of your response, write ONLY:\n"
        "Best move: <UCI format>\n"
        "Example: Best move: e2e4\n"
        "No other text after that line."
    )

    user_prompt = (
        f"{ascii_board}\n\n"
        f"Strong candidate moves: {legal_str}\n\n"
        "What is your best move as White?"
    )

    for attempt in range(1, MAX_RETRIES + 1):
        temperature = 0.3 + (attempt - 1) * 0.03  # Very low for consistency
        
        try:
            response = client.chat.completions.create(
                model=GEMMA_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=600,
                temperature=temperature,
                top_p=0.9,
            )
            output = response.choices[0].message.content.strip()
            
            print(f"  🧠 ANALYSIS (attempt {attempt}, temp={temperature:.2f}):")
            print(f"  {'-'*80}")
            print(output)
            print(f"  {'-'*80}\n")

            # Extract move
            move_match = re.search(r'Best move:\s*([a-h][1-8][a-h][1-8][qrbn]?)', output, re.IGNORECASE)
            if move_match:
                uci = move_match.group(1).lower().strip()
            else:
                candidates = re.findall(r'[a-h][1-8][a-h][1-8][qrbn]?', output.lower())
                uci = candidates[-1] if candidates else None

            if uci:
                try:
                    move = chess.Move.from_uci(uci)
                    if move in board.legal_moves:
                        print(f"  ✅ SELECTED MOVE: {move.uci()}")
                        return move
                except:
                    pass

            print("  🔄 Retrying...")

        except Exception as e:
            print(f"  ❌ API Error: {e}")

    # FINAL FAILSAFE: Pick a strong move if possible
    print("  🚨 FAILSAFE: Choosing strong opening move")
    for strong_uci in ["e2e4", "d2d4", "g1f3", "c2c4", "b1c3"]:
        try:
            move = chess.Move.from_uci(strong_uci)
            if move in board.legal_moves:
                print(f"  ✅ FAILSAFE MOVE: {strong_uci}")
                return move
        except:
            continue
    
    # Ultimate fallback
    move = list(board.legal_moves)[0]
    print(f"  ✅ ULTIMATE FALLBACK: {move.uci()}")
    return move

# =================== GAME SETUP ===================
board = chess.Board()
engine = chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH)
engine.configure({"Threads": 4, "Hash": 2048})

turn_number = 1
running = True

print(f"Starting game: {GEMMA_MODEL} (White) vs Stockfish (Black)")
print("🔥 FINAL VERSION - Clear board + strong guidance + failsafe\n")

draw_board(screen, board)
time.sleep(2)

# =================== MAIN LOOP ===================
try:
    while running and not board.is_game_over():
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        if board.turn == chess.WHITE:
            print(f"\n{'='*90}")
            print(f"🔍 Turn {turn_number} | {GEMMA_MODEL} (White) THINKING...")
            print(f"{'='*90}")
            move = get_move_from_llm(board)
            board.push(move)
            print(f"✅ {GEMMA_MODEL} PLAYS: {move.uci()}")
            print(f"{'='*90}\n")
        else:
            print(f"\nTurn {turn_number} | Stockfish (Black) calculating...")
            result = engine.play(board, chess.engine.Limit(time=THINK_TIME_STOCKFISH))
            move = result.move
            board.push(move)
            print(f"✅ Stockfish played: {move.uci()}")

        turn_number += 1
        draw_board(screen, board)
        time.sleep(1.5)
        clock.tick(FPS)

    if board.is_game_over():
        print("\n" + "="*100)
        print("🎉 GAME OVER 🎉")
        print("="*100)
        result = board.result()
        if result == "1-0":
            print(f"🏆 {GEMMA_MODEL} WINS!")
        elif result == "0-1":
            print("🏆 Stockfish wins.")
        else:
            print("🤝 Draw.")
        print(f"Result: {result}")

        draw_board(screen, board)
        time.sleep(30)

except KeyboardInterrupt:
    print("\n⏹️ Stopped.")
except Exception as e:
    print(f"\n💥 Error: {e}")
finally:
    try:
        engine.quit()
    except:
        pass
    pygame.quit()