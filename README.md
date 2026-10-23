# 🍉 Fruit Ninja: 2-Player Mouth Munch & Bomb Slash (OpenCV)

An interactive, competitive 2-player multiplayer arcade game built with **Python**, **OpenCV**, and **MediaPipe Face & Hand Landmarkers**.

---

## 🎮 How to Play

### 1. Two-Player Setup & On-Head Tags
- Stand side-by-side in front of your webcam.
- **Top-of-Player Tags**: Mentioned directly on top of each player's head:
  - **PLAYER 1 (Left Side)**: Cyan header tag + mouth munch reticle.
  - **PLAYER 2 (Right Side)**: Orange header tag + mouth munch reticle.

### 2. Gameplay Mechanics
- ⬇️ **Falling Objects**: Fruits and bombs spawn and fall smoothly from above towards the players!
- 👄 **Eating Fruits (Adds Points & Combos)**: Move your face near falling fruits and **open your mouth** to chomp on them!
  - Rapid fruit munches chain **MUNCH COMBO x2** and **MUNCH COMBO x3** multipliers!
- 💣 **Slashing Bombs (Adds +25 Points)**: Swiftly swing your hand blade across falling bombs to slash and defuse them with long glowing neon trails, earning **+25 points**!
- ☠️ **Eating Bombs (Reduces Points)**: If a player opens their mouth and munches on a bomb, it detonates and penalizes **-30 points**!
- 🏆 **Scoreboard & Winner Declaration**: Real-time dual HUD scoreboard and final Game Over podium declaring the winner (or draw).
- ⚡ **Instant Responsive Buttons**:
  - Removed slow hand hovering delays. Buttons now trigger **instantly** on click or slice!
  - **In-Game Top Bar**: `[RESTART]`, `[|| PAUSE]`, `[< MENU]`, `[X QUIT]` properly spaced with zero overlap.
  - **Front Menu**: `[> START]`, `[RESTART]`, `[X QUIT]`.
  - **Pause Menu**: `[> RESUME]`, `[RESTART]`, `[< MENU]`, `[X QUIT]`.
  - **Game Over**: `[REMATCH]`, `[< MENU]`, `[X QUIT]`.
- 🔇 **Sound**: Silenced by default (`SOUND_ENABLED = False`).
- **Fruit Types**:
  - 🍉 **Watermelon**: 10 Pts
  - 🍌 **Banana**: 15 Pts
  - 🍎 **Apple**: 10 Pts
  - 🍊 **Orange**: 15 Pts
  - 🍓 **Strawberry**: 20 Pts
  - ⭐ **Starfruit (Golden)**: 50 Pts
  - 💣 **Bomb**: -30 Pts penalty & resets combo!
- **Combos**: Slicing multiple fruits in rapid succession (within 0.5s) builds combos:
  - 2+ slices = **x2 COMBO!**
  - 4+ slices = **x3 COMBO!**

### 3. Interactive Hand-Controlled Buttons
You never have to touch the keyboard during gameplay:
- ⏸️ **Pause Match**: Hover your hand over the top **`|| PAUSE`** button for 0.8s, or slice right through it.
- ▶️ **Resume Match**: From the Pause screen, hover over or slice **`> RESUME`**.
- 🛑 **Quit Match**: Hover over or slice the **`X QUIT`** button in the top bar, in the Pause menu, or on the Game Over screen.
- ⏱️ **Timer Presets**: In the Main Menu, hover your hand over any timer button (`30s`, `60s`, `90s`, `120s`, `Endless`) to select it.
- 🍉 **Start & Rematch**: Slice the floating watermelon in the center!

---

## ⌨️ Controls & Shortcuts

| Action | Hand Motion | Keyboard / Mouse |
|---|---|---|
| **Slice / Play** | Swift slash with index finger | Left/Right Drag (Mouse Fallback) |
| **Pause / Resume** | Hover or slice `|| PAUSE` / `> RESUME` | `Space` or `P` |
| **Quit Game** | Hover or slice `X QUIT` button | `Q` or `ESC` |
| **Select Timer** | Hover over 30s/60s/90s/120s/Endless | Keys `1`, `2`, `3`, `4`, `5` |
| **Rematch** | Slice the Rematch Watermelon | `R` |
| **Main Menu** | — | `M` |

---

## 🚀 Quick Start

Double-click **`run_game.bat`** or run:

```bash
python main.py
```
