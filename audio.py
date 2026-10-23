"""
Procedural audio synthesizer for Fruit Ninja CV using Pygame mixer and NumPy.
Generates sound effects dynamically without requiring external sound files.
Supports spatial stereo panning (Player 1 left-leaning, Player 2 right-leaning).
"""
import os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
import pygame
import numpy as np
import time
import config

_INITIALIZED = False
_SOUNDS = {}
_LAST_PLAYED = {}

def init(sample_rate=44100):
    global _INITIALIZED
    if _INITIALIZED:
        return
    try:
        pygame.mixer.init(frequency=sample_rate, size=-16, channels=2, buffer=512)
        _generate_all_sounds(sample_rate)
        _INITIALIZED = True
    except Exception as e:
        print(f"[Audio] Warning: Could not initialize audio mixer: {e}")
        _INITIALIZED = False

def _make_sound(left_samples, right_samples):
    """Combine 1D float arrays (-1.0 to 1.0) into a 16-bit stereo pygame Sound."""
    l_int = np.clip(left_samples * 32767, -32767, 32767).astype(np.int16)
    r_int = np.clip(right_samples * 32767, -32767, 32767).astype(np.int16)
    stereo = np.column_stack((l_int, r_int))
    return pygame.sndarray.make_sound(stereo)

def _generate_all_sounds(sr):
    # 1. Blade Swoosh (Fast sweeping air resistance)
    dur = 0.14
    t = np.linspace(0, dur, int(sr * dur), endpoint=False)
    freq = np.linspace(800, 180, len(t))
    phase = 2 * np.pi * np.cumsum(freq) / sr
    noise = np.random.uniform(-0.15, 0.15, len(t))
    env = np.sin(np.pi * (t / dur)) ** 1.5
    swoosh_mono = (np.sin(phase) * 0.4 + noise) * env
    _SOUNDS['swoosh_p1'] = _make_sound(swoosh_mono * 0.5, swoosh_mono * 0.15)
    _SOUNDS['swoosh_p2'] = _make_sound(swoosh_mono * 0.15, swoosh_mono * 0.5)
    _SOUNDS['swoosh'] = _make_sound(swoosh_mono * 0.35, swoosh_mono * 0.35)

    # 2. Fruit Slice (Crisp impact squelch)
    dur = 0.12
    t = np.linspace(0, dur, int(sr * dur), endpoint=False)
    f1 = np.linspace(1200, 300, len(t))
    f2 = np.linspace(600, 150, len(t))
    phase1 = 2 * np.pi * np.cumsum(f1) / sr
    phase2 = 2 * np.pi * np.cumsum(f2) / sr
    env = np.exp(-t * 28)
    squelch = (np.sin(phase1) * 0.5 + np.sin(phase2) * 0.3 + np.random.uniform(-0.2, 0.2, len(t))) * env
    _SOUNDS['slice_p1'] = _make_sound(squelch * 0.7, squelch * 0.25)
    _SOUNDS['slice_p2'] = _make_sound(squelch * 0.25, squelch * 0.7)
    _SOUNDS['slice'] = _make_sound(squelch * 0.5, squelch * 0.5)

    # 3. Combo Chime (Ascending triad chord)
    dur = 0.35
    t = np.linspace(0, dur, int(sr * dur), endpoint=False)
    notes = [523.25, 659.25, 783.99, 1046.50]  # C5, E5, G5, C6
    combo_mono = np.zeros(len(t))
    for i, freq in enumerate(notes):
        offset = int(i * 0.06 * sr)
        if offset < len(t):
            sub_t = t[offset:]
            env = np.exp(-(sub_t - sub_t[0]) * 10)
            combo_mono[offset:] += np.sin(2 * np.pi * freq * (sub_t - sub_t[0])) * 0.25 * env
    _SOUNDS['combo_p1'] = _make_sound(combo_mono * 0.7, combo_mono * 0.3)
    _SOUNDS['combo_p2'] = _make_sound(combo_mono * 0.3, combo_mono * 0.7)
    _SOUNDS['combo'] = _make_sound(combo_mono * 0.5, combo_mono * 0.5)

    # 4. Bomb Explosion (Deep sub-bass impact with rumble)
    dur = 0.55
    t = np.linspace(0, dur, int(sr * dur), endpoint=False)
    freq = np.linspace(130, 35, len(t))
    phase = 2 * np.pi * np.cumsum(freq) / sr
    noise = np.random.uniform(-0.4, 0.4, len(t))
    env = np.exp(-t * 8)
    bomb_mono = (np.sin(phase) * 0.6 + noise * 0.4) * env
    _SOUNDS['bomb'] = _make_sound(bomb_mono * 0.8, bomb_mono * 0.8)

    # 5. Countdown Beep (High tick)
    dur = 0.08
    t = np.linspace(0, dur, int(sr * dur), endpoint=False)
    beep_mono = np.sin(2 * np.pi * 880 * t) * 0.4 * np.exp(-t * 25)
    _SOUNDS['beep'] = _make_sound(beep_mono, beep_mono)

    # 6. Countdown Start (GO tone)
    dur = 0.25
    t = np.linspace(0, dur, int(sr * dur), endpoint=False)
    go_mono = np.sin(2 * np.pi * 1320 * t) * 0.5 * np.exp(-t * 12)
    _SOUNDS['start'] = _make_sound(go_mono, go_mono)

    # 7. Game Over Fanfare
    dur = 0.8
    t = np.linspace(0, dur, int(sr * dur), endpoint=False)
    fanfare_notes = [523.25, 659.25, 783.99, 1046.50, 1318.51]
    fanfare_mono = np.zeros(len(t))
    for i, freq in enumerate(fanfare_notes):
        offset = int(i * 0.1 * sr)
        if offset < len(t):
            sub_t = t[offset:]
            env = np.exp(-(sub_t - sub_t[0]) * 5)
            fanfare_mono[offset:] += np.sin(2 * np.pi * freq * (sub_t - sub_t[0])) * 0.22 * env
    _SOUNDS['game_over'] = _make_sound(fanfare_mono * 0.6, fanfare_mono * 0.6)

    # 8. Munch / Chomp sound (Juicy bite with teeth snap)
    dur = 0.18
    t = np.linspace(0, dur, int(sr * dur), endpoint=False)
    f_crunch = np.linspace(950, 220, len(t))
    phase_crunch = 2 * np.pi * np.cumsum(f_crunch) / sr
    crunch_noise = np.random.uniform(-0.35, 0.35, len(t))
    bite_env = (np.sin(np.pi * (t / dur)) ** 0.8) * np.exp(-t * 18)
    munch_mono = (np.sin(phase_crunch) * 0.5 + crunch_noise * 0.5) * bite_env
    _SOUNDS['munch_p1'] = _make_sound(munch_mono * 0.8, munch_mono * 0.25)
    _SOUNDS['munch_p2'] = _make_sound(munch_mono * 0.25, munch_mono * 0.8)
    _SOUNDS['munch'] = _make_sound(munch_mono * 0.6, munch_mono * 0.6)

def play(name, player_id=None, cooldown=0.06):
    """Play a sound with optional player panning and debounce cooldown."""
    if not config.SOUND_ENABLED or not _INITIALIZED:
        return
    now = time.time()
    key = name
    if player_id in (1, 2):
        player_key = f"{name}_p{player_id}"
        if player_key in _SOUNDS:
            key = player_key

    # Debounce check
    if key in _LAST_PLAYED and (now - _LAST_PLAYED[key]) < cooldown:
        return

    snd = _SOUNDS.get(key) or _SOUNDS.get(name)
    if snd:
        snd.play()
        _LAST_PLAYED[key] = now
