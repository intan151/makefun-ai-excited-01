#!/usr/bin/env python3
"""Koi ascending the falls toward the moon.

A golden koi leaps up a glowing waterfall toward a full moon, its tail
dissolving into ribbons of light: the moment a koi becomes a dragon.
Procedural art, Python 3.13 standard library only. Fully deterministic:
fixed seed, no clock, no network, no input files.

Writes one 1024x1024 PNG to $MAKEFUN_OUTPUT_DIR/entry.png (default /output).
"""
import math
import os
import random
import struct
import zlib

W = H = 1024
fb = bytearray(W * H * 3)
RNG = random.Random(20261117)


# ---------------- framebuffer ----------------

def _fill_row(y, x0, x1, rgb):
    if x1 <= x0 or y < 0 or y >= H:
        return
    x0 = max(0, x0)
    x1 = min(W, x1)
    if x1 <= x0:
        return
    fb[(y * W + x0) * 3:(y * W + x1) * 3] = bytes(rgb) * (x1 - x0)


def _blend_row(y, x0, x1, rgb, alpha):
    if x1 <= x0 or y < 0 or y >= H or alpha <= 0.0:
        return
    x0 = max(0, x0)
    x1 = min(W, x1)
    if x1 <= x0:
        return
    if alpha >= 1.0:
        _fill_row(y, x0, x1, rgb)
        return
    r, g, b = rgb
    ia = 1.0 - alpha
    base = (y * W + x0) * 3
    for k in range(x1 - x0):
        i = base + k * 3
        fb[i] = int(r * alpha + fb[i] * ia)
        fb[i + 1] = int(g * alpha + fb[i + 1] * ia)
        fb[i + 2] = int(b * alpha + fb[i + 2] * ia)


def disc(cx, cy, r, rgb, alpha=1.0):
    if r <= 0:
        return
    r2 = r * r
    y0 = max(0, int(cy - r))
    y1 = min(H, int(cy + r) + 1)
    for y in range(y0, y1):
        dy = y - cy
        dx = math.sqrt(max(0.0, r2 - dy * dy))
        x0 = int(math.ceil(cx - dx))
        x1 = int(math.floor(cx + dx)) + 1
        if alpha >= 1.0:
            _fill_row(y, x0, x1, rgb)
        else:
            _blend_row(y, x0, x1, rgb, alpha)


def poly(pts, rgb, alpha=1.0):
    ys = [p[1] for p in pts]
    y0 = max(0, int(min(ys)))
    y1 = min(H, int(max(ys)) + 1)
    n = len(pts)
    for y in range(y0, y1):
        xs = []
        for i in range(n):
            x1, y1p = pts[i]
            x2, y2p = pts[(i + 1) % n]
            if (y1p <= y < y2p) or (y2p <= y < y1p):
                t = (y - y1p) / (y2p - y1p)
                xs.append(x1 + t * (x2 - x1))
        xs.sort()
        for j in range(0, len(xs) - 1, 2):
            x0 = int(math.ceil(xs[j]))
            x1 = int(math.floor(xs[j + 1])) + 1
            if alpha >= 1.0:
                _fill_row(y, x0, x1, rgb)
            else:
                _blend_row(y, x0, x1, rgb, alpha)


def catmull_rom(points, samples=20):
    pts = [points[0]] + list(points) + [points[-1]]
    out = []
    for i in range(len(pts) - 3):
        p0, p1, p2, p3 = pts[i], pts[i + 1], pts[i + 2], pts[i + 3]
        for s in range(samples):
            t = s / samples
            t2 = t * t
            t3 = t2 * t
            x = 0.5 * ((2 * p1[0]) + (-p0[0] + p2[0]) * t
                       + (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2
                       + (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3)
            y = 0.5 * ((2 * p1[1]) + (-p0[1] + p2[1]) * t
                       + (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2
                       + (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3)
            out.append((x, y))
    out.append(points[-1])
    return out


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def lerp_stops(stops, t):
    if t <= stops[0][0]:
        return stops[0][1]
    for i in range(len(stops) - 1):
        t0, c0 = stops[i]
        t1, c1 = stops[i + 1]
        if t0 <= t <= t1:
            return lerp(c0, c1, (t - t0) / (t1 - t0))
    return stops[-1][1]


def tube(points, radii, c0, c1, alpha=1.0):
    n = len(points)
    for i, (x, y) in enumerate(points):
        t = i / max(1, n - 1)
        disc(x, y, radii[i], lerp(c0, c1, t), alpha)


def tube_stops(points, radii, stops, alpha=1.0):
    n = len(points)
    for i, (x, y) in enumerate(points):
        t = i / max(1, n - 1)
        disc(x, y, radii[i], lerp_stops(stops, t), alpha)


def normals(points):
    n = len(points)
    out = []
    for i in range(n):
        x0, y0 = points[max(0, i - 1)]
        x1, y1 = points[min(n - 1, i + 1)]
        dx, dy = x1 - x0, y1 - y0
        m = math.hypot(dx, dy) or 1.0
        nx, ny = -dy / m, dx / m
        if ny < 0:  # belly side: normal with positive y (downward)
            nx, ny = -nx, -ny
        out.append((nx, ny))
    return out


# ---------------- scene ----------------

def draw():
    # Sky: deep indigo to teal.
    top = (9, 13, 45)
    bot = (13, 52, 72)
    for y in range(800):
        _fill_row(y, 0, W, lerp(top, bot, y / 800.0))

    # Stars.
    for _ in range(90):
        x = RNG.uniform(0, W)
        y = RNG.uniform(0, 650)
        if math.hypot(x - 800, y - 195) < 150:
            continue
        disc(x, y, RNG.uniform(1.0, 2.5), (255, 255, 255),
             RNG.uniform(0.35, 0.9))

    # Moon glow + moon.
    for r, a in ((260, 0.05), (190, 0.08), (140, 0.12)):
        disc(800, 195, r, (245, 225, 170), a)
    disc(800, 195, 105, (250, 238, 200))
    for (cx, cy, r) in ((770, 170, 16), (825, 220, 12), (790, 240, 9),
                        (835, 175, 8), (760, 215, 6)):
        disc(cx, cy, r, (232, 212, 168), 0.8)

    # Light rays from the moon toward the koi.
    poly([(700, 280), (860, 300), (760, 430), (640, 390)],
         (250, 220, 150), 0.05)
    poly([(740, 250), (830, 265), (780, 380), (700, 350)],
         (250, 220, 150), 0.06)

    # Waterfall: wavy luminous band, top to waterline.
    left = [(370 + 35 * math.sin(y / 130.0), y) for y in range(0, 801, 40)]
    right = [(650 + 35 * math.sin(y / 170.0 + 1.3), y)
             for y in range(800, -1, -40)]
    poly(left + right, (185, 232, 238))
    # Falls streaks (dense samples so the strokes are continuous).
    for _ in range(14):
        x = RNG.uniform(400, 620)
        pts = [(x + 18 * math.sin(y / 90.0 + x), y)
               for y in range(0, 801, 60)]
        spts = catmull_rom(pts, 30)
        tube(spts, [RNG.uniform(3, 6)] * len(spts),
             (255, 255, 255), (220, 245, 250), 0.45)
    for _ in range(6):
        x = RNG.uniform(400, 620)
        pts = [(x + 18 * math.sin(y / 90.0 + x), y)
               for y in range(0, 801, 60)]
        spts = catmull_rom(pts, 30)
        tube(spts, [RNG.uniform(2, 4)] * len(spts),
             (140, 200, 215), (140, 200, 215), 0.5)

    # Water at the bottom.
    for y in range(800, H):
        _fill_row(y, 0, W, lerp((10, 44, 62), (6, 30, 46), (y - 800) / 224.0))
    # Wave arcs (dense samples so the strokes are continuous).
    for wy, amp in ((850, 14), (890, 18), (930, 22), (970, 18), (1010, 14)):
        pts = [(x, wy + amp * math.sin(x / 160.0 + wy)) for x in range(0, 1025, 64)]
        wpts = catmull_rom(pts, 30)
        tube(wpts, [4] * len(wpts), (255, 255, 255),
             (200, 240, 245), 0.5)
    # Moon reflection: shimmering dashes under the moon.
    for _ in range(12):
        disc(790 + RNG.uniform(-30, 30), RNG.uniform(830, 1000),
             RNG.uniform(5, 9), (250, 220, 150), 0.3)

    # Mist at the foot of the falls.
    for (cx, cy, r) in ((300, 780, 200), (700, 800, 240), (520, 760, 180)):
        disc(cx, cy, r, (200, 230, 235), 0.05)

    # ---- The koi ----
    ctrl = [(425, 815), (480, 720), (565, 650), (585, 545),
            (650, 460), (700, 395), (720, 370)]
    path = catmull_rom(ctrl, 24)
    n = len(path)
    profile = [(0.0, 16), (0.15, 30), (0.4, 55), (0.6, 58), (0.8, 48),
               (1.0, 36)]

    def radius_at(t):
        for i in range(len(profile) - 1):
            t0, r0 = profile[i]
            t1, r1 = profile[i + 1]
            if t0 <= t <= t1:
                return r0 + (r1 - r0) * (t - t0) / (t1 - t0)
        return profile[-1][1]

    radii = [radius_at(i / max(1, n - 1)) for i in range(n)]
    ns = normals(path)
    body_stops = [(0.0, (198, 62, 32)), (0.45, (238, 122, 38)),
                  (0.75, (250, 172, 70)), (1.0, (255, 208, 115))]

    # Tail ribbons: the tail dissolves into two flowing ribbons of light
    # that sweep back along the water (drawn first, so the body overlaps
    # their roots).
    tail = path[0]
    for (pts, c0, c1) in (
            (catmull_rom([tail,
                          (tail[0] - 60, tail[1] + 10),
                          (tail[0] - 150, tail[1] - 10),
                          (tail[0] - 230, tail[1] + 25)], 16),
             (255, 190, 80), (220, 60, 30)),
            (catmull_rom([tail,
                          (tail[0] - 40, tail[1] + 45),
                          (tail[0] - 110, tail[1] + 70),
                          (tail[0] - 180, tail[1] + 110)], 16),
             (250, 160, 60), (200, 50, 40))):
        m = len(pts)
        rr = [20 * (1 - i / max(1, m - 1)) + 3 for i in range(m)]
        tube_stops(pts, rr, [(0.0, c0), (1.0, c1)], 0.95)

    # Dark outline, then body.
    tube(path, [r + 4 for r in radii], (120, 40, 20), (120, 40, 20))
    tube_stops(path, radii, body_stops)

    # Belly: cream stripe on the underside (+normal side), kept narrow so
    # the orange back stays dominant.
    belly_pts = [(path[i][0] + ns[i][0] * radii[i] * 0.55,
                  path[i][1] + ns[i][1] * radii[i] * 0.55) for i in range(n)]
    tube(belly_pts, [r * 0.38 for r in radii], (255, 226, 175),
         (255, 240, 210), 0.95)
    # Back stripe: deep red along the top (-normal side).
    back_pts = [(path[i][0] - ns[i][0] * radii[i] * 0.42,
                 path[i][1] - ns[i][1] * radii[i] * 0.42) for i in range(n)]
    tube(back_pts, [r * 0.26 for r in radii], (170, 50, 25),
         (200, 70, 30), 0.9)
    # Scale hints along the upper body.
    for i in range(6, n - 6, 9):
        disc(path[i][0] - ns[i][0] * radii[i] * 0.1,
             path[i][1] - ns[i][1] * radii[i] * 0.1, 6, (170, 60, 30), 0.45)

    # Dorsal fin (top side, mid-body): swept back, smaller.
    i0, i1 = int(n * 0.40), int(n * 0.54)
    mid = (i0 + i1) // 2
    apex = (path[mid][0] - ns[mid][0] * (radii[mid] + 55) - 18,
            path[mid][1] - ns[mid][1] * (radii[mid] + 55) + 6)
    poly([
        (path[i0][0] - ns[i0][0] * radii[i0] * 0.8,
         path[i0][1] - ns[i0][1] * radii[i0] * 0.8),
        apex,
        (path[i1][0] - ns[i1][0] * radii[i1] * 0.8,
         path[i1][1] - ns[i1][1] * radii[i1] * 0.8),
        (path[mid][0] - ns[mid][0] * radii[mid] * 0.8,
         path[mid][1] - ns[mid][1] * radii[mid] * 0.8),
    ], (235, 110, 45), 0.85)

    # Pectoral fins (belly side, near the head): small and swept.
    for (ti, sgn) in ((0.82, 1), (0.88, -1)):
        i = int(n * ti)
        base = (path[i][0] + ns[i][0] * radii[i] * 0.7,
                path[i][1] + ns[i][1] * radii[i] * 0.7)
        tip = (base[0] + ns[i][0] * 34 + sgn * 18,
               base[1] + ns[i][1] * 34 + 28)
        poly([base,
              (base[0] + sgn * 20, base[1] + 4),
              tip,
              (base[0] - sgn * 6, base[1] + 16)],
             (240, 120, 50), 0.75)

    # Head details.
    hx, hy = path[-1]
    hnx, hny = ns[-1]  # belly-side normal at head
    # Horns (dragon): short, curving back from the top of the head.
    for sgn in (1, -1):
        pts = catmull_rom([
            (hx - hnx * 20 + sgn * 14, hy - hny * 20),
            (hx - hnx * 38 + sgn * 30, hy - hny * 38 - 10),
            (hx - hnx * 56 + sgn * 48, hy - hny * 56 - 16),
        ], 12)
        m = len(pts)
        tube(pts, [6 * (1 - i / max(1, m - 1)) + 1.5 for i in range(m)],
             (255, 220, 140), (255, 200, 110))
    # Mane wisps behind the head.
    for k, sgn in enumerate((1, -1, 0)):
        pts = catmull_rom([
            (hx - hnx * 26 + sgn * 10, hy - hny * 26),
            (hx - hnx * 70 + sgn * 40, hy - hny * 60 + 20 + k * 8),
            (hx - hnx * 110 + sgn * 70, hy - hny * 95 + 40 + k * 10),
        ], 12)
        m = len(pts)
        tube(pts, [4 * (1 - i / max(1, m - 1)) + 1 for i in range(m)],
             (200, 60, 40), (230, 90, 50), 0.9)
    # Whiskers from the snout, reaching toward the moon.
    snout = (hx + 26, hy - 22)
    for sgn in (1, -1):
        pts = catmull_rom([
            snout,
            (snout[0] + 45, snout[1] - 8 + sgn * 26),
            (snout[0] + 95, snout[1] - 30 + sgn * 55),
        ], 12)
        m = len(pts)
        tube(pts, [3 * (1 - i / max(1, m - 1)) + 1 for i in range(m)],
             (255, 220, 140), (255, 200, 110))
    # Eye: bright, looking up at the moon.
    ex, ey = hx + 12, hy - 10
    disc(ex, ey, 11, (255, 250, 235))
    disc(ex + 2, ey - 2, 5.5, (30, 20, 15))
    disc(ex - 1, ey - 4, 2.5, (255, 255, 255))

    # Splash where the tail leaves the water.
    for _ in range(18):
        ang = RNG.uniform(-0.2, math.pi + 0.2)
        d = RNG.uniform(10, 95)
        disc(425 + math.cos(ang) * d, 805 - abs(math.sin(ang)) * 55,
             RNG.uniform(3, 13),
             (255, 255, 255) if RNG.random() < 0.6 else (200, 240, 245),
             RNG.uniform(0.75, 0.95))
    for _ in range(8):
        disc(RNG.uniform(380, 700), RNG.uniform(700, 800),
             RNG.uniform(2, 5), (255, 255, 255), 0.8)

    # Cherry-blossom petals drifting across the scene.
    for _ in range(26):
        cx = RNG.uniform(30, 994)
        cy = RNG.uniform(30, 994)
        s = RNG.uniform(7, 13)
        a = RNG.uniform(0, math.pi)
        ca, sa = math.cos(a), math.sin(a)
        pts = []
        for (px, py) in ((0, -s), (s * 0.7, 0), (0, s), (-s * 0.7, 0)):
            pts.append((cx + px * ca - py * sa, cy + px * sa + py * ca))
        poly(pts, (247, 168, 196) if RNG.random() < 0.7 else (232, 120, 160),
             0.9)


# ---------------- PNG output ----------------

def write_png(path):
    raw = bytearray()
    for y in range(H):
        raw.append(0)
        raw += fb[y * W * 3:(y + 1) * W * 3]
    comp = zlib.compress(bytes(raw), 9)

    def chunk(typ, data):
        out = struct.pack(">I", len(data)) + typ + data
        out += struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF)
        return out

    ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
    png = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
           + chunk(b"IDAT", comp) + chunk(b"IEND", b""))
    with open(path, "wb") as f:
        f.write(png)


def main():
    draw()
    outdir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(outdir, exist_ok=True)
    write_png(os.path.join(outdir, "entry.png"))


if __name__ == "__main__":
    main()
