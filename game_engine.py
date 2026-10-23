"""
Game Engine module for 2-Player Fruit Ninja CV.
Manages game states, wave spawning, physics updates, collision detection,
scoring, combo mechanics, audio triggers, and hand-controlled Pause/Quit buttons.
"""
import time
import random
import math
import cv2
import numpy as np
import config
import audio
from fruit import Fruit, FruitHalf
from particles import ParticleManager
from ui import UIManager

class GameEngine:
    def __init__(self):
        # Audio & UI
        audio.init(config.AUDIO_SAMPLE_RATE)
        self.ui = UIManager()
        self.particles = ParticleManager()

        # State: 'MENU', 'COUNTDOWN', 'PLAYING', 'GAMEOVER', 'PAUSED'
        self.state = 'MENU'
        self.previous_state = 'MENU'
        self.should_quit = False

        # Timer setup
        self.selected_timer_sec = config.TIMER_PRESETS[config.DEFAULT_TIMER_INDEX]
        self.round_duration = self.selected_timer_sec
        self.round_time_left = self.round_duration
        self.round_start_time = 0.0

        # Countdown state
        self.countdown_val = 3
        self.countdown_timer = 0.0

        # Player stats
        self.reset_player_stats()

        # Fruit entities
        self.fruits = []
        self.fruit_halves = []
        self.last_spawn_time = time.time()
        self.next_spawn_interval = 1.5

        # Interactive Menu/Rematch Fruit
        self.menu_fruit = Fruit(x=config.WINDOW_WIDTH // 2, fruit_type='watermelon')
        self.menu_fruit.y = 265.0
        self.menu_fruit.vy = 0.0
        self.menu_fruit.vx = 0.0
        self.rematch_fruit = None

        self.last_frame_time = time.time()

    def reset_player_stats(self):
        self.p1_stats = {
            'score': 0, 'slices': 0, 'munches': 0, 'bombs': 0,
            'combo_count': 0, 'combo_mult': 1, 'max_combo': 1,
            'last_slice_time': 0.0
        }
        self.p2_stats = {
            'score': 0, 'slices': 0, 'munches': 0, 'bombs': 0,
            'combo_count': 0, 'combo_mult': 1, 'max_combo': 1,
            'last_slice_time': 0.0
        }

    def return_to_menu(self):
        self.state = 'MENU'
        self.fruits.clear()
        self.fruit_halves.clear()
        self.particles.clear()
        self.menu_fruit.sliced = False
        self.menu_fruit.x = float(config.WINDOW_WIDTH // 2)
        self.menu_fruit.y = 265.0
        self.menu_fruit.vy = 0.0
        self.menu_fruit.vx = 0.0
        audio.play('beep')

    def start_countdown(self):
        self.state = 'COUNTDOWN'
        self.countdown_val = 3
        self.countdown_timer = time.time()
        audio.play('beep')

    def handle_click(self, x, y):
        """Instant mouse click handler for all buttons across all game states."""
        if self.state == 'MENU':
            for btn in self.ui.timer_buttons:
                if btn.contains(x, y):
                    self.set_timer_preset(btn.tag)
                    return True
            if self.ui.menu_start_btn.contains(x, y):
                self.start_countdown()
                return True
            if self.ui.menu_restart_btn.contains(x, y):
                self.restart_game()
                return True
            if self.ui.menu_quit_btn.contains(x, y):
                self.should_quit = True
                return True

        elif self.state == 'PLAYING':
            if self.ui.hud_restart_btn.contains(x, y):
                self.restart_game()
                return True
            if self.ui.pause_btn.contains(x, y):
                self.toggle_pause()
                return True
            if self.ui.hud_menu_btn.contains(x, y):
                self.return_to_menu()
                return True
            if self.ui.quit_btn.contains(x, y):
                self.should_quit = True
                return True

        elif self.state == 'PAUSED':
            if self.ui.resume_btn.contains(x, y):
                self.toggle_pause()
                return True
            if self.ui.pause_restart_btn.contains(x, y):
                self.restart_game()
                return True
            if self.ui.pause_menu_btn.contains(x, y):
                self.return_to_menu()
                return True
            if self.ui.pause_quit_btn.contains(x, y):
                self.should_quit = True
                return True

        elif self.state == 'GAMEOVER':
            if self.ui.gameover_rematch_btn.contains(x, y):
                self.start_countdown()
                return True
            if self.ui.gameover_menu_btn.contains(x, y):
                self.return_to_menu()
                return True
            if self.ui.gameover_quit_btn.contains(x, y):
                self.should_quit = True
                return True

        return False

    def start_game(self):
        self.reset_player_stats()
        self.fruits.clear()
        self.fruit_halves.clear()
        self.particles.clear()
        self.round_duration = self.selected_timer_sec
        self.round_time_left = float(self.round_duration)
        self.round_start_time = time.time()
        self.last_spawn_time = time.time()
        self.state = 'PLAYING'
        audio.play('start')

    def toggle_pause(self):
        if self.state == 'PLAYING':
            self.previous_state = 'PLAYING'
            self.state = 'PAUSED'
            audio.play('beep')
        elif self.state == 'PAUSED':
            self.state = self.previous_state
            # Adjust start time so paused duration doesn't consume round timer
            self.last_spawn_time = time.time()
            audio.play('start')

    def set_timer_preset(self, seconds):
        self.selected_timer_sec = seconds
        for btn in self.ui.timer_buttons:
            btn.is_selected = (btn.tag == seconds)
        audio.play('beep')

    def _spawn_wave(self):
        wave_size = random.choices([1, 2, 3, 4], weights=[35, 40, 20, 5])[0]
        for _ in range(wave_size):
            f = Fruit()
            self.fruits.append(f)
        self.next_spawn_interval = random.uniform(config.SPAWN_MIN_INTERVAL, config.SPAWN_MAX_INTERVAL)
        self.last_spawn_time = time.time()

    def update(self, player_data):
        now = time.time()
        dt = max(0.001, min(0.1, now - self.last_frame_time))
        self.last_frame_time = now

        # Update particles and halves
        self.particles.update()
        self.fruit_halves = [h for h in self.fruit_halves if h.update()]

        # Audio blade swoosh
        for pid in (1, 2):
            pinfo = player_data[pid]
            if pinfo['is_slicing'] and pinfo['speed'] > 28.0:
                audio.play('swoosh', player_id=pid, cooldown=0.22)

        # STATE: MENU
        if self.state == 'MENU':
            self._update_menu(player_data, dt)

        # STATE: COUNTDOWN
        elif self.state == 'COUNTDOWN':
            self._update_countdown(now)

        # STATE: PLAYING
        elif self.state == 'PLAYING':
            self._update_playing(player_data, now, dt)

        # STATE: PAUSED
        elif self.state == 'PAUSED':
            self._update_paused(player_data, dt)

        # STATE: GAMEOVER
        elif self.state == 'GAMEOVER':
            self._update_game_over(player_data, dt)

    def _update_menu(self, player_data, dt):
        self.menu_fruit.angle += 1.5
        self.menu_fruit.y = 265.0 + math.sin(time.time() * 3.5) * 8.0

        # Start watermelon can still be munched with mouth
        for pid in (1, 2):
            pinfo = player_data[pid]
            if pinfo['face']['detected'] and pinfo['face']['is_munching'] and pinfo['face']['mouth_center']:
                mx, my = pinfo['face']['mouth_center']
                if self.menu_fruit.check_munch(mx, my):
                    halves = self.menu_fruit.slice()
                    self.fruit_halves.extend(halves)
                    self.particles.add_slice_burst(self.menu_fruit.x, self.menu_fruit.y, self.menu_fruit.juice_color, is_munch=True)
                    audio.play('munch', player_id=pid)
                    self.start_countdown()
                    break

    def _update_countdown(self, now):
        elapsed = now - self.countdown_timer
        if elapsed >= 1.0:
            self.countdown_val -= 1
            self.countdown_timer = now
            if self.countdown_val > 0:
                audio.play('beep')
            elif self.countdown_val == 0:
                audio.play('start')
            else:
                self.start_game()

    def _update_playing(self, player_data, now, dt):
        # 1. Update round timer
        if self.round_duration > 0:
            self.round_time_left = max(0.0, self.round_duration - (now - self.round_start_time))
            if self.round_time_left <= 0.0:
                self.state = 'GAMEOVER'
                audio.play('game_over')
                self.rematch_fruit = Fruit(x=config.WINDOW_WIDTH // 2, fruit_type='watermelon')
                self.rematch_fruit.y = 550.0
                self.rematch_fruit.vy = 0.0
                self.rematch_fruit.vx = 0.0
                return

        # 2. Wave Spawner
        if now - self.last_spawn_time >= self.next_spawn_interval:
            self._spawn_wave()

        # 3. Update fruits
        self.fruits = [f for f in self.fruits if f.update()]

        # 4. Collision Detection: Face/Mouth Munching on Fruits + Hand Blade Slicing on Bombs
        for pid in (1, 2):
            pinfo = player_data[pid]
            pstats = self.p1_stats if pid == 1 else self.p2_stats
            cfg = config.PLAYER_1 if pid == 1 else config.PLAYER_2

            # Reset combo window
            if now - pstats['last_slice_time'] > config.COMBO_TIME_WINDOW:
                pstats['combo_count'] = 0
                pstats['combo_mult'] = 1

            # --- A. MOUTH MUNCHING MECHANIC (For Fruits) ---
            face = pinfo['face']
            if face['detected'] and face['mouth_center']:
                mx, my = face['mouth_center']
                # Check each fruit for mouth collision
                for fruit in self.fruits:
                    if fruit.sliced:
                        continue
                    if fruit.is_bomb:
                        # Eating a bomb with mouth reduces points!
                        if face['is_munching'] and fruit.check_munch(mx, my, munch_radius=config.MUNCH_COLLISION_RADIUS):
                            halves = fruit.slice(random.uniform(0, math.pi * 2))
                            self.fruit_halves.extend(halves)
                            self.particles.add_slice_burst(fruit.x, fruit.y, fruit.juice_color, is_bomb=True)

                            audio.play('bomb', player_id=pid)
                            pstats['bombs'] += 1
                            pstats['score'] = max(0, pstats['score'] - 30)  # Eating bomb penalty!
                            pstats['combo_count'] = 0
                            pstats['combo_mult'] = 1
                            self.particles.add_floating_text(fruit.x, fruit.y, "-30 ATE BOMB!", (0, 0, 255), scale=1.1)
                        continue

                    # Regular fruit: munch when mouth is open and near fruit (adds points + combo!)
                    if face['is_munching'] and fruit.check_munch(mx, my, munch_radius=config.MUNCH_COLLISION_RADIUS):
                        halves = fruit.slice(random.uniform(0, math.pi * 2))
                        self.fruit_halves.extend(halves)
                        self.particles.add_slice_burst(fruit.x, fruit.y, fruit.juice_color, is_bomb=False, is_munch=True)

                        audio.play('munch', player_id=pid)
                        pstats['munches'] += 1
                        pstats['slices'] += 1
                        pstats['last_slice_time'] = now
                        pstats['combo_count'] += 1

                        if pstats['combo_count'] >= 4:
                            pstats['combo_mult'] = 3
                        elif pstats['combo_count'] >= 2:
                            pstats['combo_mult'] = 2
                        else:
                            pstats['combo_mult'] = 1

                        if pstats['combo_mult'] > pstats['max_combo']:
                            pstats['max_combo'] = pstats['combo_mult']

                        points_earned = fruit.points * pstats['combo_mult']
                        pstats['score'] += points_earned

                        # Visual floating feedback
                        if pstats['combo_mult'] > 1:
                            audio.play('combo', player_id=pid, cooldown=0.15)
                            self.particles.add_floating_text(fruit.x, fruit.y - 30,
                                                             f"MUNCH COMBO x{pstats['combo_mult']}!",
                                                             (50, 255, 120), scale=1.0)

                        self.particles.add_floating_text(fruit.x, fruit.y,
                                                         f"CHOMP! +{points_earned}",
                                                         cfg['color'], scale=0.95)

            # --- B. HAND BLADE SLICING MECHANIC (For Bombs & Interactive Items) ---
            if not pinfo['is_slicing'] or not pinfo['prev_pos'] or not pinfo['pos']:
                continue

            p1 = pinfo['prev_pos']
            p2 = pinfo['pos']
            slice_angle = math.atan2(p2[1] - p1[1], p2[0] - p1[0])

            for fruit in self.fruits:
                if not fruit.sliced and fruit.check_slice(p1, p2):
                    if fruit.is_bomb:
                        # Slashing a bomb adds points (+25 points award!)
                        halves = fruit.slice(slice_angle)
                        self.fruit_halves.extend(halves)
                        self.particles.add_slice_burst(fruit.x, fruit.y, fruit.juice_color, is_bomb=True)

                        audio.play('bomb', player_id=pid)
                        pstats['bombs'] += 1
                        bomb_points = 25
                        pstats['score'] += bomb_points
                        pstats['last_slice_time'] = now
                        self.particles.add_floating_text(fruit.x, fruit.y, f"+{bomb_points} BOMB SLASHED!", (0, 240, 255), scale=1.1)
                    else:
                        # Fruit sliced by hand: 0 points awarded (only mouth munching scores points for fruits!)
                        halves = fruit.slice(slice_angle)
                        self.fruit_halves.extend(halves)
                        self.particles.add_slice_burst(fruit.x, fruit.y, fruit.juice_color, is_bomb=False)

                        audio.play('slice', player_id=pid)
                        pstats['slices'] += 1
                        self.particles.add_floating_text(fruit.x, fruit.y, "+0 (MUNCH ONLY!)", (180, 180, 190), scale=0.85)

    def _update_paused(self, player_data, dt):
        pass

    def _update_game_over(self, player_data, dt):
        # Rematch watermelon can be munched with mouth
        if self.rematch_fruit:
            self.rematch_fruit.angle += 1.5
            self.rematch_fruit.y = 550.0 + math.sin(time.time() * 3.5) * 8.0

            for pid in (1, 2):
                pinfo = player_data[pid]
                if pinfo['face']['detected'] and pinfo['face']['is_munching'] and pinfo['face']['mouth_center']:
                    mx, my = pinfo['face']['mouth_center']
                    if self.rematch_fruit.check_munch(mx, my):
                        halves = self.rematch_fruit.slice()
                        self.fruit_halves.extend(halves)
                        self.particles.add_slice_burst(self.rematch_fruit.x, self.rematch_fruit.y, self.rematch_fruit.juice_color, is_munch=True)
                        audio.play('munch', player_id=pid)
                        self.start_countdown()
                        break

    def draw(self, canvas, player_data):
        for half in self.fruit_halves:
            half.draw(canvas)

        for fruit in self.fruits:
            fruit.draw(canvas)

        self.particles.draw(canvas)

        if self.state == 'MENU':
            self.ui.draw_menu(canvas, self.selected_timer_sec)
            if not self.menu_fruit.sliced:
                self.menu_fruit.draw(canvas)

        elif self.state == 'COUNTDOWN':
            self.ui.draw_hud(canvas, self.p1_stats, self.p2_stats,
                             self.selected_timer_sec, self.selected_timer_sec,
                             is_endless=(self.selected_timer_sec == 0))
            self.ui.draw_countdown(canvas, self.countdown_val)

        elif self.state == 'PLAYING':
            self.ui.draw_hud(canvas, self.p1_stats, self.p2_stats,
                             self.round_time_left, self.round_duration,
                             is_endless=(self.round_duration == 0))

        elif self.state == 'PAUSED':
            self.ui.draw_hud(canvas, self.p1_stats, self.p2_stats,
                             self.round_time_left, self.round_duration,
                             is_endless=(self.round_duration == 0))
            self.ui.draw_paused(canvas)

        elif self.state == 'GAMEOVER':
            self.ui.draw_game_over(canvas, self.p1_stats, self.p2_stats)
            if self.rematch_fruit and not self.rematch_fruit.sliced:
                self.rematch_fruit.draw(canvas)
