"""
Interactive User Interface and HUD renderer for 2-Player Fruit Ninja CV.
Renders arcade HUDs, interactive hover/slice buttons, countdowns, and Game Over podiums.
"""
import time
import math
import cv2
import numpy as np
import config

def draw_glass_panel(canvas, x1, y1, x2, y2, bg_color=(20, 20, 25), alpha=0.65, border_color=None, border_thickness=2):
    """Draw a semi-transparent dark rounded HUD panel with optional neon border."""
    h, w, _ = canvas.shape
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(w, x2), min(h, y2)
    if x2 <= x1 or y2 <= y1:
        return

    sub_img = canvas[y1:y2, x1:x2]
    rect = np.full(sub_img.shape, bg_color, dtype=np.uint8)
    res = cv2.addWeighted(sub_img, 1.0 - alpha, rect, alpha, 0)
    canvas[y1:y2, x1:x2] = res

    if border_color is not None:
        cv2.rectangle(canvas, (x1, y1), (x2, y2), border_color, border_thickness, cv2.LINE_AA)

class Button:
    """Interactive button that can be clicked by mouse or hovered/sliced by hand blade."""
    def __init__(self, x, y, w, h, text, tag=None):
        self.x = int(x)
        self.y = int(y)
        self.w = int(w)
        self.h = int(h)
        self.text = text
        self.tag = tag
        self.hover_progress = 0.0  # 0.0 to 1.0
        self.is_selected = False
        self.hover_time_required = 0.5  # Snappy, responsive hover time
        self.triggered = False

    def contains(self, px, py):
        # Add hysteresis padding if already hovering to prevent jitter reset
        pad = 18 if self.hover_progress > 0 else 0
        return (self.x - pad <= px <= self.x + self.w + pad) and (self.y - pad <= py <= self.y + self.h + pad)

    def check_slice(self, p1, p2):
        """Check if blade path crosses the button bounding box."""
        bx1, by1 = self.x, self.y
        bx2, by2 = self.x + self.w, self.y + self.h
        x1, y1 = p1
        x2, y2 = p2
        # Check endpoints and midpoint of slice
        mx, my = (x1 + x2) / 2.0, (y1 + y2) / 2.0
        return self.contains(x1, y1) or self.contains(x2, y2) or self.contains(mx, my)

    def update_hover(self, is_hovered, dt):
        # Hover selection disabled per user request (takes too much time)
        return False

    def draw(self, canvas, base_color=(60, 60, 70), active_color=(0, 215, 255)):
        color = active_color if (self.is_selected or self.hover_progress > 0) else base_color
        # Panel
        draw_glass_panel(canvas, self.x, self.y, self.x + self.w, self.y + self.h,
                         bg_color=(25, 28, 35), alpha=0.75,
                         border_color=color, border_thickness=3 if (self.is_selected or self.hover_progress > 0) else 1)

        # Draw hover progress fill if hovering
        if self.hover_progress > 0:
            fill_w = int(self.w * self.hover_progress)
            draw_glass_panel(canvas, self.x, self.y + self.h - 6, self.x + fill_w, self.y + self.h,
                             bg_color=active_color, alpha=0.9)

        # Text
        (tw, th), _ = cv2.getTextSize(self.text, cv2.FONT_HERSHEY_DUPLEX, 0.65, 1)
        tx = self.x + (self.w - tw) // 2
        ty = self.y + (self.h + th) // 2
        tcolor = (255, 255, 255) if not self.is_selected else active_color
        cv2.putText(canvas, self.text, (tx, ty), cv2.FONT_HERSHEY_DUPLEX, 0.65, tcolor, 1, cv2.LINE_AA)

class UIManager:
    def __init__(self):
        # Setup Timer buttons
        self.timer_buttons = []
        labels = ["30s", "60s (Default)", "90s", "120s", "Endless"]
        btn_w, btn_h = 170, 52
        total_w = len(labels) * (btn_w + 16) - 16
        start_x = (config.WINDOW_WIDTH - total_w) // 2
        y_pos = 460

        for i, (preset, label) in enumerate(zip(config.TIMER_PRESETS, labels)):
            bx = start_x + i * (btn_w + 16)
            btn = Button(bx, y_pos, btn_w, btn_h, label, tag=preset)
            if i == config.DEFAULT_TIMER_INDEX:
                btn.is_selected = True
            self.timer_buttons.append(btn)

        # In-game Top Navigation Bar: [RESTART], [|| PAUSE], [< MENU], [X QUIT]
        # Positioned with zero overlap:
        # P1 HUD is x:16..290. P2 HUD is x:990..1264. Center timer is x:540..740.
        # Left cluster: [RESTART] x:305..415, [|| PAUSE] x:425..525
        # Right cluster: [< MENU] x:755..860, [X QUIT] x:870..975
        self.hud_restart_btn = Button(305, 24, 110, 44, "RESTART", tag='restart')
        self.pause_btn = Button(425, 24, 100, 44, "|| PAUSE", tag='pause')
        self.hud_menu_btn = Button(755, 24, 105, 44, "< MENU", tag='menu')
        self.quit_btn = Button(870, 24, 105, 44, "X QUIT", tag='quit')

        # Pause Menu Buttons (Resume, Restart, Menu, Quit)
        self.resume_btn = Button(config.WINDOW_WIDTH // 2 - 320, 420, 145, 54, "> RESUME", tag='resume')
        self.pause_restart_btn = Button(config.WINDOW_WIDTH // 2 - 160, 420, 145, 54, "RESTART", tag='restart')
        self.pause_menu_btn = Button(config.WINDOW_WIDTH // 2 + 15, 420, 145, 54, "< MENU", tag='menu')
        self.pause_quit_btn = Button(config.WINDOW_WIDTH // 2 + 175, 420, 145, 54, "X QUIT", tag='quit')

        # Front / Main Menu Control Buttons (Start, Restart/Reset, Quit)
        self.menu_start_btn = Button(config.WINDOW_WIDTH // 2 - 250, 530, 150, 50, "> START", tag='start')
        self.menu_restart_btn = Button(config.WINDOW_WIDTH // 2 - 75, 530, 150, 50, "RESTART", tag='restart')
        self.menu_quit_btn = Button(config.WINDOW_WIDTH // 2 + 100, 530, 150, 50, "X QUIT", tag='quit')

        # Game Over Control Buttons (Rematch/Restart, Main Menu, Quit)
        self.gameover_rematch_btn = Button(config.WINDOW_WIDTH // 2 - 260, 595, 160, 50, "REMATCH", tag='rematch')
        self.gameover_menu_btn = Button(config.WINDOW_WIDTH // 2 - 80, 595, 160, 50, "< MENU", tag='menu')
        self.gameover_quit_btn = Button(config.WINDOW_WIDTH // 2 + 100, 595, 160, 50, "X QUIT", tag='quit')

    def draw_hud(self, canvas, p1_stats, p2_stats, time_left, max_time, is_endless=False):
        """Draw in-game dual scoreboards, top countdown timer, and hand-controllable Pause/Quit buttons."""
        # 1. Subtle central divider line
        mid_x = config.WINDOW_WIDTH // 2
        for y in range(80, config.WINDOW_HEIGHT, 30):
            cv2.line(canvas, (mid_x, y), (mid_x, y + 15), (70, 70, 70), 1, cv2.LINE_AA)

        # 2. Player 1 HUD (Top-Left)
        p1_cfg = config.PLAYER_1
        draw_glass_panel(canvas, 16, 16, 290, 118, bg_color=(20, 24, 30), alpha=0.8,
                         border_color=p1_cfg['color'], border_thickness=2)
        cv2.circle(canvas, (36, 42), 8, p1_cfg['color'], -1, cv2.LINE_AA)
        cv2.putText(canvas, p1_cfg['name'], (52, 48), cv2.FONT_HERSHEY_DUPLEX, 0.75, p1_cfg['text_color'], 2, cv2.LINE_AA)
        cv2.putText(canvas, f"SCORE: {p1_stats['score']}", (36, 80), cv2.FONT_HERSHEY_DUPLEX, 0.95, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.putText(canvas, f"Munches: {p1_stats.get('munches', 0)}  Bombs: {p1_stats['bombs']}", (36, 104),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (180, 200, 210), 1, cv2.LINE_AA)

        # Player 1 Combo Tag
        if p1_stats.get('combo_mult', 1) > 1:
            draw_glass_panel(canvas, 16, 126, 175, 162, bg_color=(20, 40, 60), alpha=0.85,
                             border_color=p1_cfg['glow_color'], border_thickness=2)
            cv2.putText(canvas, f"MUNCH x{p1_stats['combo_mult']}!", (26, 152),
                        cv2.FONT_HERSHEY_DUPLEX, 0.65, p1_cfg['glow_color'], 2, cv2.LINE_AA)

        # 3. Player 2 HUD (Top-Right)
        p2_cfg = config.PLAYER_2
        draw_glass_panel(canvas, config.WINDOW_WIDTH - 290, 16, config.WINDOW_WIDTH - 16, 118,
                         bg_color=(30, 20, 24), alpha=0.8,
                         border_color=p2_cfg['color'], border_thickness=2)
        cv2.circle(canvas, (config.WINDOW_WIDTH - 270, 42), 8, p2_cfg['color'], -1, cv2.LINE_AA)
        cv2.putText(canvas, p2_cfg['name'], (config.WINDOW_WIDTH - 252, 48),
                    cv2.FONT_HERSHEY_DUPLEX, 0.75, p2_cfg['text_color'], 2, cv2.LINE_AA)
        cv2.putText(canvas, f"SCORE: {p2_stats['score']}", (config.WINDOW_WIDTH - 270, 80),
                    cv2.FONT_HERSHEY_DUPLEX, 0.95, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.putText(canvas, f"Munches: {p2_stats.get('munches', 0)}  Bombs: {p2_stats['bombs']}",
                    (config.WINDOW_WIDTH - 270, 104),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (210, 190, 190), 1, cv2.LINE_AA)

        # Player 2 Combo Tag
        if p2_stats.get('combo_mult', 1) > 1:
            draw_glass_panel(canvas, config.WINDOW_WIDTH - 175, 126, config.WINDOW_WIDTH - 16, 162,
                             bg_color=(60, 25, 20), alpha=0.85,
                             border_color=p2_cfg['glow_color'], border_thickness=2)
            cv2.putText(canvas, f"MUNCH x{p2_stats['combo_mult']}!", (config.WINDOW_WIDTH - 165, 152),
                        cv2.FONT_HERSHEY_DUPLEX, 0.65, p2_cfg['glow_color'], 2, cv2.LINE_AA)

        # 4. Center Countdown Timer
        box_w, box_h = 200, 72
        bx1 = (config.WINDOW_WIDTH - box_w) // 2
        bx2 = bx1 + box_w
        by1 = 16
        by2 = by1 + box_h

        # Urgency color
        if is_endless:
            timer_text = "ENDLESS"
            ring_color = (0, 220, 255)
        else:
            secs = max(0, int(math.ceil(time_left)))
            timer_text = f"{secs // 60:02d}:{secs % 60:02d}"
            if secs <= 10:
                ring_color = (0, 0, 255) if int(time.time() * 4) % 2 == 0 else (0, 140, 255)
            elif secs <= 25:
                ring_color = (0, 180, 255)
            else:
                ring_color = (100, 255, 120)

        draw_glass_panel(canvas, bx1, by1, bx2, by2, bg_color=(18, 18, 22), alpha=0.85,
                         border_color=ring_color, border_thickness=2)
        cv2.putText(canvas, "ROUND TIME", (bx1 + 45, by1 + 22),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (180, 180, 180), 1, cv2.LINE_AA)
        cv2.putText(canvas, timer_text, (bx1 + 35, by1 + 58),
                    cv2.FONT_HERSHEY_DUPLEX, 1.05, ring_color, 2, cv2.LINE_AA)

        # Progress bar under timer
        if not is_endless and max_time > 0:
            frac = max(0.0, min(1.0, time_left / max_time))
            bar_y = by2 + 4
            cv2.line(canvas, (bx1, bar_y), (bx2, bar_y), (40, 40, 45), 4, cv2.LINE_AA)
            cv2.line(canvas, (bx1, bar_y), (bx1 + int(box_w * frac), bar_y), ring_color, 4, cv2.LINE_AA)

        # Leader Banner
        s1, s2 = p1_stats['score'], p2_stats['score']
        if s1 > s2:
            leader_str = "P1 LEADING"
            l_color = p1_cfg['color']
        elif s2 > s1:
            leader_str = "P2 LEADING"
            l_color = p2_cfg['color']
        else:
            leader_str = "TIED MATCH"
            l_color = (200, 200, 200)
        cv2.putText(canvas, leader_str, (mid_x - 48, by2 + 24),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.44, l_color, 1, cv2.LINE_AA)

        # 5. In-Game Navigation Buttons: RESTART, PAUSE, MENU, QUIT
        self.hud_restart_btn.draw(canvas, base_color=(40, 110, 60), active_color=(50, 255, 120))
        self.pause_btn.draw(canvas, base_color=(30, 120, 200), active_color=(0, 215, 255))
        self.hud_menu_btn.draw(canvas, base_color=(120, 90, 30), active_color=(255, 200, 50))
        self.quit_btn.draw(canvas, base_color=(40, 40, 180), active_color=(0, 50, 255))

    def draw_menu(self, canvas, selected_timer_sec):
        """Draw interactive Start / Setup Screen."""
        # Dim backdrop
        draw_glass_panel(canvas, 0, 0, config.WINDOW_WIDTH, config.WINDOW_HEIGHT,
                         bg_color=(12, 14, 18), alpha=0.7)

        # Title
        title = "FRUIT NINJA"
        (tw, th), _ = cv2.getTextSize(title, cv2.FONT_HERSHEY_DUPLEX, 2.3, 4)
        tx = (config.WINDOW_WIDTH - tw) // 2
        cv2.putText(canvas, title, (tx + 3, 113), cv2.FONT_HERSHEY_DUPLEX, 2.3, (0, 0, 0), 6, cv2.LINE_AA)
        cv2.putText(canvas, title, (tx, 110), cv2.FONT_HERSHEY_DUPLEX, 2.3, (0, 215, 255), 4, cv2.LINE_AA)

        subtitle = "2 - P L A Y E R   M O U T H   M U N C H   &   B O M B   S L A S H"
        (sw, sh), _ = cv2.getTextSize(subtitle, cv2.FONT_HERSHEY_DUPLEX, 0.65, 1)
        sx = (config.WINDOW_WIDTH - sw) // 2
        cv2.putText(canvas, subtitle, (sx, 150), cv2.FONT_HERSHEY_DUPLEX, 0.65, (220, 240, 255), 1, cv2.LINE_AA)

        # Player Zone indicators
        p1_cfg = config.PLAYER_1
        p2_cfg = config.PLAYER_2
        draw_glass_panel(canvas, 60, 195, 380, 320, bg_color=(20, 35, 45), alpha=0.8,
                         border_color=p1_cfg['color'], border_thickness=2)
        cv2.putText(canvas, p1_cfg['name'], (80, 230), cv2.FONT_HERSHEY_DUPLEX, 0.85, p1_cfg['color'], 2, cv2.LINE_AA)
        cv2.putText(canvas, "LEFT HALF (Head Tag: P1)", (80, 258), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (200, 240, 255), 1, cv2.LINE_AA)
        cv2.putText(canvas, "MUNCH FRUITS: Open mouth to eat!", (80, 282), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (100, 255, 150), 1, cv2.LINE_AA)
        cv2.putText(canvas, "SLASH BOMBS: Slice with hand blade!", (80, 306), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (255, 200, 100), 1, cv2.LINE_AA)

        draw_glass_panel(canvas, config.WINDOW_WIDTH - 380, 195, config.WINDOW_WIDTH - 60, 320,
                         bg_color=(45, 25, 20), alpha=0.8,
                         border_color=p2_cfg['color'], border_thickness=2)
        cv2.putText(canvas, p2_cfg['name'], (config.WINDOW_WIDTH - 360, 230),
                    cv2.FONT_HERSHEY_DUPLEX, 0.85, p2_cfg['color'], 2, cv2.LINE_AA)
        cv2.putText(canvas, "RIGHT HALF (Head Tag: P2)", (config.WINDOW_WIDTH - 360, 258),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.52, (255, 220, 200), 1, cv2.LINE_AA)
        cv2.putText(canvas, "MUNCH FRUITS: Open mouth to eat!", (config.WINDOW_WIDTH - 360, 282),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.48, (100, 255, 150), 1, cv2.LINE_AA)
        cv2.putText(canvas, "SLASH BOMBS: Slice with hand blade!", (config.WINDOW_WIDTH - 360, 306),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.48, (255, 200, 100), 1, cv2.LINE_AA)

        # Section: Choose Round Timer
        sec_str = "SELECT ROUND TIMER (Press Keys [1] to [5] or Click)"
        (cw, ch), _ = cv2.getTextSize(sec_str, cv2.FONT_HERSHEY_SIMPLEX, 0.65, 1)
        cx = (config.WINDOW_WIDTH - cw) // 2
        cv2.putText(canvas, sec_str, (cx, 435), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (230, 230, 230), 1, cv2.LINE_AA)

        # Render Timer buttons
        for btn in self.timer_buttons:
            btn.is_selected = (btn.tag == selected_timer_sec)
            btn.draw(canvas)

        # Start prompt under watermelon
        start_txt = "MUNCH THE WATERMELON OR PRESS [SPACE] TO START!"
        (stw, _), _ = cv2.getTextSize(start_txt, cv2.FONT_HERSHEY_DUPLEX, 0.82, 2)
        cv2.putText(canvas, start_txt, ((config.WINDOW_WIDTH - stw) // 2, 350),
                    cv2.FONT_HERSHEY_DUPLEX, 0.82, (255, 255, 255), 2, cv2.LINE_AA)

        # Main Menu Options: START, RESTART, QUIT
        self.menu_start_btn.draw(canvas, base_color=(40, 160, 70), active_color=(50, 255, 100))
        self.menu_restart_btn.draw(canvas, base_color=(30, 110, 180), active_color=(0, 215, 255))
        self.menu_quit_btn.draw(canvas, base_color=(40, 40, 180), active_color=(0, 50, 255))

        # Keyboard helper info at bottom
        info_txt = "KEYBOARD CONTROLS: [Space] Start  |  [R] Restart  |  [1-5] Timer  |  [Q] Quit"
        (iw, _), _ = cv2.getTextSize(info_txt, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1)
        cv2.putText(canvas, info_txt, ((config.WINDOW_WIDTH - iw) // 2, config.WINDOW_HEIGHT - 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 215, 255), 1, cv2.LINE_AA)

    def draw_paused(self, canvas):
        """Draw interactive Pause menu with Resume, Restart, Menu, and Quit buttons controllable by keyboard or mouse."""
        draw_glass_panel(canvas, 0, 0, config.WINDOW_WIDTH, config.WINDOW_HEIGHT,
                         bg_color=(10, 12, 16), alpha=0.75)
        (tw, _), _ = cv2.getTextSize("GAME PAUSED", cv2.FONT_HERSHEY_DUPLEX, 2.0, 4)
        cx = (config.WINDOW_WIDTH - tw) // 2
        cv2.putText(canvas, "GAME PAUSED", (cx, 320), cv2.FONT_HERSHEY_DUPLEX, 2.0, (0, 220, 255), 4, cv2.LINE_AA)
        sub = "KEYBOARD: [Space/P] Resume  |  [R] Restart  |  [M] Main Menu  |  [Q] Quit"
        (sw, _), _ = cv2.getTextSize(sub, cv2.FONT_HERSHEY_SIMPLEX, 0.65, 1)
        cv2.putText(canvas, sub, ((config.WINDOW_WIDTH - sw) // 2, 370), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 215, 255), 1, cv2.LINE_AA)

        self.resume_btn.draw(canvas, base_color=(40, 160, 70), active_color=(50, 255, 100))
        self.pause_restart_btn.draw(canvas, base_color=(30, 110, 180), active_color=(0, 215, 255))
        self.pause_menu_btn.draw(canvas, base_color=(120, 90, 30), active_color=(255, 200, 50))
        self.pause_quit_btn.draw(canvas, base_color=(40, 40, 180), active_color=(0, 50, 255))

    def draw_countdown(self, canvas, count_val):
        """Draw dramatic 3, 2, 1, SLICE! pre-round countdown."""
        txt = str(count_val) if count_val > 0 else "SLICE!"
        color = (0, 215, 255) if count_val > 0 else (50, 255, 100)
        scale = 3.2 if count_val > 0 else 2.6
        (tw, th), _ = cv2.getTextSize(txt, cv2.FONT_HERSHEY_DUPLEX, scale, 5)
        tx = (config.WINDOW_WIDTH - tw) // 2
        ty = (config.WINDOW_HEIGHT + th) // 2 - 20

        # Backplate
        cv2.circle(canvas, (config.WINDOW_WIDTH // 2, config.WINDOW_HEIGHT // 2 - 20), 110, (15, 15, 20), -1, cv2.LINE_AA)
        cv2.circle(canvas, (config.WINDOW_WIDTH // 2, config.WINDOW_HEIGHT // 2 - 20), 110, color, 4, cv2.LINE_AA)

        cv2.putText(canvas, txt, (tx, ty), cv2.FONT_HERSHEY_DUPLEX, scale, (255, 255, 255), 6, cv2.LINE_AA)
        cv2.putText(canvas, txt, (tx, ty), cv2.FONT_HERSHEY_DUPLEX, scale, color, 3, cv2.LINE_AA)

    def draw_game_over(self, canvas, p1_stats, p2_stats):
        """Draw victory podium, full stats comparison, and rematch options."""
        draw_glass_panel(canvas, 0, 0, config.WINDOW_WIDTH, config.WINDOW_HEIGHT,
                         bg_color=(10, 12, 16), alpha=0.82)

        s1, s2 = p1_stats['score'], p2_stats['score']
        if s1 > s2:
            win_txt = "PLAYER 1 WINS!"
            win_color = config.PLAYER_1['color']
            win_sub = "SUPREME FRUIT NINJA MASTER"
        elif s2 > s1:
            win_txt = "PLAYER 2 WINS!"
            win_color = config.PLAYER_2['color']
            win_sub = "SUPREME FRUIT NINJA MASTER"
        else:
            win_txt = "HONORABLE DRAW!"
            win_color = (0, 220, 255)
            win_sub = "BOTH BLADES EQUALLY SHARP"

        # Banner
        (tw, _), _ = cv2.getTextSize(win_txt, cv2.FONT_HERSHEY_DUPLEX, 1.9, 4)
        cv2.putText(canvas, win_txt, ((config.WINDOW_WIDTH - tw) // 2, 110),
                    cv2.FONT_HERSHEY_DUPLEX, 1.9, win_color, 4, cv2.LINE_AA)
        (sw, _), _ = cv2.getTextSize(win_sub, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 1)
        cv2.putText(canvas, win_sub, ((config.WINDOW_WIDTH - sw) // 2, 150),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (220, 230, 240), 1, cv2.LINE_AA)

        # Comparison Podiums
        panel_w = 380
        p1_x = config.WINDOW_WIDTH // 2 - panel_w - 30
        p2_x = config.WINDOW_WIDTH // 2 + 30
        py = 180

        # P1 Card
        draw_glass_panel(canvas, p1_x, py, p1_x + panel_w, py + 260,
                         bg_color=(18, 30, 40), alpha=0.85,
                         border_color=config.PLAYER_1['color'], border_thickness=3 if s1 >= s2 else 1)
        cv2.putText(canvas, config.PLAYER_1['name'], (p1_x + 30, py + 45),
                    cv2.FONT_HERSHEY_DUPLEX, 0.9, config.PLAYER_1['color'], 2, cv2.LINE_AA)
        cv2.putText(canvas, f"FINAL SCORE:  {s1}", (p1_x + 30, py + 95),
                    cv2.FONT_HERSHEY_DUPLEX, 0.95, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.putText(canvas, f"Fruits Munched:   {p1_stats.get('munches', 0)}", (p1_x + 30, py + 140),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, (100, 255, 160), 1, cv2.LINE_AA)
        cv2.putText(canvas, f"Bombs Slashed:    {p1_stats['bombs']}", (p1_x + 30, py + 180),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, (200, 180, 180), 1, cv2.LINE_AA)
        cv2.putText(canvas, f"Max Combo Streak: x{p1_stats.get('max_combo', 1)}", (p1_x + 30, py + 220),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, (160, 240, 255), 1, cv2.LINE_AA)

        # P2 Card
        draw_glass_panel(canvas, p2_x, py, p2_x + panel_w, py + 260,
                         bg_color=(40, 22, 18), alpha=0.85,
                         border_color=config.PLAYER_2['color'], border_thickness=3 if s2 >= s1 else 1)
        cv2.putText(canvas, config.PLAYER_2['name'], (p2_x + 30, py + 45),
                    cv2.FONT_HERSHEY_DUPLEX, 0.9, config.PLAYER_2['color'], 2, cv2.LINE_AA)
        cv2.putText(canvas, f"FINAL SCORE:  {s2}", (p2_x + 30, py + 95),
                    cv2.FONT_HERSHEY_DUPLEX, 0.95, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.putText(canvas, f"Fruits Munched:   {p2_stats.get('munches', 0)}", (p2_x + 30, py + 140),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, (100, 255, 160), 1, cv2.LINE_AA)
        cv2.putText(canvas, f"Bombs Slashed:    {p2_stats['bombs']}", (p2_x + 30, py + 180),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, (230, 170, 170), 1, cv2.LINE_AA)
        cv2.putText(canvas, f"Max Combo Streak: x{p2_stats.get('max_combo', 1)}", (p2_x + 30, py + 220),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 210, 170), 1, cv2.LINE_AA)

        # Rematch call to action
        rematch_txt = "MUNCH THE WATERMELON OR PRESS [R] TO REMATCH!"
        (rw, _), _ = cv2.getTextSize(rematch_txt, cv2.FONT_HERSHEY_DUPLEX, 0.82, 2)
        cv2.putText(canvas, rematch_txt, ((config.WINDOW_WIDTH - rw) // 2, 470),
                    cv2.FONT_HERSHEY_DUPLEX, 0.82, (255, 255, 255), 2, cv2.LINE_AA)

        # Game Over Control Buttons: REMATCH, < MENU, X QUIT
        self.gameover_rematch_btn.draw(canvas, base_color=(40, 160, 70), active_color=(50, 255, 100))
        self.gameover_menu_btn.draw(canvas, base_color=(120, 90, 30), active_color=(255, 200, 50))
        self.gameover_quit_btn.draw(canvas, base_color=(40, 40, 180), active_color=(0, 50, 255))

        sub_info = "KEYBOARD: [R] Rematch  |  [M] Main Menu  |  [Q] Quit"
        (siw, _), _ = cv2.getTextSize(sub_info, cv2.FONT_HERSHEY_SIMPLEX, 0.58, 1)
        cv2.putText(canvas, sub_info, ((config.WINDOW_WIDTH - siw) // 2, 675),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.58, (0, 215, 255), 1, cv2.LINE_AA)
