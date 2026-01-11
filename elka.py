import sys
import time
import random
import shutil
import math
from collections import deque
import threading

CSI = "\x1b["
HIDE_CURSOR = CSI + "?25l"
SHOW_CURSOR = CSI + "?25h"
CLEAR = CSI + "2J"
HOME = CSI + "H"
RESET = CSI + "0m"

def color_fg(code: int) -> str:
    return f"{CSI}38;5;{code}m"

COL_SNOW = 255
COL_SNOW_DIM = 245
COL_TREE = 43
COL_TRUNK = 179
COL_STAR = 220

COL_CAT = 208
COL_EYES = 46

COL_GIFT_RED = 196
COL_GIFT_GREEN = 46
COL_GIFT_GOLD = 220
COL_GIFT_WHITE = 255

BULB_COLS = [201, 82, 226, 45, 214, 39]

SNOW_CHARS = ["·", ".", "*", "+"]
TREE_CHAR = "x"
TRUNK_CHAR = "m"
STAR_CHAR = "*"

FPS = 30
SPEED_MIN = 1.4
SPEED_MAX = 4.2
TAIL_LEN = 3
MIN_BULBS_ON = 5

VER_TEXT = "ver 2.0"

def clamp(v, a, b):
    return max(a, min(b, v))

MUSIC_ENABLED = True

def _play_melody_loop(stop_event: threading.Event):
    try:
        import winsound  
    except Exception:
        return

    melody = [
        (659, 140), (659, 140), (659, 220),
        (659, 140), (659, 140), (659, 220),
        (659, 140), (784, 140), (523, 140), (587, 140), (659, 260),
        (698, 140), (698, 140), (698, 220),
        (698, 140), (659, 140), (659, 140), (659, 140),
        (659, 140), (587, 140), (587, 140), (659, 140), (587, 220), (784, 220),
    ]

    while not stop_event.is_set():
        for freq, dur in melody:
            if stop_event.is_set():
                break
            try:
                winsound.Beep(freq, dur)
            except Exception:
                return
        time.sleep(0.35)

class Snow:
    __slots__ = ("x", "y", "vy", "phase", "wob", "ch", "trail")

    def __init__(self, w: int, ground_y: int):
        self.trail = deque(maxlen=TAIL_LEN)
        self.respawn(w, ground_y, initial=True)

    def respawn(self, w: int, ground_y: int, initial: bool = False):
        self.x = random.randint(0, max(0, w - 1))
        if initial:
            self.y = random.uniform(0, max(1, ground_y - 1))
        else:
            self.y = random.uniform(-ground_y * 0.6, -1.0)

        self.vy = random.uniform(SPEED_MIN, SPEED_MAX)
        self.phase = random.uniform(0, math.tau)
        self.wob = random.uniform(0.25, 1.15)
        self.ch = random.choice(SNOW_CHARS)
        self.trail.clear()

    def draw_x(self, t: float, w: int) -> int:
        dx = int(round(math.sin(t * 1.05 + self.phase) * self.wob))
        return clamp(self.x + dx, 0, w - 1)

    def step(self, dt: float, w: int, ground_y: int, t: float):
        self.trail.appendleft((self.draw_x(t, w), int(self.y)))
        self.y += self.vy * dt

        if int(self.y) >= ground_y:
            self.respawn(w, ground_y, initial=False)

def build_tree(w: int, ground_y: int):
    cx = w // 2
    trunk_h = 4
    trunk_w = 5

    trunk_bottom_y = ground_y - 1
    trunk_top_y = trunk_bottom_y - (trunk_h - 1)

    max_rows_by_height = max(10, trunk_top_y - 3)  
    rows = clamp(16, 10, min(18, max_rows_by_height))

    crown_bottom_y = trunk_top_y - 2
    top = crown_bottom_y - (rows - 1)

    tree_points = []
    bulbs = []

    for r in range(rows):
        width = 1 + r * 2
        y = top + r
        start_x = cx - width // 2
        for i in range(width):
            x = start_x + i
            if random.random() < 0.86:
                if random.random() < 0.12 and 2 < r < rows - 2:
                    bulbs.append({
                        "x": x,
                        "y": y,
                        "phase": random.uniform(0, math.tau),
                        "speed": random.uniform(2.0, 6.0),
                        "ci": random.randrange(len(BULB_COLS)),
                    })
                else:
                    tree_points.append((x, y))

    # если ламп мало — добьём
    if len(bulbs) < 10:
        candidates = [(x, y) for (x, y) in tree_points if y > top + 2 and y < top + rows - 2]
        random.shuffle(candidates)
        while len(bulbs) < 10 and candidates:
            x, y = candidates.pop()
            bulbs.append({
                "x": x,
                "y": y,
                "phase": random.uniform(0, math.tau),
                "speed": random.uniform(2.0, 6.0),
                "ci": random.randrange(len(BULB_COLS)),
            })
            tree_points.remove((x, y))

    trunk_points = []
    for dy in range(trunk_h):
        y = trunk_top_y + dy
        for dx in range(trunk_w):
            x = cx - trunk_w // 2 + dx
            trunk_points.append((x, y))

    star = (cx, top - 1)

    half_width = rows - 1
    return tree_points, bulbs, trunk_points, star, cx, top, rows, half_width, trunk_top_y, trunk_bottom_y

def put(frame, x, y, ch, col, w, h):
    if 0 <= x < w and 0 <= y < h:
        frame[y][x] = [ch, col]

def draw_text(frame, x, y, text, col, w, h):
    for i, c in enumerate(text):
        put(frame, x + i, y, c, col, w, h)

def draw_cat(frame, x, base_y, t, w, h):
    tail = "~" if int(t * 6) % 2 == 0 else "="
    lines = [
        " /\\_/\\ ",
        "( o o )",
        " > ^ < ",
        "(  -  )",
        "  U U  ",
        f"   {tail}   ",
    ]

    top_y = base_y - len(lines)
    for dy, line in enumerate(lines):
        for dx, ch in enumerate(line):
            if ch == "o":
                put(frame, x + dx, top_y + dy, "o", COL_EYES, w, h)
            elif ch != " ":
                put(frame, x + dx, top_y + dy, ch, COL_CAT, w, h)

def draw_gift(frame, x, base_y, t, w, h):
    bow = "*" if int(t * 4) % 2 == 0 else "+"
    lines = [
        f" {bow}{bow} ",
        "┌─┬─┐",
        "│ │ │",
        "├─┼─┤",
        "└─┴─┘",
    ]
    top_y = base_y - len(lines)

    for dy, line in enumerate(lines):
        for dx, ch in enumerate(line):
            if ch in (bow,):
                put(frame, x + dx, top_y + dy, ch, COL_GIFT_GOLD, w, h)
            elif ch in ("│", "┼", "┬", "┴"):
                put(frame, x + dx, top_y + dy, ch, COL_GIFT_GREEN, w, h)
            elif ch != " ":
                put(frame, x + dx, top_y + dy, ch, COL_GIFT_RED, w, h)

def main():
    sys.stdout.write(HIDE_CURSOR + CLEAR)
    sys.stdout.flush()

    last = time.time()
    last_size = (0, 0)

    music_stop = threading.Event()
    music_thread = None

    try:
        while True:
            now = time.time()
            dt = now - last
            last = now

            tw, th = shutil.get_terminal_size((100, 30))

            w = max(60, tw - 1)
            h = max(24, th)

            ground_y1 = h - 3
            ground_y2 = h - 2

            if (w, h) != last_size:
                snow = [Snow(w, ground_y1) for _ in range(int(w * ground_y1 * 0.02))]

                tree_points, bulbs, trunk_points, star, cx, top, rows, half_w, trunk_top_y, trunk_bottom_y = build_tree(w, ground_y1)

                last_size = (w, h)
                sys.stdout.write(CLEAR)

                if MUSIC_ENABLED and music_thread is None:
                    music_thread = threading.Thread(target=_play_melody_loop, args=(music_stop,), daemon=True)
                    music_thread.start()

            frame = [[[" ", None] for _ in range(w)] for _ in range(h)]

            for s in snow:
                s.step(dt, w, ground_y1, now)

                for i, (tx, ty) in enumerate(s.trail):
                    if 0 <= ty < ground_y1:
                        put(frame, tx, ty, ".", COL_SNOW_DIM, w, h)

                y = int(s.y)
                if 0 <= y < ground_y1:
                    put(frame, s.draw_x(now, w), y, s.ch, COL_SNOW, w, h)

            for x, y in tree_points:
                if y < ground_y1:
                    put(frame, x, y, TREE_CHAR, COL_TREE, w, h)

            put(frame, star[0], star[1], STAR_CHAR, COL_STAR, w, h)

            brightness = []
            for i, b in enumerate(bulbs):
                v = 0.5 + 0.5 * math.sin(now * b["speed"] + b["phase"])
                brightness.append((v, i))
            brightness.sort(reverse=True)
            force_on = {i for _, i in brightness[:MIN_BULBS_ON]}

            for i, b in enumerate(bulbs):
                x, y = b["x"], b["y"]
                if 0 <= y < ground_y1:
                    v = 0.5 + 0.5 * math.sin(now * b["speed"] + b["phase"])
                    if i in force_on or v > 0.62:
                        put(frame, x, y, "o", BULB_COLS[b["ci"]], w, h)
                    else:
                        put(frame, x, y, ".", 240, w, h)

            for x, y in trunk_points:
                if y < ground_y1:
                    put(frame, x, y, TRUNK_CHAR, COL_TRUNK, w, h)

            base_plane_y = ground_y1

            gift_x = clamp(cx - half_w + 2, 1, w - 8)
            draw_gift(frame, gift_x, base_plane_y, now, w, h)

            cat_x = clamp(cx + half_w + 6, 1, w - 10)
            draw_cat(frame, cat_x, base_plane_y, now, w, h)

            for x in range(w):
                put(frame, x, ground_y1, ".", 252, w, h)
                put(frame, x, ground_y2, ".", 252, w, h)

            vx = max(2, w - len(VER_TEXT) - 2)
            draw_text(frame, vx, ground_y1, VER_TEXT, 250, w, h)

            out = []
            for row in frame:
                line = []
                cur = None
                for ch, col in row:
                    if col != cur:
                        line.append(RESET if col is None else color_fg(col))
                        cur = col
                    line.append(ch)
                line.append(RESET)
                out.append("".join(line))

            sys.stdout.write(HOME + "\n".join(out))
            sys.stdout.flush()

            time.sleep(1 / FPS)

    except KeyboardInterrupt:
        pass
    finally:
        music_stop.set()
        sys.stdout.write(RESET + SHOW_CURSOR)
        sys.stdout.flush()

if __name__ == "__main__":
    main()
