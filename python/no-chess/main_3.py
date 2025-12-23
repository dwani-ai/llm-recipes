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
THINK_TIME_OUR = 1.0  # Not used anymore for our moves, but kept for compatibility
THINK_TIME_OPP = 2.0  # Seconds for opponent (perfect play)
BOARD_SIZE = 800
SQUARE_SIZE = BOARD_SIZE // 8
DEBUG_DIR = "debug_images"
os.makedirs(DEBUG_DIR, exist_ok=True)

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
WHITE_PIECE_COLOR = (0, 0, 0)  # Black for white pieces (high contrast)
BLACK_PIECE_COLOR = (0, 0, 0)  # Black for black pieces

# OpenAI
openai_client = OpenAI(api_key=OPENAI_API_KEY)

# Stockfish engine (shared, only for opponent)
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

def get_placement_from_screenshot(b64_image, turn_number):
    """Parse piece placement from board screenshot using OpenAI Vision"""

    model_name = "gemma3"  # Switched to "gpt-oss" as "gemma3" appears to ignore images; revert if needed
    client = get_openai_client(model_name)

    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": """You are an expert at parsing chessboard screenshots into FEN piece placements. The board has white pieces at the bottom (ranks 1-2 initially), black at the top (ranks 7-8). Use these rules:
- Uppercase for White: P=pawn, N=knight, B=bishop, R=rook, Q=queen, K=king.
- Lowercase for Black: p=pawn, n=knight, b=bishop, r=rook, q=queen, k=king.
- Numbers for consecutive empty squares per row (e.g., 8 for empty row).
- Output ONLY the 8-row placement string separated by /, no extra text or explanations.

Examples:
1. Starting position: rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR
2. After white e4, black c5 (Sicilian): rnbqkbnr/pp1ppppp/8/2p5/4P3/8/PPPP1PPP/RNBQKBNR
3. After white e4, black e6 (French): rnbqkbnr/pppp1ppp/4p3/8/4P3/8/PPPP1PPP/RNBQKBNR
4. Midgame with capture: rnb1kbnr/ppqQ3p/PqpPpPPp/1PPp1p2/3p4/5NPP/PPP4P/RNBq3K (detect moved pieces, empties, and captures accurately).

Now, analyze this screenshot and output ONLY the placement."""
                    },
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64_image}"}}
                ]
            }
        ],
        max_tokens=100,
        temperature=0.0  # More deterministic
    )
    # Logging the vision model output
    print(f"\n--- Vision Model Logging (Turn {turn_number}) ---")
    print("Full response object:", response)
    content = response.choices[0].message.content
    print("Raw content:", repr(content))  # Use repr to show newlines/escapes
    print("--- End Vision Model Logging ---\n")
    
    placement = content.strip()
    if '/' not in placement or len(placement.split('/')) != 8:
        raise ValueError("Invalid placement parsed")
    return placement

def get_move_from_openai(current_board):
    """Get the next move for White from OpenAI."""
    model_name = "gemma3"  # Use the same as vision or change to "gemma3" if preferred for text
    client = get_openai_client(model_name)
    
    fen = current_board.fen()
    prompt = f"You are a chess grandmaster. Given this FEN: {fen} (White to move), suggest the best move in UCI format (e.g., e2e4). Output ONLY the move, no extra text."
    
    for attempt in range(3):  # Retry up to 3 times if invalid
        response = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=10,
            temperature=0.0
        )
        move_str = response.choices[0].message.content.strip()
        print(f"OpenAI suggested move: {move_str}")
        
        try:
            move = chess.Move.from_uci(move_str)
            if move in current_board.legal_moves:
                return move
            else:
                print(f"Invalid move {move_str} (not legal), retrying...")
        except ValueError:
            print(f"Invalid UCI format {move_str}, retrying...")
    
    raise ValueError("Failed to get a valid move from OpenAI after retries.")

# Game setup: We (White, vision-bot with OpenAI moves) vs Opponent (Black, perfect Stockfish)
game_board = chess.Board()
our_turn = True  # White to move first
turn_counter = 1  # To track turns for logging/images

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
        time.sleep(0.5)  # Increased wait time to ensure display is fully updated before screenshot

        if our_turn:
            # Our turn (always White)
            print("\nOur turn (White)...")
            b64_image = get_board_screenshot_b64(screen)
            # Save screenshot for debugging
            image_path = os.path.join(DEBUG_DIR, f"turn_{turn_counter}_white.png")
            with open(image_path, 'wb') as f:
                f.write(base64.b64decode(b64_image))
            print(f"Saved screenshot to: {image_path}")
            
            placement = get_placement_from_screenshot(b64_image, turn_counter)
            print("Parsed placement:", placement)
            print("Actual placement:", game_board.board_fen())  # For comparison

            # Validation: Check for mismatch and retry/fallback
            use_internal = False
            expected_placement = game_board.board_fen()
            if placement != expected_placement:
                print(f"Vision parse mismatch on turn {turn_counter}! Expected: {expected_placement}, Parsed: {placement}")
                # Retry vision once
                print("Retrying vision parse...")
                placement = get_placement_from_screenshot(b64_image, turn_counter)
                if placement != expected_placement:
                    print("Retry failed. Falling back to internal board state.")
                    use_internal = True
                else:
                    print("Retry successful.")
            else:
                print("Vision parse matches.")

            # Now set current_board based on validation
            if MODE == 1 and not use_internal:
                fen = f"{placement} w KQkq - 0 1"
                print("Mode 1 FEN:", fen)
                try:
                    current_board = chess.Board(fen)
                    # Validate basic position (e.g., kings present)
                    if current_board.king(chess.WHITE) is None or current_board.king(chess.BLACK) is None:
                        raise ValueError("Invalid chess position: Missing king(s)")
                except ValueError as e:
                    print(f"Error creating board: {e}")
                    print("Falling back to full board state.")
                    current_board = game_board
                    use_internal = True
            else:
                current_board = game_board
                if MODE == 1:
                    print("Using internal state for this turn (fallback).")
                else:
                    print("Mode 2: Using full board state")

            # Compute and play move using OpenAI
            print("Thinking with OpenAI...")
            move = get_move_from_openai(current_board)
            print("Our move:", move)
            game_board.push(move)
            print("Board after our move:\n", game_board)
            
            turn_counter += 1

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