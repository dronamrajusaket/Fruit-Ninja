"""
Configuration settings for Fruit Ninja 2-Player Edition.
"""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, 'hand_landmarker.task')
FACE_MODEL_PATH = os.path.join(BASE_DIR, 'face_landmarker.task')

# Window and Display
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720
FPS = 30
WINDOW_TITLE = 'Fruit Ninja - 2 Player Mouth Munch & Bomb Slash'

# Slicing & Hand Tracking
BLADE_TRAIL_LEN = 28  # Extended longer neon glowing trail
MIN_SLICE_SPEED = 14.0  # px/frame threshold for registering an intentional slice
HAND_DETECTION_CONFIDENCE = 0.5
HAND_TRACKING_CONFIDENCE = 0.5
MAX_NUM_HANDS = 4

# Face & Mouth Munch Tracking
MOUTH_OPEN_RATIO_THRESH = 0.22   # Threshold for mouth considered open / munching
MUNCH_COLLISION_RADIUS = 65     # Proximity radius around mouth center to munch a fruit
MAX_NUM_FACES = 2

# Player Configurations (BGR format for OpenCV)
PLAYER_1 = {
    'id': 1,
    'name': 'PLAYER 1',
    'color': (255, 220, 0),        # Vibrant Cyan / Blue in BGR
    'glow_color': (255, 255, 120),
    'text_color': (255, 240, 100),
    'zone': 'left'
}

PLAYER_2 = {
    'id': 2,
    'name': 'PLAYER 2',
    'color': (30, 80, 255),        # Vibrant Coral / Orange-Red in BGR
    'glow_color': (100, 150, 255),
    'text_color': (140, 180, 255),
    'zone': 'right'
}

# Timer Presets (in seconds; 0 represents Endless)
TIMER_PRESETS = [30, 60, 90, 120, 0]
DEFAULT_TIMER_INDEX = 1  # 60s

# Fruit Definitions
FRUIT_TYPES = {
    'watermelon': {
        'name': 'Watermelon',
        'points': 10,
        'radius': 44,
        'outer_color': (34, 139, 34),     # Forest Green
        'inner_color': (60, 60, 220),     # Juicy Red
        'juice_color': (50, 50, 240),
        'weight': 25,
        'is_bomb': False
    },
    'banana': {
        'name': 'Banana',
        'points': 15,
        'radius': 36,
        'outer_color': (0, 215, 255),     # Bright Gold/Yellow
        'inner_color': (150, 240, 255),   # Creamy yellow
        'juice_color': (80, 220, 255),
        'weight': 20,
        'is_bomb': False
    },
    'apple': {
        'name': 'Apple',
        'points': 10,
        'radius': 38,
        'outer_color': (25, 30, 200),     # Ruby Red
        'inner_color': (220, 250, 250),   # Off white flesh
        'juice_color': (40, 50, 220),
        'weight': 22,
        'is_bomb': False
    },
    'orange': {
        'name': 'Orange',
        'points': 15,
        'radius': 38,
        'outer_color': (0, 140, 255),     # Tangy Orange
        'inner_color': (50, 170, 255),
        'juice_color': (20, 150, 255),
        'weight': 18,
        'is_bomb': False
    },
    'strawberry': {
        'name': 'Strawberry',
        'points': 20,
        'radius': 30,
        'outer_color': (45, 45, 230),     # Bright Red
        'inner_color': (100, 120, 245),
        'juice_color': (60, 60, 240),
        'weight': 12,
        'is_bomb': False
    },
    'starfruit': {
        'name': 'Starfruit',
        'points': 50,
        'radius': 36,
        'outer_color': (0, 225, 255),     # Golden yellow
        'inner_color': (100, 245, 255),
        'juice_color': (50, 240, 255),
        'weight': 5,                      # Rare bonus
        'is_bomb': False
    },
    'bomb': {
        'name': 'Bomb',
        'points': 25,                     # Slashing a bomb awards +25 points!
        'eat_penalty': -30,               # Eating a bomb with mouth penalizes -30 points!
        'radius': 40,
        'outer_color': (35, 35, 35),      # Charcoal
        'inner_color': (10, 10, 180),     # Dark red warning core
        'juice_color': (0, 140, 255),     # Spark embers
        'weight': 15,
        'is_bomb': True
    }
}

# Physics
GRAVITY = 0.45
SPAWN_MIN_INTERVAL = 1.0   # seconds
SPAWN_MAX_INTERVAL = 2.2
COMBO_TIME_WINDOW = 0.5    # seconds between slices to chain combos

# Audio Settings
SOUND_ENABLED = False
AUDIO_SAMPLE_RATE = 44100
