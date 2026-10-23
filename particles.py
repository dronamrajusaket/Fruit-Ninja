"""
Particle effects system for Fruit Ninja CV.
Handles juice splashes, slice sparks, shockwaves, and floating score/combo texts.
"""
import random
import math
import cv2
import numpy as np

class JuiceParticle:
    def __init__(self, x, y, color, speed_mult=1.0):
        self.x = float(x)
        self.y = float(y)
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(3.0, 10.0) * speed_mult
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed - random.uniform(1.0, 4.0)
        self.color = color
        self.radius = random.randint(3, 7)
        self.life = 1.0  # 1.0 down to 0.0
        self.decay = random.uniform(0.025, 0.055)
        self.gravity = 0.35

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += self.gravity
        self.life -= self.decay
        return self.life > 0

    def draw(self, canvas):
        if self.life <= 0:
            return
        r = max(1, int(self.radius * self.life))
        pt = (int(self.x), int(self.y))
        cv2.circle(canvas, pt, r, self.color, -1, cv2.LINE_AA)

class FloatingText:
    def __init__(self, x, y, text, color, scale=1.0, duration=1.0):
        self.x = float(x)
        self.y = float(y)
        self.text = text
        self.color = color
        self.scale = scale
        self.life = 1.0
        self.decay = 1.0 / (duration * 30.0)
        self.vy = -1.8

    def update(self):
        self.y += self.vy
        self.life -= self.decay
        return self.life > 0

    def draw(self, canvas):
        if self.life <= 0:
            return
        pt = (int(self.x), int(self.y))
        # Draw shadow
        cv2.putText(canvas, self.text, (pt[0] + 2, pt[1] + 2),
                    cv2.FONT_HERSHEY_DUPLEX, self.scale, (0, 0, 0), 3, cv2.LINE_AA)
        # Draw colored text
        cv2.putText(canvas, self.text, pt,
                    cv2.FONT_HERSHEY_DUPLEX, self.scale, self.color, 2, cv2.LINE_AA)

class Shockwave:
    def __init__(self, x, y, max_radius=80, color=(0, 220, 255)):
        self.x = int(x)
        self.y = int(y)
        self.radius = 8
        self.max_radius = max_radius
        self.color = color
        self.life = 1.0
        self.decay = 0.07

    def update(self):
        self.radius += 5
        self.life -= self.decay
        return self.life > 0 and self.radius < self.max_radius

    def draw(self, canvas):
        if self.life <= 0:
            return
        thickness = max(1, int(4 * self.life))
        cv2.circle(canvas, (self.x, self.y), int(self.radius), self.color, thickness, cv2.LINE_AA)

class ParticleManager:
    def __init__(self):
        self.particles = []
        self.texts = []
        self.shockwaves = []

    def add_slice_burst(self, x, y, juice_color, is_bomb=False, is_munch=False):
        count = 35 if is_bomb else (28 if is_munch else 22)
        speed_mult = 1.6 if is_bomb else (1.2 if is_munch else 1.0)
        for _ in range(count):
            p_color = (random.randint(20, 60), random.randint(120, 220), 255) if is_bomb else juice_color
            self.particles.append(JuiceParticle(x, y, p_color, speed_mult))
        
        sw_color = (0, 100, 255) if is_bomb else ((50, 255, 120) if is_munch else juice_color)
        self.shockwaves.append(Shockwave(x, y, max_radius=110 if is_bomb else 75, color=sw_color))

    def add_floating_text(self, x, y, text, color, scale=0.9):
        self.texts.append(FloatingText(x, y, text, color, scale))

    def update(self):
        self.particles = [p for p in self.particles if p.update()]
        self.texts = [t for t in self.texts if t.update()]
        self.shockwaves = [sw for sw in self.shockwaves if sw.update()]

    def draw(self, canvas):
        for sw in self.shockwaves:
            sw.draw(canvas)
        for p in self.particles:
            p.draw(canvas)
        for t in self.texts:
            t.draw(canvas)

    def clear(self):
        self.particles.clear()
        self.texts.clear()
        self.shockwaves.clear()
