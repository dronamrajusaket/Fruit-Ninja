"""
Fruit and Bomb physics, procedural rendering, and slicing mechanics for Fruit Ninja CV.
"""
import random
import math
import cv2
import numpy as np
import config

class FruitHalf:
    """Represents one of two severed fruit halves flying apart after a slice."""
    def __init__(self, x, y, vx, vy, fruit_type, angle, rot_speed, side=1):
        self.x = float(x)
        self.y = float(y)
        self.vx = float(vx)
        self.vy = float(vy)
        self.type = fruit_type
        self.angle = float(angle)
        self.rot_speed = float(rot_speed)
        self.side = side  # +1 or -1
        self.radius = config.FRUIT_TYPES[fruit_type]['radius']
        self.outer_color = config.FRUIT_TYPES[fruit_type]['outer_color']
        self.inner_color = config.FRUIT_TYPES[fruit_type]['inner_color']
        self.is_bomb = config.FRUIT_TYPES[fruit_type]['is_bomb']
        self.gravity = config.GRAVITY

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += self.gravity
        self.angle += self.rot_speed
        # Keep until off screen
        return self.y < config.WINDOW_HEIGHT + 100

    def draw(self, canvas):
        cx, cy = int(self.x), int(self.y)
        r = int(self.radius)
        if cx < -r or cx > config.WINDOW_WIDTH + r or cy < -r or cy > config.WINDOW_HEIGHT + r:
            return

        # Draw half-circle rotated at self.angle
        # Side determines whether we draw 0..180 or 180..360
        start_a = int(self.angle + (0 if self.side > 0 else 180)) % 360
        end_a = (start_a + 180) % 360

        # Outer rind
        cv2.ellipse(canvas, (cx, cy), (r, r), 0, start_a, start_a + 180, self.outer_color, -1, cv2.LINE_AA)
        # Inner flesh
        cv2.ellipse(canvas, (cx, cy), (int(r * 0.82), int(r * 0.82)), 0, start_a, start_a + 180, self.inner_color, -1, cv2.LINE_AA)

        # Cut face line
        rad1 = math.radians(start_a)
        rad2 = math.radians(start_a + 180)
        p1 = (int(cx + r * math.cos(rad1)), int(cy + r * math.sin(rad1)))
        p2 = (int(cx + r * math.cos(rad2)), int(cy + r * math.sin(rad2)))
        cv2.line(canvas, p1, p2, (255, 255, 255), 2, cv2.LINE_AA)

class Fruit:
    """Active whole fruit or bomb soaring across the screen."""
    def __init__(self, x=None, fruit_type=None):
        if fruit_type is None:
            # Weighted random selection
            types = list(config.FRUIT_TYPES.keys())
            weights = [config.FRUIT_TYPES[t]['weight'] for t in types]
            self.type = random.choices(types, weights=weights)[0]
        else:
            self.type = fruit_type

        cfg = config.FRUIT_TYPES[self.type]
        self.name = cfg['name']
        self.points = cfg['points']
        self.radius = cfg['radius']
        self.outer_color = cfg['outer_color']
        self.inner_color = cfg['inner_color']
        self.juice_color = cfg['juice_color']
        self.is_bomb = cfg['is_bomb']

        # Spawn positioning: launch downwards from above the screen
        if x is None:
            self.x = float(random.randint(180, config.WINDOW_WIDTH - 180))
        else:
            self.x = float(x)
        self.y = float(-self.radius - 15)

        # Velocity: gentle horizontal drift, downward initial velocity
        center_x = config.WINDOW_WIDTH / 2.0
        offset_dir = (center_x - self.x) / (config.WINDOW_WIDTH / 2.0)
        self.vx = offset_dir * random.uniform(0.5, 2.5) + random.uniform(-1.0, 1.0)
        self.vy = random.uniform(3.5, 6.5)

        self.angle = random.uniform(0, 360)
        self.rot_speed = random.uniform(-3.5, 3.5)
        self.sliced = False
        self.fuse_frame = 0

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += config.GRAVITY * 0.45  # Gentle accelerating gravity downwards
        self.angle += self.rot_speed
        self.fuse_frame += 1

        # Check if fruit fell off bottom of screen
        if self.y > config.WINDOW_HEIGHT + self.radius + 30:
            return False
        return True

    def check_slice(self, p1, p2):
        """
        Check if blade segment from p1(x1, y1) to p2(x2, y2) intersects this fruit.
        Uses point-to-line-segment distance formula.
        """
        if self.sliced:
            return False
        x1, y1 = p1
        x2, y2 = p2
        fx, fy = self.x, self.y

        dx = x2 - x1
        dy = y2 - y1
        len_sq = dx * dx + dy * dy
        if len_sq == 0:
            dist = math.hypot(fx - x1, fy - y1)
        else:
            t = max(0.0, min(1.0, ((fx - x1) * dx + (fy - y1) * dy) / len_sq))
            proj_x = x1 + t * dx
            proj_y = y1 + t * dy
            dist = math.hypot(fx - proj_x, fy - proj_y)

        return dist <= (self.radius + 10)

    def check_munch(self, mouth_x, mouth_y, munch_radius=None):
        """
        Check if open mouth overlaps this fruit to munch/chomp it.
        """
        if self.sliced:
            return False
        if munch_radius is None:
            munch_radius = config.MUNCH_COLLISION_RADIUS
        dist = math.hypot(self.x - mouth_x, self.y - mouth_y)
        return dist <= (self.radius + munch_radius)

    def slice(self, slice_angle=None):
        """Sever the fruit into two halves flying away."""
        self.sliced = True
        if slice_angle is None:
            slice_angle = random.uniform(0, math.pi * 2)

        # Perpendicular normal impulse
        nx = math.cos(slice_angle + math.pi / 2)
        ny = math.sin(slice_angle + math.pi / 2)
        impulse = random.uniform(4.0, 7.0)

        h1 = FruitHalf(
            self.x, self.y,
            self.vx + nx * impulse, min(self.vy, 2.0) + ny * impulse - 2.0,
            self.type, math.degrees(slice_angle), self.rot_speed - 6.0, side=1
        )
        h2 = FruitHalf(
            self.x, self.y,
            self.vx - nx * impulse, min(self.vy, 2.0) - ny * impulse - 2.0,
            self.type, math.degrees(slice_angle), self.rot_speed + 6.0, side=-1
        )
        return [h1, h2]

    def draw(self, canvas):
        if self.sliced:
            return
        cx, cy = int(self.x), int(self.y)
        r = int(self.radius)
        if cx < -r or cx > config.WINDOW_WIDTH + r or cy < -r or cy > config.WINDOW_HEIGHT + r:
            return

        if self.is_bomb:
            self._draw_bomb(canvas, cx, cy, r)
        elif self.type == 'watermelon':
            self._draw_watermelon(canvas, cx, cy, r)
        elif self.type == 'banana':
            self._draw_banana(canvas, cx, cy, r)
        elif self.type == 'apple':
            self._draw_apple(canvas, cx, cy, r)
        elif self.type == 'orange':
            self._draw_orange(canvas, cx, cy, r)
        elif self.type == 'strawberry':
            self._draw_strawberry(canvas, cx, cy, r)
        elif self.type == 'starfruit':
            self._draw_starfruit(canvas, cx, cy, r)
        else:
            # Fallback circle
            cv2.circle(canvas, (cx, cy), r, self.outer_color, -1, cv2.LINE_AA)
            cv2.circle(canvas, (cx, cy), int(r * 0.8), self.inner_color, -1, cv2.LINE_AA)

    def _draw_watermelon(self, canvas, cx, cy, r):
        # Green rind
        cv2.circle(canvas, (cx, cy), r, self.outer_color, -1, cv2.LINE_AA)
        # Dark green stripes
        rad = math.radians(self.angle)
        for i in range(4):
            a = rad + i * (math.pi / 2)
            p1 = (int(cx + r * math.cos(a)), int(cy + r * math.sin(a)))
            p2 = (int(cx - r * math.cos(a)), int(cy - r * math.sin(a)))
            cv2.line(canvas, p1, p2, (15, 80, 15), 4, cv2.LINE_AA)
        # White inner line
        cv2.circle(canvas, (cx, cy), int(r * 0.88), (220, 245, 220), -1, cv2.LINE_AA)
        # Red pulp
        cv2.circle(canvas, (cx, cy), int(r * 0.80), self.inner_color, -1, cv2.LINE_AA)
        # Black seeds
        for i in range(5):
            sa = rad + i * (2 * math.pi / 5)
            sx = int(cx + (r * 0.5) * math.cos(sa))
            sy = int(cy + (r * 0.5) * math.sin(sa))
            cv2.circle(canvas, (sx, sy), 3, (10, 10, 10), -1, cv2.LINE_AA)

    def _draw_orange(self, canvas, cx, cy, r):
        # Orange rind
        cv2.circle(canvas, (cx, cy), r, self.outer_color, -1, cv2.LINE_AA)
        # Pale pith
        cv2.circle(canvas, (cx, cy), int(r * 0.90), (180, 225, 255), -1, cv2.LINE_AA)
        # Pulp center
        cv2.circle(canvas, (cx, cy), int(r * 0.84), self.inner_color, -1, cv2.LINE_AA)
        # Citrus segments
        rad = math.radians(self.angle)
        for i in range(8):
            a = rad + i * (2 * math.pi / 8)
            px = int(cx + (r * 0.8) * math.cos(a))
            py = int(cy + (r * 0.8) * math.sin(a))
            cv2.line(canvas, (cx, cy), (px, py), (200, 235, 255), 2, cv2.LINE_AA)
        cv2.circle(canvas, (cx, cy), int(r * 0.15), (200, 235, 255), -1, cv2.LINE_AA)

    def _draw_apple(self, canvas, cx, cy, r):
        # Red apple body
        cv2.circle(canvas, (cx, cy), r, self.outer_color, -1, cv2.LINE_AA)
        # Stem and leaf at top (relative to angle)
        rad = math.radians(self.angle - 90)
        stem_x = int(cx + (r * 0.9) * math.cos(rad))
        stem_y = int(cy + (r * 0.9) * math.sin(rad))
        stem_end = (int(stem_x + 14 * math.cos(rad)), int(stem_y + 14 * math.sin(rad)))
        cv2.line(canvas, (stem_x, stem_y), stem_end, (30, 60, 110), 3, cv2.LINE_AA)
        # Green leaf
        leaf_p = (int(stem_x + 10 * math.cos(rad + 0.6)), int(stem_y + 10 * math.sin(rad + 0.6)))
        cv2.circle(canvas, leaf_p, 5, (40, 180, 40), -1, cv2.LINE_AA)
        # Specular shine
        shine_p = (int(cx - r * 0.35), int(cy - r * 0.35))
        cv2.circle(canvas, shine_p, int(r * 0.22), (180, 180, 255), -1, cv2.LINE_AA)

    def _draw_banana(self, canvas, cx, cy, r):
        # Crescent banana
        rad = math.radians(self.angle)
        pts = []
        for a_deg in range(-60, 61, 15):
            a = rad + math.radians(a_deg)
            dist = r * (1.1 - 0.3 * (a_deg / 60) ** 2)
            pts.append([int(cx + dist * math.cos(a)), int(cy + dist * math.sin(a))])
        for a_deg in range(60, -61, -15):
            a = rad + math.radians(a_deg)
            dist = r * (0.6 - 0.2 * (a_deg / 60) ** 2)
            pts.append([int(cx + dist * math.cos(a)), int(cy + dist * math.sin(a))])
        poly = np.array(pts, dtype=np.int32)
        cv2.fillPoly(canvas, [poly], self.outer_color, cv2.LINE_AA)
        # Tips (green/brown)
        if pts:
            cv2.circle(canvas, tuple(pts[0]), 5, (30, 80, 50), -1, cv2.LINE_AA)
            cv2.circle(canvas, tuple(pts[len(pts)//2]), 5, (20, 50, 90), -1, cv2.LINE_AA)

    def _draw_strawberry(self, canvas, cx, cy, r):
        # Tapered heart/berry
        rad = math.radians(self.angle)
        cv2.circle(canvas, (cx, cy), r, self.outer_color, -1, cv2.LINE_AA)
        # Green cap
        for i in range(4):
            a = rad + math.pi + i * (math.pi / 3) - (math.pi / 3)
            lx = int(cx + r * math.cos(a))
            ly = int(cy + r * math.sin(a))
            cv2.circle(canvas, (lx, ly), 5, (30, 180, 40), -1, cv2.LINE_AA)
        # Seed specs
        for i in range(7):
            sa = rad + i * (2 * math.pi / 7)
            sx = int(cx + (r * 0.5) * math.cos(sa))
            sy = int(cy + (r * 0.5) * math.sin(sa))
            cv2.circle(canvas, (sx, sy), 2, (200, 240, 255), -1, cv2.LINE_AA)

    def _draw_starfruit(self, canvas, cx, cy, r):
        # 5-pointed golden star
        rad = math.radians(self.angle)
        pts = []
        for i in range(10):
            a = rad + i * (math.pi / 5)
            dist = r if (i % 2 == 0) else (r * 0.45)
            pts.append([int(cx + dist * math.cos(a)), int(cy + dist * math.sin(a))])
        poly = np.array(pts, dtype=np.int32)
        cv2.fillPoly(canvas, [poly], (0, 220, 255), cv2.LINE_AA)
        cv2.polylines(canvas, [poly], True, (0, 150, 255), 2, cv2.LINE_AA)
        # Bright core
        cv2.circle(canvas, (cx, cy), int(r * 0.25), (180, 255, 255), -1, cv2.LINE_AA)

    def _draw_bomb(self, canvas, cx, cy, r):
        # Black bomb body
        cv2.circle(canvas, (cx, cy), r, (35, 35, 35), -1, cv2.LINE_AA)
        cv2.circle(canvas, (cx, cy), r, (80, 80, 80), 2, cv2.LINE_AA)
        # Specular light highlight
        cv2.circle(canvas, (cx - int(r * 0.35), cy - int(r * 0.35)), int(r * 0.22), (120, 120, 120), -1, cv2.LINE_AA)
        # Fuse collar & rope
        fuse_top = (cx, cy - r - 12)
        cv2.line(canvas, (cx, cy - r), fuse_top, (80, 120, 160), 3, cv2.LINE_AA)
        # Animated burning spark
        spark_color = (0, 120, 255) if (self.fuse_frame % 2 == 0) else (0, 230, 255)
        cv2.circle(canvas, fuse_top, 6, spark_color, -1, cv2.LINE_AA)
        cv2.circle(canvas, fuse_top, 3, (255, 255, 255), -1, cv2.LINE_AA)
        # Skull or red danger emblem
        cv2.putText(canvas, "!", (cx - 7, cy + 10), cv2.FONT_HERSHEY_DUPLEX, 0.9, (0, 50, 255), 2, cv2.LINE_AA)
