"""Golden koi leaping up a moonlit waterfall toward the full moon.

Pure Python 3.13, standard library only. No randomness, no clock, no
network: every pixel is a deterministic function of its coordinates.
Draws one 768x768 PNG to $MAKEFUN_OUTPUT_DIR/entry.png (default /output).
"""

import math
import os
import struct
import zlib

W = 768
H = 768
WATER_Y = 560
MOON_X, MOON_Y, MOON_R = 565, 140, 92

SIN = math.sin
COS = math.cos
SQRT = math.sqrt


def h2(x, y):
    """Deterministic hash of integer grid coords -> float in [0, 1)."""
    n = (x * 374761393 + y * 668265263) & 0xFFFFFFFF
    n = ((n ^ (n >> 13)) * 1274126177) & 0xFFFFFFFF
    n = (n ^ (n >> 16)) & 0xFFFFFFFF
    return n / 4294967296.0


def mix3(c1, c2, t):
    return (c1[0] + (c2[0] - c1[0]) * t,
            c1[1] + (c2[1] - c1[1]) * t,
            c1[2] + (c2[2] - c1[2]) * t)


# Fixed splash droplets: (x, y, radius)
DROPS = (
    (318, 540, 16), (345, 528, 12), (292, 548, 10), (372, 542, 9),
    (330, 512, 7), (360, 505, 6), (300, 500, 5), (388, 520, 6),
    (410, 470, 5), (452, 440, 4), (280, 470, 5), (255, 520, 8),
    (300, 556, 20), (330, 560, 24), (360, 556, 18), (285, 562, 14),
    (250, 545, 9), (395, 545, 8),
)


def render():
    # Koi body: nose up-right at -35 degrees.
    th = -0.61
    c = COS(th)
    s = SIN(th)
    # Tail fin: same centre line, fanned open.
    tht = -0.16
    ct = COS(tht)
    st = SIN(tht)
    # Tail centre on screen.
    tx, ty = 285, 500
    # Eye centre on screen.
    ex, ey = 507, 327

    sky_stops = ((0.0, (10, 14, 34)), (0.45, (26, 26, 66)),
                 (0.75, (74, 52, 104)), (1.0, (196, 104, 52)))
    rows = []
    for y in range(H):
        # ---- row sky / water base colour ----
        if y < WATER_Y:
            t = y / WATER_Y
            if t < 0.45:
                f = t / 0.45
                sr, sg, sb = mix3(sky_stops[0][1], sky_stops[1][1], f)
            elif t < 0.75:
                f = (t - 0.45) / 0.30
                sr, sg, sb = mix3(sky_stops[1][1], sky_stops[2][1], f)
            else:
                f = (t - 0.75) / 0.25
                sr, sg, sb = mix3(sky_stops[2][1], sky_stops[3][1], f)
            wt = 0.0
        else:
            f = (y - WATER_Y) / (H - WATER_Y)
            sr = 7 + (5 - 7) * f
            sg = 38 + (22 - 38) * f
            sb = 50 + (36 - 50) * f
            wt = 1.0
        dy_moon = y - MOON_Y
        dy_moon2 = dy_moon * dy_moon
        sy_fall = SIN(y * 0.06)
        row = bytearray(W * 3)
        for x in range(W):
            r, g, b = sr, sg, sb
            # ---- stars (sky only) ----
            if y < 430:
                cx = x // 26
                cy = y // 26
                if h2(cx, cy) < 0.10:
                    sx = cx * 26 + int(h2(cx, cy + 7) * 22) + 2
                    syy = cy * 26 + int(h2(cx + 3, cy) * 22) + 2
                    ddx = x - sx
                    ddy = y - syy
                    d2 = ddx * ddx + ddy * ddy
                    if d2 < 5.0:
                        br = (1.0 - d2 / 5.0) * 200.0
                        r += br
                        g += br
                        b += br
            # ---- moon disc + glow ----
            dxm = x - MOON_X
            d2m = dxm * dxm + dy_moon2
            if d2m < MOON_R * MOON_R:
                r, g, b = 255.0, 243.0, 212.0
                # subtle craters
                for crx, cry, crr in ((540, 120, 18), (585, 160, 14),
                                      (560, 110, 10)):
                    ddx = x - crx
                    ddy = y - cry
                    if ddx * ddx + ddy * ddy < crr * crr:
                        r, g, b = 232.0, 220.0, 188.0
                        break
            else:
                gl = 9000.0 / (9000.0 + d2m)
                r += 255.0 * gl * 0.55
                g += 220.0 * gl * 0.55
                b += 150.0 * gl * 0.55
            # ---- waterfall (sky side) ----
            if y < WATER_Y and 150 <= x <= 250:
                streak = 0.84 + 0.16 * SIN(x * 0.55 + sy_fall * 1.5)
                fr, fg, fb = 168.0 * streak, 208.0 * streak, 224.0 * streak
                foam = 0.12 * max(0.0, SIN(y * 0.32))
                fr += 255.0 * foam
                fg += 255.0 * foam
                fb += 255.0 * foam
                a = 0.92
                r = fr * a + r * (1.0 - a)
                g = fg * a + g * (1.0 - a)
                b = fb * a + b * (1.0 - a)
            # ---- waterfall mist near the base ----
            if 500 <= y < WATER_Y:
                hw = 50.0 + (y - 500) * 0.7
                if abs(x - 200) < hw:
                    ma = (1.0 - (y - 500) / 60.0) * 0.5
                    ma *= 0.6 + 0.4 * SIN(x * 0.3 + y * 0.1)
                    r = 225.0 * ma + r * (1.0 - ma)
                    g = 238.0 * ma + g * (1.0 - ma)
                    b = 242.0 * ma + b * (1.0 - ma)
            # ---- water: ripples + reflections ----
            if wt:
                rip = 1.0 + 0.07 * SIN(y * 0.5 + 2.0 * SIN(x * 0.02))
                r *= rip
                g *= rip
                b *= rip
                # moon reflection column (vertical wavy streaks)
                wcol = 1.0 - abs(x - 565) / 75.0
                if wcol > 0.0:
                    shim = 0.5 + 0.5 * SIN(x * 0.5 + SIN(y * 0.05) * 1.2)
                    k = wcol * shim * 0.55
                    r += 255.0 * k
                    g += 196.0 * k
                    b += 90.0 * k
                # koi reflection smear
                if 340 < x < 520:
                    w2 = 1.0 - abs(x - 430) / 90.0
                    k = w2 * (1.0 - (y - WATER_Y) / 200.0) * 0.4
                    k *= 0.6 + 0.4 * SIN(x * 0.2 + y * 0.09)
                    r += 200.0 * k
                    g += 110.0 * k
                    b += 40.0 * k
            # ---- golden motion arc behind the koi ----
            if 240 < x < 620 and y < 620:
                adx = x - 430
                ady = y - 640
                ad2 = adx * adx + ady * ady
                if 59049 < ad2 < 66049 or 71684 < ad2 < 77841:
                    ad = SQRT(ad2)
                    if abs(ad - 250.0) < 7.0:
                        a = 0.26
                        r = 255.0 * a + r * (1.0 - a)
                        g = 198.0 * a + g * (1.0 - a)
                        b = 92.0 * a + b * (1.0 - a)
                    elif abs(ad - 272.0) < 5.0:
                        a = 0.14
                        r = 255.0 * a + r * (1.0 - a)
                        g = 198.0 * a + g * (1.0 - a)
                        b = 92.0 * a + b * (1.0 - a)
            # ---- koi tail fin ----
            dx2 = x - tx
            dy2 = y - ty
            u2 = dx2 * ct + dy2 * st
            v2 = -dx2 * st + dy2 * ct
            e2 = (u2 / 88.0) ** 2 + (v2 / 30.0) ** 2
            e2 *= 1.0 + 0.10 * SIN(u2 * 0.22)
            if e2 < 1.0:
                a = 0.92
                tr, tg, tb = 238.0, 142.0, 50.0
                if e2 > 0.8:
                    k = (e2 - 0.8) / 0.2 * 0.5
                    tr = tr * (1.0 - k) + 150.0 * k
                    tg = tg * (1.0 - k) + 70.0 * k
                    tb = tb * (1.0 - k) + 20.0 * k
                r = tr * a + r * (1.0 - a)
                g = tg * a + g * (1.0 - a)
                b = tb * a + b * (1.0 - a)
            # ---- koi dorsal + pectoral fins ----
            # dorsal (u=0, v=-62) -> screen (394, 349)
            ddx = x - 394
            ddy = y - 349
            uu = ddx * c + ddy * s
            vv = -ddx * s + ddy * c
            ef = (uu / 72.0) ** 2 + (vv / 15.0) ** 2
            if ef < 1.0:
                a = 0.85
                r = 222.0 * a + r * (1.0 - a)
                g = 112.0 * a + g * (1.0 - a)
                b = 34.0 * a + b * (1.0 - a)
            # pectoral (u=60, v=55) -> screen (511, 411), angled +0.7
            cf = COS(th + 0.7)
            sf = SIN(th + 0.7)
            ddx = x - 511
            ddy = y - 411
            uu = ddx * cf + ddy * sf
            vv = -ddx * sf + ddy * cf
            ef = (uu / 46.0) ** 2 + (vv / 13.0) ** 2
            if ef < 1.0:
                a = 0.85
                r = 242.0 * a + r * (1.0 - a)
                g = 152.0 * a + g * (1.0 - a)
                b = 62.0 * a + b * (1.0 - a)
            # ---- koi body ----
            dx = x - 430
            dy = y - 400
            u = dx * c + dy * s
            v = -dx * s + dy * c
            e = (u / 150.0) ** 2 + (v / 58.0) ** 2
            if e < 1.0:
                t = (u + 150.0) / 300.0
                br = 228.0 + (255.0 - 228.0) * t
                bg = 116.0 + (214.0 - 116.0) * t
                bb = 36.0 + (108.0 - 36.0) * t
                if v > 18.0:  # pale belly
                    k = min(1.0, (v - 18.0) / 40.0) * 0.75
                    br = br * (1.0 - k) + 255.0 * k
                    bg = bg * (1.0 - k) + 242.0 * k
                    bb = bb * (1.0 - k) + 205.0 * k
                if v < -22.0:  # darker back
                    k = min(1.0, (-v - 22.0) / 36.0) * 0.55
                    br = br * (1.0 - k) + 190.0 * k
                    bg = bg * (1.0 - k) + 80.0 * k
                    bb = bb * (1.0 - k) + 22.0 * k
                sc = SIN(u * 0.24) * SIN(v * 0.42)
                m = 1.0 + 0.05 * sc
                br *= m
                bg *= m
                bb *= m
                if e > 0.86:  # rim
                    k = (e - 0.86) / 0.14 * 0.5
                    br = br * (1.0 - k) + 138.0 * k
                    bg = bg * (1.0 - k) + 58.0 * k
                    bb = bb * (1.0 - k) + 14.0 * k
                r, g, b = br, bg, bb
                # eye
                edx = x - ex
                edy = y - ey
                ed2 = edx * edx + edy * edy
                if ed2 < 81.0:
                    r, g, b = 20.0, 12.0, 8.0
                    if (x - (ex - 3)) ** 2 + (y - (ey - 3)) ** 2 < 9.0:
                        r, g, b = 255.0, 255.0, 255.0
            # ---- splash droplets ----
            if 200 < x < 470 and 430 < y < 580:
                for drx, dry, drr in DROPS:
                    ddx = x - drx
                    if ddx > drr or ddx < -drr:
                        continue
                    ddy = y - dry
                    if ddy > drr or ddy < -drr:
                        continue
                    d2 = ddx * ddx + ddy * ddy
                    if d2 < drr * drr:
                        a = 0.95
                        r = 228.0 * a + r * (1.0 - a)
                        g = 246.0 * a + g * (1.0 - a)
                        b = 252.0 * a + b * (1.0 - a)
                        if d2 < (drr * 0.4) ** 2:
                            r, g, b = 255.0, 255.0, 255.0
                        break
            # ---- fireflies (glow gated to a small radius) ----
            if 360 < y < 720:
                cx = x // 56
                cy = y // 56
                if h2(cx + 11, cy + 5) < 0.07:
                    fx = cx * 56 + int(h2(cx + 21, cy) * 44) + 6
                    fy = cy * 56 + int(h2(cx, cy + 31) * 44) + 6
                    ddx = x - fx
                    ddy = y - fy
                    d2f = ddx * ddx + ddy * ddy
                    if d2f < 900.0:
                        gl = 30.0 / (30.0 + d2f)
                        r += 255.0 * gl * 0.8
                        g += 200.0 * gl * 0.8
                        b += 90.0 * gl * 0.8
            # ---- vignette ----
            vx = x - 384
            vy = y - 384
            vg = 1.0 - 0.16 * min(1.0, (vx * vx + vy * vy) / 291600.0)
            i3 = 3 * x
            row[i3] = 0 if r < 0 else (255 if r > 255 else int(r))
            row[i3 + 1] = 0 if g < 0 else (255 if g > 255 else int(g))
            row[i3 + 2] = 0 if b < 0 else (255 if b > 255 else int(b))
            # apply vignette by scaling the stored bytes
            row[i3] = int(row[i3] * vg)
            row[i3 + 1] = int(row[i3 + 1] * vg)
            row[i3 + 2] = int(row[i3 + 2] * vg)
        rows.append(b"\x00" + bytes(row))
    return rows


def png_bytes(rows):
    raw = b"".join(rows)
    comp = zlib.compress(raw, 6)

    def chunk(tag, data):
        out = struct.pack(">I", len(data)) + tag + data
        return out + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", comp) + chunk(b"IEND", b""))


def main():
    outdir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(outdir, exist_ok=True)
    data = png_bytes(render())
    path = os.path.join(outdir, "entry.png")
    with open(path, "wb") as f:
        f.write(data)
    print(f"wrote {path} {len(data)} bytes {W}x{H}")


if __name__ == "__main__":
    main()
