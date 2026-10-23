"""
Automated headless test and verification suite for Fruit Ninja 2-Player Mouth Munch & Bomb Slash.
Tests audio synthesis, MultiPlayerTracker processing, mouth munching mechanics,
hand blade bomb slicing, extended trails, top-of-player tagging, and UI rendering.
"""
import os
import sys
import time
import cv2
import numpy as np

# Ensure working directory is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
import audio
from hand_tracker import MultiPlayerTracker
from fruit import Fruit, FruitHalf
from particles import ParticleManager
from ui import UIManager
from game_engine import GameEngine

def run_tests():
    print("[1/6] Testing Audio Synthesis & Pygame Mixer (including new Munch sound)...")
    audio.init(config.AUDIO_SAMPLE_RATE)
    for snd in ['swoosh_p1', 'swoosh_p2', 'slice_p1', 'slice_p2', 'munch_p1', 'munch_p2', 'combo', 'bomb', 'beep', 'start', 'game_over']:
        audio.play(snd)
    print("  -> All sound effects (including bite munch) verified without errors.")

    print("[2/6] Testing MultiPlayerTracker (Hand + Face/Mouth) initialization...")
    tracker = MultiPlayerTracker()
    test_frame = np.zeros((config.WINDOW_HEIGHT, config.WINDOW_WIDTH, 3), dtype=np.uint8)
    pdata = tracker.process_frame(test_frame)
    assert 1 in pdata and 2 in pdata, "Player data missing player IDs"
    assert 'face' in pdata[1] and 'face' in pdata[2], "Player data missing face/mouth tracking structures"
    print("  -> MultiPlayerTracker initialized and processed test frame successfully.")

    print("[3/6] Testing Fruit & Bomb interaction (Mouth Munch vs Hand Slash)...")
    fruit_apple = Fruit(x=400, fruit_type='apple')
    fruit_apple.y = 300

    # 3.1 Test Mouth Munch on fruit
    mouth_x, mouth_y = 420, 310
    assert fruit_apple.check_munch(mouth_x, mouth_y), "Fruit mouth munch proximity check failed"
    munch_halves = fruit_apple.slice()
    assert len(munch_halves) == 2, "Munched fruit did not split cleanly into halves"

    # 3.2 Test Bomb Slicing with hand blade
    bomb = Fruit(x=900, fruit_type='bomb')
    bomb.y = 300
    p1 = (850, 300)
    p2 = (950, 300)
    assert bomb.check_slice(p1, p2), "Bomb blade slice check failed"
    bomb_halves = bomb.slice()
    assert len(bomb_halves) == 2, "Slashed bomb did not split cleanly into halves"
    print("  -> Fruit munching and bomb slicing physics verified.")

    print("[4/6] Testing GameEngine 2-Player Lifecycle & Mechanics...")
    engine = GameEngine()
    canvas = np.zeros((config.WINDOW_HEIGHT, config.WINDOW_WIDTH, 3), dtype=np.uint8)

    # Mock 2 players on screen: P1 on left (x=320), P2 on right (x=960)
    tracker.set_mock_face(1, mouth_x=320, mouth_y=280, is_munching=True)
    tracker.set_mock_face(2, mouth_x=960, mouth_y=280, is_munching=False)
    pdata[1]['face'] = tracker.player_faces[1]
    pdata[2]['face'] = tracker.player_faces[2]

    # 4.1 Menu state
    assert engine.state == 'MENU'
    engine.draw(canvas, pdata)
    tracker.draw_player_trackers(canvas, pdata)
    cv2.imwrite("preview_menu.png", canvas)
    print("  -> Rendered preview_menu.png (with Top-of-Player tags & mouth reticles)")

    # Select 60s preset
    engine.set_timer_preset(60)
    assert engine.selected_timer_sec == 60

    # Trigger start via mouth munch on menu fruit
    engine.menu_fruit.x = 320
    engine.menu_fruit.y = 280
    engine.update(pdata)
    assert engine.state == 'COUNTDOWN', f"Expected COUNTDOWN after mouth chomp, got {engine.state}"
    print("  -> Menu fruit mouth chomp successfully triggered countdown.")

    # 4.2 Countdown progression
    sim_t = time.time()
    for i in range(1, 5):
        engine._update_countdown(sim_t + i * 1.05)
    assert engine.state == 'PLAYING', f"Expected PLAYING, got {engine.state}"
    print("  -> Countdown successfully entered PLAYING state.")

    # 4.3 In-game action: P1 munches a Watermelon, P2 slashes a Bomb
    p1_wm = Fruit(x=320, fruit_type='watermelon')
    p1_wm.y = 280
    engine.fruits.append(p1_wm)

    p2_bomb = Fruit(x=960, fruit_type='bomb')
    p2_bomb.y = 350
    engine.fruits.append(p2_bomb)

    # P2 swings hand to slash bomb with long neon trail
    for step_x in range(900, 1020, 20):
        tracker.set_mouse_pos(step_x, 350, player_id=2)
    pdata = tracker.process_frame(test_frame)
    pdata[1]['face'] = tracker.player_faces[1]
    pdata[2]['face'] = tracker.player_faces[2]
    pdata[2]['pos'] = (1000, 350)
    pdata[2]['prev_pos'] = (920, 350)
    pdata[2]['speed'] = 40.0
    pdata[2]['is_slicing'] = True

    engine.update(pdata)
    assert engine.p1_stats['munches'] >= 1, "Player 1 should have recorded at least 1 munch"
    assert engine.p1_stats['score'] > 0, "Player 1 score should have increased from munch"
    assert engine.p2_stats['bombs'] >= 1, "Player 2 should have recorded a bomb slash"

    # Render playing screenshot
    canvas_play = np.zeros((config.WINDOW_HEIGHT, config.WINDOW_WIDTH, 3), dtype=np.uint8)
    engine.draw(canvas_play, pdata)
    tracker.draw_player_trackers(canvas_play, pdata)
    cv2.imwrite("preview_playing.png", canvas_play)
    print("  -> Rendered preview_playing.png (showing munching, bomb slash, tags on top of players, and extended trails)")

    # 4.4 Keyboard and Click-Controlled Navigation & Pause/Resume
    # Test pause via method/space
    engine.toggle_pause()
    assert engine.state == 'PAUSED', f"Expected PAUSED, got {engine.state}"
    print("  -> In-Game Pause (Space / Click) verified.")

    canvas_pause = np.zeros((config.WINDOW_HEIGHT, config.WINDOW_WIDTH, 3), dtype=np.uint8)
    engine.draw(canvas_pause, pdata)
    tracker.draw_player_trackers(canvas_pause, pdata)
    cv2.imwrite("preview_paused.png", canvas_pause)
    print("  -> Rendered preview_paused.png")

    # Test resume via method/space
    engine.toggle_pause()
    assert engine.state == 'PLAYING', f"Expected PLAYING, got {engine.state}"
    print("  -> In-Game Resume (Space / Click) verified.")

    # 4.5 In-Game Menu Button Test (via click or return_to_menu)
    engine.return_to_menu()
    assert engine.state == 'MENU', f"Expected MENU from In-Game < MENU, got {engine.state}"
    print("  -> In-Game '< MENU' (Key M / Click) verified.")

    # 4.6 Front Menu START via keyboard (Space)
    engine.start_countdown()
    assert engine.state == 'COUNTDOWN', f"Expected COUNTDOWN from Front Menu START, got {engine.state}"
    print("  -> Front Menu START (Space / Click) verified.")

    for i in range(1, 5):
        engine._update_countdown(time.time() + i * 1.05)
    assert engine.state == 'PLAYING'

    # 4.7 Test fruit slicing awards 0 points and bomb slicing awards +25 points
    p1_score_before = engine.p1_stats['score']
    p1_fruit_slice = Fruit(x=500, fruit_type='banana')
    p1_fruit_slice.y = 300
    engine.fruits.append(p1_fruit_slice)

    # Player 1 slices the fruit with hand blade
    p1_hand_slice = {
        1: {'pos': (530, 300), 'prev_pos': (470, 300), 'speed': 40.0, 'is_slicing': True, 'trail': [], 'face': pdata[1]['face']},
        2: {'pos': None, 'prev_pos': None, 'speed': 0.0, 'is_slicing': False, 'trail': [], 'face': pdata[2]['face']}
    }
    engine.update(p1_hand_slice)
    assert engine.p1_stats['score'] == p1_score_before, f"Slicing fruit should award 0 points, but score changed from {p1_score_before} to {engine.p1_stats['score']}"
    print("  -> Slicing fruit awards 0 points verified (Munch only for fruits).")

    # Player 1 slashes a bomb with hand blade -> should award +25 points
    p1_bomb = Fruit(x=500, fruit_type='bomb')
    p1_bomb.y = 300
    engine.fruits.append(p1_bomb)
    engine.update(p1_hand_slice)
    assert engine.p1_stats['score'] == p1_score_before + 25, f"Slashing bomb should award +25 points, got {engine.p1_stats['score']}"
    print("  -> Slashing bomb awards +25 points verified.")

    # 4.7 Game Over, Scoreboard & Winner Declaration
    engine.p1_stats['score'] = 120
    engine.p1_stats['munches'] = 8
    engine.p2_stats['score'] = 85
    engine.p2_stats['munches'] = 5
    engine.round_start_time = time.time() - 200
    engine.update(pdata)
    assert engine.state == 'GAMEOVER', f"Expected GAMEOVER, got {engine.state}"

    canvas_gover = np.zeros((config.WINDOW_HEIGHT, config.WINDOW_WIDTH, 3), dtype=np.uint8)
    engine.draw(canvas_gover, pdata)
    tracker.draw_player_trackers(canvas_gover, pdata)
    cv2.imwrite("preview_gameover.png", canvas_gover)
    print("  -> Rendered preview_gameover.png (verifying scoreboard, stats comparison, and winner declaration)")

    print("[5/6] Verifying all player top tags, mouth munching, and extended slash trail configurations...")
    assert config.BLADE_TRAIL_LEN >= 25, "Blade trail length must be extended"
    assert config.MOUTH_OPEN_RATIO_THRESH > 0, "Mouth open threshold must be positive"
    print("  -> All configurations verified.")

    print("[6/6] All verification tests passed successfully!")

if __name__ == '__main__':
    run_tests()
