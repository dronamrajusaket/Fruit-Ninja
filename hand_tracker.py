"""
Multi-Modal Motion Tracker for 2-Player Fruit Ninja CV.
Simultaneously tracks:
1. Mouth opening and face movement via MediaPipe FaceLandmarker for fruit munching.
2. Hand positions and slashing movements via MediaPipe HandLandmarker for bomb slicing.
3. Partitions players into Player 1 (Left side) and Player 2 (Right side).
4. Generates extended glowing neon blade trails.
"""
import time
import math
from collections import deque
import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import config

class MultiPlayerTracker:
    def __init__(self, hand_model_path=config.MODEL_PATH, face_model_path=config.FACE_MODEL_PATH):
        # 1. Initialize Hand Landmarker
        hand_base_options = python.BaseOptions(model_asset_path=hand_model_path)
        hand_options = vision.HandLandmarkerOptions(
            base_options=hand_base_options,
            num_hands=config.MAX_NUM_HANDS,
            running_mode=vision.RunningMode.IMAGE,
            min_hand_detection_confidence=config.HAND_DETECTION_CONFIDENCE,
            min_tracking_confidence=config.HAND_TRACKING_CONFIDENCE
        )
        self.hand_detector = vision.HandLandmarker.create_from_options(hand_options)

        # 2. Initialize Face Landmarker (tracks up to 2 players)
        face_base_options = python.BaseOptions(model_asset_path=face_model_path)
        face_options = vision.FaceLandmarkerOptions(
            base_options=face_base_options,
            num_faces=config.MAX_NUM_FACES,
            running_mode=vision.RunningMode.IMAGE
        )
        self.face_detector = vision.FaceLandmarker.create_from_options(face_options)

        # Player hand blade states:
        self.player_trails = {
            1: deque(maxlen=config.BLADE_TRAIL_LEN),
            2: deque(maxlen=config.BLADE_TRAIL_LEN)
        }
        self.player_prev_pos = {1: None, 2: None}
        self.player_curr_pos = {1: None, 2: None}
        self.player_speeds = {1: 0.0, 2: 0.0}

        # Player face & mouth states:
        self.player_faces = {
            1: {'detected': False, 'mouth_center': None, 'face_center': None, 'mouth_ratio': 0.0, 'is_munching': False, 'box': None},
            2: {'detected': False, 'mouth_center': None, 'face_center': None, 'mouth_ratio': 0.0, 'is_munching': False, 'box': None}
        }
        # Munch animation trigger timestamps for visual bite effect
        self.last_munch_time = {1: 0.0, 2: 0.0}

    def process_frame(self, frame_bgr):
        """
        Process BGR frame from webcam.
        Returns combined dictionary:
        {
            1: {
                'pos': (x,y), 'prev_pos': (px,py), 'speed': float, 'is_slicing': bool, 'trail': [...],
                'face': {'detected': bool, 'mouth_center': (x,y), 'face_center': (x,y),
                         'mouth_ratio': float, 'is_munching': bool, 'box': (x, y, w, h)}
            },
            2: { ... }
        }
        """
        h, w, _ = frame_bgr.shape
        if w > 640:
            small_bgr = cv2.resize(frame_bgr, (640, int(h * 640 / w)), interpolation=cv2.INTER_LINEAR)
            rgb_frame = cv2.cvtColor(small_bgr, cv2.COLOR_BGR2RGB)
        else:
            rgb_frame = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

        # Detect hands and faces
        hand_results = self.hand_detector.detect(mp_image)
        face_results = self.face_detector.detect(mp_image)

        # -----------------------------
        # 1. Process Hands
        # -----------------------------
        p1_hand_candidates = []
        p2_hand_candidates = []

        if hand_results.hand_landmarks:
            for hand_landmarks in hand_results.hand_landmarks:
                wrist_x = hand_landmarks[0].x * w
                wrist_y = hand_landmarks[0].y * h
                tip_x = int(hand_landmarks[8].x * w)
                tip_y = int(hand_landmarks[8].y * h)

                tip_x = max(0, min(w - 1, tip_x))
                tip_y = max(0, min(h - 1, tip_y))

                hand_x = (wrist_x + tip_x) / 2.0
                if hand_x < w / 2:
                    p1_hand_candidates.append((tip_x, tip_y))
                else:
                    p2_hand_candidates.append((tip_x, tip_y))

        for pid, candidates in [(1, p1_hand_candidates), (2, p2_hand_candidates)]:
            prev = self.player_curr_pos[pid]
            curr = None
            speed = 0.0

            if candidates:
                if prev is None:
                    curr = candidates[0]
                else:
                    curr = min(candidates, key=lambda pt: math.hypot(pt[0] - prev[0], pt[1] - prev[1]))

                if prev is not None:
                    dist = math.hypot(curr[0] - prev[0], curr[1] - prev[1])
                    speed = dist
                    self.player_speeds[pid] = self.player_speeds[pid] * 0.25 + speed * 0.75
                else:
                    self.player_speeds[pid] = 0.0

                self.player_prev_pos[pid] = prev
                self.player_curr_pos[pid] = curr
                self.player_trails[pid].append((curr[0], curr[1], time.time()))
            else:
                self.player_speeds[pid] = 0.0
                self.player_prev_pos[pid] = None
                self.player_curr_pos[pid] = None
                if self.player_trails[pid]:
                    self.player_trails[pid].popleft()

        # -----------------------------
        # 2. Process Faces & Mouths
        # -----------------------------
        detected_faces = []
        if face_results.face_landmarks:
            for f_lm in face_results.face_landmarks:
                lip_upper = f_lm[13]
                lip_lower = f_lm[14]
                lip_left = f_lm[61]
                lip_right = f_lm[291]
                nose = f_lm[1]
                chin = f_lm[152]
                forehead = f_lm[10]

                # Mouth opening vertical vs face height
                lip_dist = abs(lip_lower.y - lip_upper.y)
                face_height = max(0.04, abs(chin.y - forehead.y))
                mouth_ratio = lip_dist / face_height

                # Mouth center coordinates
                mouth_cx = int((lip_upper.x + lip_lower.x + lip_left.x + lip_right.x) / 4.0 * w)
                mouth_cy = int((lip_upper.y + lip_lower.y + lip_left.y + lip_right.y) / 4.0 * h)

                face_cx = int(nose.x * w)
                face_cy = int(nose.y * h)

                # Face bounding box estimation
                fx_min = int(min(lm.x for lm in f_lm) * w)
                fx_max = int(max(lm.x for lm in f_lm) * w)
                fy_min = int(min(lm.y for lm in f_lm) * h)
                fy_max = int(max(lm.y for lm in f_lm) * h)
                box = (fx_min, fy_min, max(20, fx_max - fx_min), max(20, fy_max - fy_min))

                is_munching = mouth_ratio >= config.MOUTH_OPEN_RATIO_THRESH

                detected_faces.append({
                    'detected': True,
                    'mouth_center': (mouth_cx, mouth_cy),
                    'face_center': (face_cx, face_cy),
                    'mouth_ratio': mouth_ratio,
                    'is_munching': is_munching,
                    'box': box
                })

        # Assign faces to Player 1 (Left: x < w/2) and Player 2 (Right: x >= w/2)
        # If real faces detected in webcam frame, update player_faces.
        # Otherwise, keep previous or mock state if set.
        if detected_faces:
            mid_x = w / 2.0
            p1_faces = [f for f in detected_faces if f['face_center'][0] < mid_x]
            p2_faces = [f for f in detected_faces if f['face_center'][0] >= mid_x]

            p1_face_final = p1_faces[0] if p1_faces else (
                detected_faces[0] if detected_faces and detected_faces[0]['face_center'][0] < mid_x else
                {'detected': False, 'mouth_center': None, 'face_center': None, 'mouth_ratio': 0.0, 'is_munching': False, 'box': None}
            )
            p2_face_final = p2_faces[0] if p2_faces else (
                detected_faces[-1] if len(detected_faces) > 1 and detected_faces[-1]['face_center'][0] >= mid_x else
                {'detected': False, 'mouth_center': None, 'face_center': None, 'mouth_ratio': 0.0, 'is_munching': False, 'box': None}
            )

            self.player_faces[1] = p1_face_final
            self.player_faces[2] = p2_face_final
        elif not hasattr(self, '_mocked_faces') or not self._mocked_faces:
            self.player_faces[1] = {'detected': False, 'mouth_center': None, 'face_center': None, 'mouth_ratio': 0.0, 'is_munching': False, 'box': None}
            self.player_faces[2] = {'detected': False, 'mouth_center': None, 'face_center': None, 'mouth_ratio': 0.0, 'is_munching': False, 'box': None}

        # -----------------------------
        # 3. Assemble Output Data
        # -----------------------------
        player_data = {}
        for pid in (1, 2):
            is_slicing = self.player_speeds[pid] >= config.MIN_SLICE_SPEED
            player_data[pid] = {
                'pos': self.player_curr_pos[pid],
                'prev_pos': self.player_prev_pos[pid],
                'speed': self.player_speeds[pid],
                'is_slicing': is_slicing,
                'trail': list(self.player_trails[pid]),
                'face': self.player_faces[pid]
            }

        return player_data

    def set_mouse_pos(self, x, y, player_id=1):
        """Simulate blade movement using mouse position for testing/fallback."""
        prev = self.player_curr_pos[player_id]
        curr = (int(x), int(y))
        speed = 0.0
        if prev is not None:
            speed = math.hypot(curr[0] - prev[0], curr[1] - prev[1])
            self.player_speeds[player_id] = self.player_speeds[player_id] * 0.25 + speed * 0.75
        else:
            self.player_speeds[player_id] = 0.0

        self.player_prev_pos[player_id] = prev
        self.player_curr_pos[player_id] = curr
        self.player_trails[player_id].append((curr[0], curr[1], time.time()))

    def set_mock_face(self, player_id, mouth_x, mouth_y, is_munching=True, mouth_ratio=0.35):
        """Mock face and mouth data for testing / simulation."""
        self._mocked_faces = True
        self.player_faces[player_id] = {
            'detected': True,
            'mouth_center': (int(mouth_x), int(mouth_y)),
            'face_center': (int(mouth_x), int(mouth_y) - 35),
            'mouth_ratio': mouth_ratio,
            'is_munching': is_munching,
            'box': (int(mouth_x) - 60, int(mouth_y) - 90, 120, 140)
        }

    def trigger_munch_effect(self, player_id):
        self.last_munch_time[player_id] = time.time()

    def draw_player_trackers(self, canvas, player_data):
        """
        Draws:
        1. On top of each player's face:
           - Floating Player Tag ("PLAYER 1", "PLAYER 2") with custom colored banner
           - Mouth Munch Target circle and teeth chomper animation when mouth opens
           - Real-time Status: "MUNCHING" (green/pulsing) or "OPEN MOUTH TO MUNCH" (yellow)
        2. Extended neon glowing blade trails for slicing bombs.
        """
        now = time.time()

        # 1. Draw Player Face Overlays & Tags
        for pid in (1, 2):
            cfg = config.PLAYER_1 if pid == 1 else config.PLAYER_2
            face = player_data[pid]['face']

            if face['detected'] and face['mouth_center'] and face['face_center']:
                mx, my = face['mouth_center']
                fx, fy = face['face_center']
                box = face['box']

                # Calculate player tag position on top of the player's head
                tag_y = max(45, (box[1] - 25) if box else (fy - 85))
                tag_x = fx

                # Draw Top-of-Player Tag Banner
                tag_text = cfg['name']
                (tw, th), _ = cv2.getTextSize(tag_text, cv2.FONT_HERSHEY_DUPLEX, 0.7, 2)
                bx1 = tag_x - tw // 2 - 14
                bx2 = tag_x + tw // 2 + 14
                by1 = tag_y - th - 10
                by2 = tag_y + 8

                # Banner background
                sub = canvas[max(0, by1):min(canvas.shape[0], by2), max(0, bx1):min(canvas.shape[1], bx2)]
                if sub.size > 0:
                    bg = np.full(sub.shape, (20, 24, 30), dtype=np.uint8)
                    cv2.addWeighted(sub, 0.25, bg, 0.75, 0, sub)
                    canvas[max(0, by1):min(canvas.shape[0], by2), max(0, bx1):min(canvas.shape[1], bx2)] = sub

                cv2.rectangle(canvas, (bx1, by1), (bx2, by2), cfg['color'], 2, cv2.LINE_AA)
                cv2.putText(canvas, tag_text, (tag_x - tw // 2, tag_y),
                            cv2.FONT_HERSHEY_DUPLEX, 0.7, cfg['color'], 2, cv2.LINE_AA)

                # Status label under player tag
                status_text = "MUNCHING!" if face['is_munching'] else "OPEN MOUTH TO MUNCH"
                status_col = (50, 255, 120) if face['is_munching'] else (0, 215, 255)
                (stw, sth), _ = cv2.getTextSize(status_text, cv2.FONT_HERSHEY_SIMPLEX, 0.42, 1)
                cv2.putText(canvas, status_text, (tag_x - stw // 2, by2 + 16),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.42, status_col, 1, cv2.LINE_AA)

                # Draw Mouth Munching Reticle
                munch_radius = config.MUNCH_COLLISION_RADIUS
                if face['is_munching']:
                    # Pulsing active chomp circle
                    pulse = int(math.sin(now * 15.0) * 4)
                    r = munch_radius + pulse
                    cv2.circle(canvas, (mx, my), r, (50, 255, 120), 3, cv2.LINE_AA)
                    cv2.circle(canvas, (mx, my), r - 8, cfg['glow_color'], 1, cv2.LINE_AA)
                    # Chomper Teeth Graphics
                    teeth_w = 16
                    cv2.line(canvas, (mx - teeth_w, my - 12), (mx + teeth_w, my - 12), (255, 255, 255), 4, cv2.LINE_AA)
                    cv2.line(canvas, (mx - teeth_w, my + 12), (mx + teeth_w, my + 12), (255, 255, 255), 4, cv2.LINE_AA)
                    for tx in (-10, 0, 10):
                        cv2.line(canvas, (mx + tx, my - 12), (mx + tx, my - 4), (255, 255, 255), 3, cv2.LINE_AA)
                        cv2.line(canvas, (mx + tx, my + 12), (mx + tx, my + 4), (255, 255, 255), 3, cv2.LINE_AA)
                else:
                    # Idle mouth indicator
                    cv2.circle(canvas, (mx, my), 18, (120, 120, 150), 2, cv2.LINE_AA)
                    cv2.ellipse(canvas, (mx, my), (14, 6), 0, 0, 360, cfg['glow_color'], 1, cv2.LINE_AA)

                # Recent munch bite flash effect
                since_munch = now - self.last_munch_time[pid]
                if since_munch < 0.25:
                    burst_r = int(munch_radius * (1.0 + since_munch * 2.0))
                    alpha_burst = max(0.0, 1.0 - since_munch / 0.25)
                    cv2.circle(canvas, (mx, my), burst_r, (0, 255, 255), int(4 * alpha_burst) + 1, cv2.LINE_AA)

        # 2. Draw Extended Neon Blade Trails for Bomb Slashing
        for pid in (1, 2):
            cfg = config.PLAYER_1 if pid == 1 else config.PLAYER_2
            trail = player_data[pid]['trail']
            if len(trail) < 2:
                if len(trail) == 1:
                    pt = (trail[0][0], trail[0][1])
                    cv2.circle(canvas, pt, 14, cfg['glow_color'], 2, cv2.LINE_AA)
                    cv2.circle(canvas, pt, 6, (255, 255, 255), -1, cv2.LINE_AA)
                continue

            n = len(trail)
            for i in range(n - 1):
                p_start = (int(trail[i][0]), int(trail[i][1]))
                p_end = (int(trail[i+1][0]), int(trail[i+1][1]))
                progress = (i + 1) / n  # 0.0 to 1.0

                # Extended outer wide neon glow
                glow_thickness = int(14 * progress) + 4
                cv2.line(canvas, p_start, p_end, cfg['glow_color'], glow_thickness, cv2.LINE_AA)

                # Vivid colored core
                mid_thickness = int(8 * progress) + 3
                cv2.line(canvas, p_start, p_end, cfg['color'], mid_thickness, cv2.LINE_AA)

                # Bright white blade center
                white_thickness = int(4 * progress) + 1
                cv2.line(canvas, p_start, p_end, (255, 255, 255), white_thickness, cv2.LINE_AA)

            # Blade tip spark
            tip_pt = (int(trail[-1][0]), int(trail[-1][1]))
            cv2.circle(canvas, tip_pt, 9, cfg['color'], -1, cv2.LINE_AA)
            cv2.circle(canvas, tip_pt, 4, (255, 255, 255), -1, cv2.LINE_AA)
