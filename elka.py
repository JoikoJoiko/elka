import os
import sys
import time
import random
import shutil
import math

CSI = "\x1b["
HIDE_CURSOR = CSI + "?25l"
SHOW_CURSOR = CSI + "?25h"
CLEAR = CSI + "2J"
HOME = CSI + "H"

def color_fg(code: int) -> str:
    return f"{CSI}38;5;{code}m"

RESET = CSI + "0m"

COL_SNOW = 255
COL_TREE = 43
COL_TRUNK = 179
BULB_COLS = [201, 82, 226, 45, 214, 39]  

SNOW_CHARS = ["·", ".", "✶", "✳", "❄"]
TREE_CHAR = "×"
TRUNK_CHAR = "m"

class Snow:
    __slots__ = ("x", "y", "vy", "phase", "wob", "char", "col")
    def __init__(self, w, h):
        self.x = random.randint(0, max(0, w-1))
        self.y = random.random() * h
        self.vy = random.uniform(6.0, 18.0)     
        self.phase = random.uniform(0, math.tau)
        self.wob = random.uniform(0.6, 2.0)
        self.char = random.choice(SNOW_CHARS)
        self.col = COL_SNOW

    def step(self, dt, w, h, t):
        self.y += self.vy * dt
        if self.y >= h:
            self.y = 0
            self.x = random.randint(0, max(0, w-1))
            self.vy = random.uniform(6.0, 18.0)
            self.phase = random.uniform(0, math.tau)
            self.wob = random.uniform(0.6, 2.0)
            self.char = random.choice(SNOW_CHARS)

    def draw_x(self, t, w):
        dx = int(round(math.sin(t * 1.2 + self.phase) * self.wob))
        return max(0, min(w-1, self.x + dx))

def build_tree(w, h):
    """
    Returns:
      tree_points: list of (x, y) for green parts
      bulbs: list of dict {x,y,phase,speed,color_index}
      trunk_points: list of (x, y)
      ground_y: int
    """
    cx = w // 2
    top = max(2, h // 5)
    rows = min(18, max(10, h - top - 8))

    tree_points = []
    bulbs = []
    cell = 1

    for r in range(rows):
        width = 1 + r * 2
        y = top + r * cell
        start_x = cx - (width // 2)
        for i in range(width):
            x = start_x + i
            if random.random() < 0.85:
                if random.random() < 0.10 and 2 < r < rows - 2:
                    bulbs.append({
                        "x": x,
                        "y": y,
                        "phase": random.uniform(0, math.tau),
                        "speed": random.uniform(3.0, 9.0),
                        "ci": random.randrange(len(BULB_COLS)),
                    })
                else:
                    tree_points.append((x, y))

    trunk_points = []
    trunk_h = 4
    trunk_w = 5
    base_y = top + rows + 1
    for r in range(trunk_h):
        y = base_y + r
        for i in range(trunk_w):
            x = cx - trunk_w // 2 + i
            trunk_points.append((x, y))

    ground_y = base_y + trunk_h + 1
    return tree_points, bulbs, trunk_points, ground_y

def main():
    w, h = shutil.get_terminal_size((100, 30))
    w = max(40, w)
    h = max(20, h)

    snow_count = int(w * h * 0.015)  
    snow = [Snow(w, h) for _ in range(snow_count)]
    tree_points, bulbs, trunk_points, ground_y = build_tree(w, h)

    def blank_frame():
        return [[" ", None] for _ in range(w)]

    last = time.time()

    sys.stdout.write(HIDE_CURSOR + CLEAR)
    sys.stdout.flush()

    try:
        while True:
            now = time.time()
            dt = now - last
            last = now
            t = now

            for s in snow:
                s.step(dt, w, h, t)

            frame = [blank_frame() for _ in range(h)]

            for s in snow:
                y = int(s.y)
                if 0 <= y < h:
                    x = s.draw_x(t, w)
                    frame[y][x] = [s.char, s.col]

            for (x, y) in tree_points:
                if 0 <= y < h and 0 <= x < w:
                    frame[y][x] = [TREE_CHAR, COL_TREE]

            for b in bulbs:
                x, y = b["x"], b["y"]
                if 0 <= y < h and 0 <= x < w:
                    blink = 0.5 + 0.5 * math.sin(t * b["speed"] + b["phase"])
                    if blink > 0.55:
                        col = BULB_COLS[b["ci"]]
                        frame[y][x] = ["o", col]
                    else:
                        frame[y][x] = ["·", 240]

            for (x, y) in trunk_points:
                if 0 <= y < h and 0 <= x < w:
                    frame[y][x] = [TRUNK_CHAR, COL_TRUNK]

            if 0 <= ground_y < h:
                for x in range(w):
                    if random.random() < 0.4:
                        frame[ground_y][x] = ["·", 250]
                    else:
                        frame[ground_y][x] = [" ", None]

            out_lines = []
            for row in frame:
                line = []
                current = None
                for ch, col in row:
                    if col != current:
                        if col is None:
                            line.append(RESET)
                        else:
                            line.append(color_fg(col))
                        current = col
                    line.append(ch)
                line.append(RESET)
                out_lines.append("".join(line))

            sys.stdout.write(HOME + "\n".join(out_lines))
            sys.stdout.flush()

            time.sleep(1/30)  
    except KeyboardInterrupt:
        pass
    finally:
        sys.stdout.write(RESET + SHOW_CURSOR + "\n")
        sys.stdout.flush()

if __name__ == "__main__":
    main()
