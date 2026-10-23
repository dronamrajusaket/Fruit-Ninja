"""
Fruit Ninja 2-Player Edition with Face/Mouth Munching & Hand Bomb Slashing.
Main entry point.
"""
import sys
import time
import cv2
import numpy as np
import config
from hand_tracker import MultiPlayerTracker
from game_engine import GameEngine

# Global mouse state for fallback testing & instant UI clicking
mouse_x, mouse_y = -1, -1
mouse_down = False
mouse_player_id = 1
engine_ref = None

def on_mouse(event, x, y, flags, param):
    global mouse_x, mouse_y, mouse_down, mouse_player_id, engine_ref
    mouse_x, mouse_y = x, y
    if event == cv2.EVENT_LBUTTONDOWN:
        mouse_down = True
        mouse_player_id = 1
        if engine_ref:
            engine_ref.handle_click(x, y)
    elif event == cv2.EVENT_RBUTTONDOWN:
        mouse_down = True
        mouse_player_id = 2
        if engine_ref:
            engine_ref.handle_click(x, y)
    elif event == cv2.EVENT_LBUTTONUP or event == cv2.EVENT_RBUTTONUP:
        mouse_down = False

def main():
    global engine_ref
    print("=" * 65)
    print("  FRUIT NINJA - 2 PLAYER MOUTH MUNCH & BOMB SLASH (OpenCV)")
    print("=" * 65)
    print("Controls & Rules:")
    print(" - Player 1 (Left Side): Mentioned as PLAYER 1 on top of player's head")
    print(" - Player 2 (Right Side): Mentioned as PLAYER 2 on top of player's head")
    print(" - MUNCH FRUITS: Open mouth and move face to chomp fruits (+Points & Combos)!")
    print(" - SLASH BOMBS: Swing hand blade across bombs with long neon trails (+25 Points)!")
    print(" - EATING BOMBS: Chomp on a bomb with your mouth = -30 Points penalty!")
    print(" - Instant Buttons: Click or slice [RESTART], [PAUSE], [MENU], [QUIT]")
    print(" - Keys: [Space] Start/Pause | [P] Pause | [1-5] Timer | [R] Restart | [M] Menu | [Q] Quit")
    print(" - Mouse Fallback: Left-Click = P1 Blade/Munch, Right-Click = P2 Blade/Munch")
    print("=" * 65)

    # Initialize Camera
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cap.isOpened():
        print("[Warning] Could not open camera with DSHOW, trying default backend...")
        cap = cv2.VideoCapture(0)

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.WINDOW_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.WINDOW_HEIGHT)

    # Initialize Multi-Modal Tracker & Game Engine
    print("[Init] Loading Hand & Face Landmarker models...")
    tracker = MultiPlayerTracker()
    print("[Init] Hand & Face models loaded successfully!")

    engine = GameEngine()
    engine_ref = engine

    window_name = config.WINDOW_TITLE
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, config.WINDOW_WIDTH, config.WINDOW_HEIGHT)
    cv2.setMouseCallback(window_name, on_mouse)

    fps_timer = time.time()
    fps_count = 0
    current_fps = 30.0

    while True:
        ret, frame = cap.read()
        if not ret or frame is None:
            frame = np.zeros((config.WINDOW_HEIGHT, config.WINDOW_WIDTH, 3), dtype=np.uint8)
        else:
            if frame.shape[1] != config.WINDOW_WIDTH or frame.shape[0] != config.WINDOW_HEIGHT:
                frame = cv2.resize(frame, (config.WINDOW_WIDTH, config.WINDOW_HEIGHT))
            frame = cv2.flip(frame, 1)

        # Subtle contrast grading on webcam feed to make neon blades & fruits pop
        frame = cv2.convertScaleAbs(frame, alpha=0.88, beta=-8)

        # Process Hands & Faces for both players
        player_data = tracker.process_frame(frame)

        # Mouse fallback integration
        if mouse_down and mouse_x >= 0 and mouse_y >= 0:
            tracker.set_mouse_pos(mouse_x, mouse_y, player_id=mouse_player_id)
            player_data[mouse_player_id]['pos'] = (mouse_x, mouse_y)
            player_data[mouse_player_id]['prev_pos'] = tracker.player_prev_pos[mouse_player_id]
            player_data[mouse_player_id]['speed'] = tracker.player_speeds[mouse_player_id]
            player_data[mouse_player_id]['is_slicing'] = tracker.player_speeds[mouse_player_id] >= config.MIN_SLICE_SPEED
            player_data[mouse_player_id]['trail'] = list(tracker.player_trails[mouse_player_id])
            # If no face detected, also mock mouth munch at mouse location
            if not player_data[mouse_player_id]['face']['detected']:
                player_data[mouse_player_id]['face'] = {
                    'detected': True,
                    'mouth_center': (mouse_x, mouse_y),
                    'face_center': (mouse_x, mouse_y - 40),
                    'mouth_ratio': 0.35,
                    'is_munching': True,
                    'box': (mouse_x - 50, mouse_y - 80, 100, 120)
                }

        # Update Game Engine State & Physics
        engine.update(player_data)

        # Check if Hand-Controlled Quit was triggered
        if engine.should_quit:
            print("[Game] Hand-controlled Quit triggered.")
            break

        # Render Game Elements (Fruits, Halves, Particles, HUD)
        engine.draw(frame, player_data)

        # Render Player Tags (on top of players), Mouth Reticles, and Extended Glowing Blade Trails
        tracker.draw_player_trackers(frame, player_data)

        # FPS indicator
        fps_count += 1
        now = time.time()
        if now - fps_timer >= 1.0:
            current_fps = fps_count / (now - fps_timer)
            fps_count = 0
            fps_timer = now
        cv2.putText(frame, f"{int(current_fps)} FPS", (config.WINDOW_WIDTH - 85, config.WINDOW_HEIGHT - 12),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (120, 140, 150), 1, cv2.LINE_AA)

        # Display Frame
        cv2.imshow(window_name, frame)

        # Keyboard Event Handling
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q') or key == 27:  # Q or ESC
            break
        elif key == 32:  # Space
            if engine.state == 'MENU':
                engine.start_countdown()
            elif engine.state in ('PLAYING', 'PAUSED'):
                engine.toggle_pause()
            elif engine.state == 'GAMEOVER':
                engine.start_countdown()
        elif key == ord('p') or key == ord('P'):
            engine.toggle_pause()
        elif key == ord('r') or key == ord('R'):
            engine.restart_game()
        elif key == ord('m') or key == ord('M'):
            engine.return_to_menu()
        elif key in (ord('1'), ord('2'), ord('3'), ord('4'), ord('5')):
            idx = key - ord('1')
            if 0 <= idx < len(config.TIMER_PRESETS):
                engine.set_timer_preset(config.TIMER_PRESETS[idx])

    cap.release()
    cv2.destroyAllWindows()
    print("[Shutdown] Game closed cleanly.")

if __name__ == '__main__':
    main()
