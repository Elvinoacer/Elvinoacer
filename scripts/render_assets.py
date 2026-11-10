"""Generate the Unified Main Space Card (Raymarched Gargantua Black Hole + 60fps Einstein-Lensed Spacetime Grid + 6 Holographic Project Sub-Cards)."""

from __future__ import annotations

import base64
import math
import random
from io import BytesIO
from pathlib import Path

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"

GOLD = "#f59e0b"
BRIGHT_GOLD = "#fbbf24"
SOLAR = "#fef08a"
CYAN = "#22d3ee"
ICE = "#38bdf8"
EMERALD = "#10b981"
GREEN = "#34d399"


def rotate_3d(x: float, y: float, z: float, ax: float, ay: float, az: float) -> tuple[float, float, float]:
    cy, sy = math.cos(ax), math.sin(ax)
    y, z = y * cy - z * sy, y * sy + z * cy
    cx, sx = math.cos(ay), math.sin(ay)
    x, z = x * cx + z * sx, -x * sx + z * cx
    cz, sz = math.cos(az), math.sin(az)
    x, y = x * cz - y * sz, x * sz + y * cz
    return x, y, z


def project_3d(
    x: float, y: float, z: float,
    cx: float, cy: float,
    fov: float = 135.0, dist: float = 3.6,
) -> tuple[float, float, float]:
    scale = fov / max(0.5, dist - z)
    return cx + x * scale, cy + y * scale, z


def render_gargantua_backdrop_b64(width: int = 1200, height: int = 960, bh_cx: float = 600.0, bh_cy: float = 205.0) -> str:
    """Raymarch a 24-bit TrueColor relativistic Gargantua Black Hole & gravitational glow."""
    # Render at 1x resolution directly to lossless PNG for crisp TrueColor shader quality
    y, x = np.mgrid[0:height, 0:width].astype(np.float32)
    dx = (x - bh_cx) / 215.0
    dy = (y - bh_cy) / 215.0

    # Tilt black hole axis by -11 degrees
    tilt = np.deg2rad(11.0)
    tx = dx * np.cos(tilt) - dy * np.sin(tilt)
    ty = dx * np.sin(tilt) + dy * np.cos(tilt)

    r2 = tx * tx + ty * ty
    r = np.sqrt(r2 + 1e-6)

    r_eh = 0.34
    r_photon = 0.365
    r_einstein = 0.64

    disk_in = 0.37
    disk_out = 2.35

    r_disk_front = np.sqrt(tx * tx + (ty / 0.14) ** 2 + 1e-6)
    phi_front = np.arctan2(ty / 0.14, tx)

    r_disk_lensed = np.sqrt(tx * tx + (ty / 0.78) ** 2 + 1e-6)
    phi_lensed = np.arctan2(ty / 0.78, tx)

    def accretion_spiral(rd, phi, r_peak=0.80, w_spread=0.58):
        radial = np.exp(-((rd - r_peak) / w_spread) ** 2) * (rd > disk_in) * (rd < disk_out)
        radial *= np.clip((rd - disk_in) / 0.065, 0.0, 1.0)
        twist = phi + 8.8 / (rd + 0.22)
        s1 = 0.5 + 0.5 * np.sin(twist * 3.0 + np.cos(rd * 11.0))
        s2 = 0.5 + 0.5 * np.cos(twist * 6.0 - rd * 17.0)
        turb = 0.40 + 0.60 * (0.65 * s1 + 0.35 * s2)
        doppler = 1.0 - 0.46 * (tx / (rd + 0.24))
        return radial * turb * np.clip(doppler, 0.28, 1.80)

    front_mask = (ty > -0.015) | (r > r_eh)
    I_primary = accretion_spiral(r_disk_front, phi_front, 0.84, 0.62) * front_mask
    I_lensed = accretion_spiral(r_disk_lensed, phi_lensed, 0.62, 0.28) * (r > r_eh) * 0.90
    I_photon = 2.25 * np.exp(-((r - r_photon) / 0.015) ** 2)
    I_corona = 0.62 * np.exp(-((r - r_photon) / 0.20) ** 2) * (r > r_eh)

    I_total = I_primary + I_lensed + I_photon + I_corona
    I_total = np.where((r < r_eh) & (ty < -0.01), 0.0, I_total)

    # Deep space gradient base
    R = np.full((height, width), 2.0, dtype=np.float32)
    G = np.full((height, width), 5.0, dtype=np.float32)
    B = np.full((height, width), 12.0, dtype=np.float32)

    # Subtle Einstein ring atmospheric glow + lensed background starfield
    e_glow = np.exp(-((r - r_einstein) / 0.32) ** 2) * (r > r_eh)
    deflect = 1.0 - (r_einstein ** 2) / (r2 + 0.04)
    bx = dx * deflect
    by = dy * deflect
    inner_fade = np.clip((r - r_einstein * 0.75) / 0.22, 0.0, 1.0) ** 2
    sx_cell = np.floor(bx * 18.0)
    sy_cell = np.floor(by * 18.0)
    fx = (bx * 18.0) - sx_cell - 0.5
    fy = (by * 18.0) - sy_cell - 0.5
    star_hash = np.sin(sx_cell * 127.1 + sy_cell * 311.7) * 43758.5453
    star_prob = star_hash - np.floor(star_hash)
    stars = (star_prob > 0.945) * np.exp(-(fx * fx + fy * fy) / 0.012) * inner_fade * 0.85

    R += e_glow * 18.0 + stars * 215.0
    G += e_glow * 48.0 + stars * 238.0
    B += e_glow * 82.0 + stars * 255.0

    # Doppler relativistic plasma color mapping (Blue-White-Gold on left, Solar Gold-Amber on right)
    blue_shift = np.clip(-tx * 0.55 + 0.28, 0.0, 1.0)
    R += I_total * (255.0 * (1.0 - 0.10 * blue_shift))
    G += I_total * (168.0 + 75.0 * blue_shift + 48.0 * np.clip(I_total - 0.75, 0.0, 1.0))
    B += I_total * (52.0 + 195.0 * blue_shift + 98.0 * np.clip(I_total - 0.95, 0.0, 1.0))

    # Pure pitch-black Event Horizon shadow
    in_shadow = (r < r_eh) & ((ty < 0.0) | (I_primary < 0.08))
    R = np.where(in_shadow, 1.0, R)
    G = np.where(in_shadow, 2.0, G)
    B = np.where(in_shadow, 5.0, B)

    rgb_arr = np.stack([np.clip(R, 0, 255), np.clip(G, 0, 255), np.clip(B, 0, 255)], axis=-1).astype(np.uint8)
    img = Image.fromarray(rgb_arr)
    buf = BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def einstein_lensed_point(bx: float, by: float, bh_cx: float, bh_cy: float, scale: float, r_einstein: float, branch: int = 1) -> tuple[float, float]:
    """Map an un-lensed background coordinate (bx, by) to its exact Einstein-lensed screen position."""
    b = math.sqrt(bx * bx + by * by + 1e-5)
    if branch > 0:
        r_lensed = 0.5 * (b + math.sqrt(b * b + 4.0 * r_einstein * r_einstein))
    else:
        r_lensed = 0.5 * (b - math.sqrt(b * b + 4.0 * r_einstein * r_einstein))
    factor = r_lensed / b
    sx = bh_cx + bx * factor * scale
    sy = bh_cy + by * factor * scale
    return sx, sy


def generate_einstein_spacetime_grid_svg(bh_cx: float = 600.0, bh_cy: float = 205.0) -> str:
    """Generate 60fps animated SVG paths of a 3D spacetime grid continuously warping around the Black Hole."""
    scale = 215.0
    r_einstein = 0.64
    spacing = 0.24
    keyframes = 18

    # Animate grid lines shifting by 1 full grid period (`spacing`) so the loop is 100% seamless!
    v_line_indices = range(-12, 13)
    h_line_indices = range(-5, 15)

    animated_paths = []

    # Vertical spacetime grid lines moving horizontally across the Black Hole gravitational field
    for idx in v_line_indices:
        d_frames = []
        for f in range(keyframes + 1):
            phase = (f % keyframes) / keyframes
            bx = (idx + phase) * spacing
            pts = []
            steps = 34
            for s in range(steps + 1):
                by = -1.25 + (s / steps) * 4.65
                sx, sy = einstein_lensed_point(bx, by, bh_cx, bh_cy, scale, r_einstein, branch=1)
                pts.append(f"{'M' if s == 0 else 'L'}{sx:.1f},{sy:.1f}")
            d_frames.append("".join(pts))
        op = 0.34 if abs(idx) <= 4 else 0.18
        col = "#38bdf8" if abs(idx) <= 3 else "#0284c7"
        animated_paths.append(
            f'<path fill="none" stroke="{col}" stroke-opacity="{op}" stroke-width="1.05">'
            f'<animate attributeName="d" values="{";".join(d_frames)}" dur="4.5s" repeatCount="indefinite"/>'
            f'</path>'
        )

    # Horizontal spacetime grid lines moving vertically through the Black Hole gravitational field
    for idx in h_line_indices:
        d_frames = []
        for f in range(keyframes + 1):
            phase = (f % keyframes) / keyframes
            by = (idx - phase) * spacing
            pts = []
            steps = 44
            for s in range(steps + 1):
                bx = -2.85 + (s / steps) * 5.70
                sx, sy = einstein_lensed_point(bx, by, bh_cx, bh_cy, scale, r_einstein, branch=1)
                pts.append(f"{'M' if s == 0 else 'L'}{sx:.1f},{sy:.1f}")
            d_frames.append("".join(pts))
        op = 0.34 if abs(idx) <= 3 else 0.16
        col = "#22d3ee" if abs(idx) <= 2 else "#0369a1"
        animated_paths.append(
            f'<path fill="none" stroke="{col}" stroke-opacity="{op}" stroke-width="1.05">'
            f'<animate attributeName="d" values="{";".join(d_frames)}" dur="4.5s" repeatCount="indefinite"/>'
            f'</path>'
        )

    return "\n  ".join(animated_paths)


def make_3d_wireframe_keyframes(kind: str, cx: float, cy: float, keyframes: int = 24) -> list[str]:
    paths: list[str] = []
    for f in range(keyframes + 1):
        angle = (f % keyframes) / keyframes * 2.0 * math.pi
        segs: list[str] = []

        if kind == "helix":
            n = 12
            strand1, strand2 = [], []
            for i in range(n):
                t = (i / (n - 1)) * 2.0 - 1.0
                theta = t * math.pi * 1.3 + angle
                x1, y1, z1 = rotate_3d(0.72 * math.cos(theta), t * 1.05, 0.72 * math.sin(theta), 0.25, 0.0, 0.2)
                x2, y2, z2 = rotate_3d(-0.72 * math.cos(theta), t * 1.05, -0.72 * math.sin(theta), 0.25, 0.0, 0.2)
                p1 = project_3d(x1, y1, z1, cx, cy, fov=95.0, dist=3.6)
                p2 = project_3d(x2, y2, z2, cx, cy, fov=95.0, dist=3.6)
                strand1.append(p1)
                strand2.append(p2)
                if i % 2 == 0:
                    segs.append(f"M{p1[0]:.1f},{p1[1]:.1f}L{p2[0]:.1f},{p2[1]:.1f}")
            for i in range(n - 1):
                segs.append(f"M{strand1[i][0]:.1f},{strand1[i][1]:.1f}L{strand1[i+1][0]:.1f},{strand1[i+1][1]:.1f}")
                segs.append(f"M{strand2[i][0]:.1f},{strand2[i][1]:.1f}L{strand2[i+1][0]:.1f},{strand2[i+1][1]:.1f}")

        elif kind == "sphere":
            for ring in range(3):
                pts = []
                for k in range(18):
                    th = (k / 18) * 2.0 * math.pi
                    if ring == 0:
                        vx, vy, vz = math.cos(th), math.sin(th), 0.0
                    elif ring == 1:
                        vx, vy, vz = math.cos(th), 0.0, math.sin(th)
                    else:
                        vx, vy, vz = 0.0, math.cos(th), math.sin(th)
                    rx, ry, rz = rotate_3d(vx, vy, vz, 0.5 + angle * 0.5, angle, 0.3)
                    px, py, _ = project_3d(rx, ry, rz, cx, cy, fov=95.0, dist=3.5)
                    pts.append(f"{'M' if k == 0 else 'L'}{px:.1f},{py:.1f}")
                pts.append("Z")
                segs.append("".join(pts))

        elif kind == "tesseract":
            verts = []
            for s in (0.92, 0.46):
                for dx in (-s, s):
                    for dy in (-s, s):
                        for dz in (-s, s):
                            rx, ry, rz = rotate_3d(dx, dy, dz, 0.55, angle, angle * 0.5)
                            verts.append(project_3d(rx, ry, rz, cx, cy, fov=90.0, dist=3.8))
            cube_edges = [
                (0, 1), (1, 3), (3, 2), (2, 0),
                (4, 5), (5, 7), (7, 6), (6, 4),
                (0, 4), (1, 5), (2, 6), (3, 7),
            ]
            for base in (0, 8):
                for u, v in cube_edges:
                    p1, p2 = verts[base + u], verts[base + v]
                    segs.append(f"M{p1[0]:.1f},{p1[1]:.1f}L{p2[0]:.1f},{p2[1]:.1f}")
            for i in range(8):
                p1, p2 = verts[i], verts[i + 8]
                segs.append(f"M{p1[0]:.1f},{p1[1]:.1f}L{p2[0]:.1f},{p2[1]:.1f}")

        elif kind == "gyro":
            for r_scale, ax_m, ay_m in ((1.02, 1.0, 1.0), (0.76, -1.0, 1.5), (0.50, 1.5, -1.0)):
                pts = []
                for k in range(20):
                    th = (k / 20) * 2.0 * math.pi
                    rx, ry, rz = rotate_3d(r_scale * math.cos(th), r_scale * math.sin(th), 0.0, angle * ax_m + 0.6, angle * ay_m, 0.4)
                    px, py, _ = project_3d(rx, ry, rz, cx, cy, fov=95.0, dist=3.5)
                    pts.append(f"{'M' if k == 0 else 'L'}{px:.1f},{py:.1f}")
                pts.append("Z")
                segs.append("".join(pts))

        elif kind == "tower":
            raw_v = [
                (-0.8, 0.9, -0.8), (0.8, 0.9, -0.8), (0.8, 0.9, 0.8), (-0.8, 0.9, 0.8),
                (-0.55, -0.2, -0.55), (0.55, -0.2, -0.55), (0.55, -0.2, 0.55), (-0.55, -0.2, 0.55),
                (0.0, -1.1, 0.0),
            ]
            pverts = [
                project_3d(*rotate_3d(vx, vy, vz, 0.38, angle, 0.0), cx, cy, fov=95.0, dist=3.6)
                for vx, vy, vz in raw_v
            ]
            edges = [
                (0, 1), (1, 2), (2, 3), (3, 0),
                (4, 5), (5, 6), (6, 7), (7, 4),
                (0, 4), (1, 5), (2, 6), (3, 7),
                (4, 8), (5, 8), (6, 8), (7, 8),
            ]
            for u, v in edges:
                segs.append(f"M{pverts[u][0]:.1f},{pverts[u][1]:.1f}L{pverts[v][0]:.1f},{pverts[v][1]:.1f}")

        else:
            raw_v = [(0.0, -1.1, 0.0), (0.0, 1.1, 0.0)]
            for k in range(6):
                th = (k / 6) * 2.0 * math.pi
                raw_v.append((0.95 * math.cos(th), 0.0, 0.95 * math.sin(th)))
            pverts = [
                project_3d(*rotate_3d(vx, vy, vz, 0.45, angle, 0.25), cx, cy, fov=95.0, dist=3.6)
                for vx, vy, vz in raw_v
            ]
            for k in range(6):
                curr_i = 2 + k
                next_i = 2 + ((k + 1) % 6)
                segs.append(f"M{pverts[curr_i][0]:.1f},{pverts[curr_i][1]:.1f}L{pverts[next_i][0]:.1f},{pverts[next_i][1]:.1f}")
                segs.append(f"M{pverts[0][0]:.1f},{pverts[0][1]:.1f}L{pverts[curr_i][0]:.1f},{pverts[curr_i][1]:.1f}")
                segs.append(f"M{pverts[1][0]:.1f},{pverts[1][1]:.1f}L{pverts[curr_i][0]:.1f},{pverts[curr_i][1]:.1f}")

        paths.append("".join(segs))
    return paths


def generate_unified_main_card_svg() -> None:
    width, height = 1200, 960
    bh_cx, bh_cy = 600.0, 200.0

    b64_backdrop = render_gargantua_backdrop_b64(width, height, bh_cx, bh_cy)
    lensed_grid_svg = generate_einstein_spacetime_grid_svg(bh_cx, bh_cy)

    # 6 Sub-Cards Docked Inside the Bottom Half of the Main Card (3x2 grid)
    subcards_spec = [
        (
            "01 // HEALTHCARE OS",
            "AFYVIA · PHARMACARE",
            [("57", "MODELS"), ("308", "ROUTES"), ("4", "PORTALS")],
            "NEXT.JS 16 · PRISMA · GROQ AI · M-PESA",
            "#10b981",
            "helix",
        ),
        (
            "02 // GIG MARKETPLACE",
            "JUSTINTIME",
            [("22MB", "CORE"), ("4", "ROLES"), ("LIVE", "SOCKETS")],
            "NEXT.JS · SOCKET.IO · PRISMA · M-PESA",
            "#22d3ee",
            "sphere",
        ),
        (
            "03 // OFFLINE-FIRST POS",
            "RESTAURANT POS",
            [("39", "SCREENS"), ("5", "ROLES"), ("0ms", "CLOUD DEP.")],
            "ELECTRON · NODE.JS · SOCKET.IO · LAN",
            "#f59e0b",
            "tesseract",
        ),
        (
            "04 // CAMPUS ECOSYSTEM",
            "KAMPUS &amp; MASHINANI",
            [("18MB+", "SUITE"), ("EXPO", "iOS/AND"), ("P2P", "MARKET")],
            "REACT NATIVE · EXPO · NEXT.JS · PGSQL",
            "#38bdf8",
            "gyro",
        ),
        (
            "05 // ARCHITECTURAL CAD",
            "CONCEPT BUILDERS",
            [("35MB", "PLATFORM"), ("3D", "PLANS"), ("LIVE", "SOCKETS")],
            "NEXT.JS · TYPESCRIPT · SOCKET.IO",
            "#fbbf24",
            "tower",
        ),
        (
            "06 // LIVE EDTECH OS",
            "GERMAN SCHOOL",
            [("A1–C2", "6 TIERS"), ("LIVE", "SYNC"), ("3", "PORTALS")],
            "NEXT.JS · SOCKET.IO · PRISMA · WEBRTC",
            "#34d399",
            "crystal",
        ),
    ]

    subcards_svg = []
    for idx, (badge, title, metrics, stack_line, accent, shape_kind) in enumerate(subcards_spec):
        col = idx % 3
        row = idx // 3
        cw, ch = 364, 188
        cx_card = 36 + col * 382
        cy_card = 532 + row * 204

        holo_x = cx_card + cw - 56
        holo_y = cy_card + 56
        wire_paths = make_3d_wireframe_keyframes(shape_kind, holo_x, holo_y)

        m_blocks = []
        for m_i, (m_val, m_lbl) in enumerate(metrics):
            mx = cx_card + 18 + m_i * 108
            my = cy_card + 92
            m_blocks.append(
                f'<rect x="{mx}" y="{my}" width="100" height="52" rx="8" fill="#050c18" fill-opacity="0.88" stroke="{accent}" stroke-opacity="0.38"/>'
                f'<text x="{mx + 50}" y="{my + 26}" text-anchor="middle" fill="{accent}" font-family="ui-monospace,SFMono-Regular,JetBrains Mono,monospace" font-size="18" font-weight="900">{m_val}</text>'
                f'<text x="{mx + 50}" y="{my + 43}" text-anchor="middle" fill="#94a3b8" font-family="ui-monospace,SFMono-Regular,monospace" font-size="8" font-weight="700" letter-spacing="0.8">{m_lbl}</text>'
            )

        subcards_svg.append(f'''
  <g>
    <rect x="{cx_card}" y="{cy_card}" width="{cw}" height="{ch}" rx="14" fill="#060d1b" fill-opacity="0.80" stroke="{accent}" stroke-opacity="0.45" stroke-width="1.2"/>
    <path d="M {cx_card + 20} {cy_card + 1} H {cx_card + 165}" stroke="{accent}" stroke-width="2.2"/>
    <circle cx="{cx_card + 24}" cy="{cy_card + 24}" r="3.5" fill="{accent}"/>
    <text x="{cx_card + 35}" y="{cy_card + 28}" fill="{accent}" font-family="ui-monospace,SFMono-Regular,monospace" font-size="10" font-weight="800" letter-spacing="1.2">{badge}</text>
    <text x="{cx_card + 18}" y="{cy_card + 62}" fill="#ffffff" font-family="Inter,ui-sans-serif,system-ui,sans-serif" font-size="20" font-weight="900" letter-spacing="-0.4">{title}</text>
    <circle cx="{holo_x}" cy="{holo_y}" r="38" fill="none" stroke="{accent}" stroke-opacity="0.18" stroke-dasharray="4 6"/>
    <path fill="none" stroke="{accent}" stroke-width="1.35" stroke-linejoin="round">
      <animate attributeName="d" values="{";".join(wire_paths)}" dur="8s" repeatCount="indefinite"/>
    </path>
    {"".join(m_blocks)}
    <text x="{cx_card + 18}" y="{cy_card + 168}" fill="#64748b" font-family="ui-monospace,SFMono-Regular,monospace" font-size="9.5" font-weight="700" letter-spacing="0.8">{stack_line}</text>
  </g>''')

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="Elvin Omondi Juma — Relativistic Black Hole &amp; Unified Space Command Deck">
<defs>
  <clipPath id="cardClip">
    <rect width="{width}" height="{height}" rx="24"/>
  </clipPath>
  <radialGradient id="gridFadeGrad" cx="{bh_cx}" cy="{bh_cy}" r="185" gradientUnits="userSpaceOnUse">
    <stop offset="0%" stop-color="#000000"/>
    <stop offset="52%" stop-color="#000000"/>
    <stop offset="78%" stop-color="#ffffff"/>
    <stop offset="100%" stop-color="#ffffff"/>
  </radialGradient>
  <mask id="gridMask">
    <rect width="{width}" height="{height}" fill="url(#gridFadeGrad)"/>
  </mask>
  <filter id="softGlow" x="-20%" y="-20%" width="140%" height="140%">
    <feGaussianBlur stdDeviation="3" result="b"/>
    <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
  <filter id="textShadow" x="-20%" y="-20%" width="140%" height="140%">
    <feDropShadow dx="0" dy="2" stdDeviation="6" flood-color="#000000" flood-opacity="0.95"/>
  </filter>
</defs>

<g clip-path="url(#cardClip)">
  <!-- 1. 24-Bit TrueColor Raymarched Gargantua Black Hole & Relativistic Plasma Backdrop -->
  <image href="data:image/png;base64,{b64_backdrop}" width="{width}" height="{height}"/>

  <!-- 2. 60fps Animated Einstein-Lensed 3D Spacetime Grid Bending Around the Black Hole -->
  <g mask="url(#gridMask)">
    {lensed_grid_svg}
  </g>

  <!-- 3. Animated Relativistic Accretion Streams Swirling Across Front of Accretion Disk -->
  <g transform="translate({bh_cx}, {bh_cy}) rotate(-11)">
    <path d="M -290 0 A 290 42 0 0 0 290 0" fill="none" stroke="#fef08a" stroke-width="2.2" stroke-opacity="0.85" stroke-dasharray="55 110" filter="url(#softGlow)">
      <animate attributeName="stroke-dashoffset" values="0;-330" dur="2.1s" repeatCount="indefinite"/>
    </path>
    <path d="M -225 0 A 225 32 0 0 0 225 0" fill="none" stroke="#ffffff" stroke-width="1.8" stroke-opacity="0.9" stroke-dasharray="40 90" filter="url(#softGlow)">
      <animate attributeName="stroke-dashoffset" values="0;-260" dur="1.6s" repeatCount="indefinite"/>
    </path>
    <path d="M -345 0 A 345 50 0 0 0 345 0" fill="none" stroke="#38bdf8" stroke-width="1.5" stroke-opacity="0.75" stroke-dasharray="35 130" filter="url(#softGlow)">
      <animate attributeName="stroke-dashoffset" values="0;-330" dur="2.9s" repeatCount="indefinite"/>
    </path>
  </g>

  <!-- 4. HERO IDENTITY & CORE METRICS IN THE GRAVITATIONAL FIELD -->
  <g transform="translate(415, 20)">
    <rect width="370" height="28" rx="14" fill="#040a16" fill-opacity="0.82" stroke="#22d3ee" stroke-opacity="0.45"/>
    <circle cx="18" cy="14" r="4" fill="#10b981" filter="url(#softGlow)">
      <animate attributeName="opacity" values="1;0.2;1" dur="1.4s" repeatCount="indefinite"/>
    </circle>
    <text x="32" y="18" fill="#bae6fd" font-family="ui-monospace,SFMono-Regular,JetBrains Mono,monospace" font-size="10.5" font-weight="800" letter-spacing="1.6">FOUNDING ENGINEER @ GTSS  ·  KENYA</text>
  </g>

  <g font-family="Inter,ui-sans-serif,system-ui,-apple-system,Segoe UI,sans-serif" text-anchor="middle" filter="url(#textShadow)">
    <text x="600" y="362" fill="#ffffff" font-size="46" font-weight="900" letter-spacing="3.5">ELVIN OMONDI JUMA</text>
    <text x="600" y="388" fill="#fbbf24" font-family="ui-monospace,SFMono-Regular,monospace" font-size="12.5" font-weight="800" letter-spacing="3.4">
      PULLING COMPLEXITY INTO RELIABLE SYSTEMS
    </text>
  </g>

  <!-- 4 Translucent Telemetry Pods -->
  <g transform="translate(36, 408)" font-family="ui-monospace,SFMono-Regular,JetBrains Mono,monospace">
    <g transform="translate(0, 0)">
      <rect width="268" height="72" rx="12" fill="#050c1a" fill-opacity="0.84" stroke="#f59e0b" stroke-opacity="0.48"/>
      <text x="134" y="34" text-anchor="middle" fill="#fbbf24" font-size="26" font-weight="900">5,107+</text>
      <text x="134" y="54" text-anchor="middle" fill="#cbd5e1" font-size="10" font-weight="700" letter-spacing="1.4">COMMITS (+310% YoY)</text>
    </g>
    <g transform="translate(286, 0)">
      <rect width="268" height="72" rx="12" fill="#050c1a" fill-opacity="0.84" stroke="#22d3ee" stroke-opacity="0.48"/>
      <text x="134" y="34" text-anchor="middle" fill="#22d3ee" font-size="26" font-weight="900">117 / 124</text>
      <text x="134" y="54" text-anchor="middle" fill="#cbd5e1" font-size="10" font-weight="700" letter-spacing="1.4">PUBLIC REPOSITORIES</text>
    </g>
    <g transform="translate(572, 0)">
      <rect width="268" height="72" rx="12" fill="#050c1a" fill-opacity="0.84" stroke="#10b981" stroke-opacity="0.48"/>
      <text x="134" y="34" text-anchor="middle" fill="#34d399" font-size="26" font-weight="900">6 LIVE</text>
      <text x="134" y="54" text-anchor="middle" fill="#cbd5e1" font-size="10" font-weight="700" letter-spacing="1.4">SAAS ECOSYSTEMS</text>
    </g>
    <g transform="translate(858, 0)">
      <rect width="270" height="72" rx="12" fill="#050c1a" fill-opacity="0.84" stroke="#38bdf8" stroke-opacity="0.48"/>
      <text x="135" y="34" text-anchor="middle" fill="#38bdf8" font-size="26" font-weight="900">99.98%</text>
      <text x="135" y="54" text-anchor="middle" fill="#cbd5e1" font-size="10" font-weight="700" letter-spacing="1.4">UPTIME · 0ms LAN POS</text>
    </g>
  </g>

  <!-- Divider Header for Sub-Cards Inside Main Card -->
  <line x1="36" y1="504" x2="1164" y2="504" stroke="#1e293b" stroke-width="1.2"/>
  <text x="600" y="519" text-anchor="middle" fill="#94a3b8" font-family="ui-monospace,SFMono-Regular,monospace" font-size="10" font-weight="800" letter-spacing="2.6">
    FLAGSHIP PRODUCTION SYSTEMS IN ORBIT
  </text>

  <!-- 5. 6 FEATURED PROJECT SUB-CARDS DOCKED INSIDE THE MAIN CARD -->
  {"".join(subcards_svg)}
</g>

<!-- Outer Master Card Rim -->
<rect x="1" y="1" width="{width - 2}" height="{height - 2}" rx="23" fill="none" stroke="#38bdf8" stroke-opacity="0.35" stroke-width="1.5"/>
</svg>
'''
    (ASSETS / "hero-3d.svg").write_text(svg, encoding="utf-8")
    print("hero-3d.svg (Unified Main Card with Raymarched Gargantua + 6 Sub-Cards) generated.")


def starfield_svg(width: int, height: int, count: int = 85, seed: int = 909) -> str:
    rng = random.Random(seed)
    items = []
    palette = ["#ffffff", "#bae6fd", "#fef08a", "#67e8f9", "#a7f3d0"]
    for i in range(count):
        x = rng.uniform(12, width - 12)
        y = rng.uniform(12, height - 12)
        r = rng.choice([0.6, 0.8, 1.0, 1.3, 1.6])
        op = rng.uniform(0.25, 0.85)
        col = rng.choice(palette)
        if i % 7 == 0:
            dur = rng.uniform(2.2, 5.0)
            items.append(
                f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{col}" opacity="{op:.2f}">'
                f'<animate attributeName="opacity" values="{op:.2f};0.12;{op:.2f}" dur="{dur:.1f}s" repeatCount="indefinite"/>'
                f'</circle>'
            )
        else:
            items.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{col}" opacity="{op:.2f}"/>')
    return "\n  ".join(items)


def generate_space_orbit_svg() -> None:
    width, height = 1200, 320
    cx, cy = 600, 165
    stars = starfield_svg(width, height, count=85, seed=909)

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="3D Orbital Engineering Stack">
<defs>
  <radialGradient id="sBg" cx="0.5" cy="0.52" r="0.65">
    <stop offset="0%" stop-color="#0b192e"/>
    <stop offset="55%" stop-color="#050a15"/>
    <stop offset="100%" stop-color="#02040a"/>
  </radialGradient>
  <filter id="sGlow" x="-30%" y="-30%" width="160%" height="160%">
    <feGaussianBlur stdDeviation="4" result="b"/>
    <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
</defs>

<rect width="{width}" height="{height}" rx="20" fill="url(#sBg)" stroke="#16243d" stroke-width="1.5"/>
<g>{stars}</g>

<!-- 3 Tilted 3D Orbital Tracks -->
<g fill="none">
  <path id="orbitInner" d="M 410 165 A 190 48 0 1 0 790 165 A 190 48 0 1 0 410 165" stroke="#f59e0b" stroke-opacity="0.25" stroke-width="1.2" stroke-dasharray="6 8"/>
  <path id="orbitMid" d="M 280 165 A 320 78 0 1 1 920 165 A 320 78 0 1 1 280 165" stroke="#22d3ee" stroke-opacity="0.22" stroke-width="1.2" stroke-dasharray="8 10"/>
  <path id="orbitOuter" d="M 150 165 A 450 108 0 1 0 1050 165 A 450 108 0 1 0 150 165" stroke="#10b981" stroke-opacity="0.20" stroke-width="1.2" stroke-dasharray="10 12"/>
</g>

<!-- Central Gravity Star -->
<g transform="translate({cx}, {cy})">
  <circle r="44" fill="#071426" stroke="#fbbf24" stroke-width="2.2" filter="url(#sGlow)"/>
  <circle r="52" fill="none" stroke="#22d3ee" stroke-opacity="0.4" stroke-dasharray="4 8"/>
  <text y="-3" text-anchor="middle" fill="#ffffff" font-family="ui-monospace,SFMono-Regular,monospace" font-size="13" font-weight="900">92% TS</text>
  <text y="14" text-anchor="middle" fill="#fbbf24" font-family="ui-monospace,SFMono-Regular,monospace" font-size="9.5" font-weight="700">CORE ENGINE</text>
</g>

<!-- Orbiting Tech Satellites (Smooth 60fps Motion Along Elliptical Orbits) -->
<g font-family="ui-monospace,SFMono-Regular,JetBrains Mono,monospace" font-size="10.5" font-weight="800" text-anchor="middle">
  <g>
    <circle r="5.5" fill="#fbbf24" filter="url(#sGlow)"/>
    <text x="0" y="-12" fill="#fef08a">NEXT.JS 16 · REACT 19</text>
    <animateMotion dur="14s" repeatCount="indefinite"><mpath href="#orbitInner"/></animateMotion>
  </g>
  <g>
    <circle r="5.5" fill="#fbbf24" filter="url(#sGlow)"/>
    <text x="0" y="-12" fill="#fef08a">PRISMA · POSTGRESQL</text>
    <animateMotion dur="14s" begin="-7s" repeatCount="indefinite"><mpath href="#orbitInner"/></animateMotion>
  </g>
  <g>
    <circle r="5.5" fill="#22d3ee" filter="url(#sGlow)"/>
    <text x="0" y="-12" fill="#bae6fd">SOCKET.IO · OFFLINE LAN</text>
    <animateMotion dur="20s" repeatCount="indefinite"><mpath href="#orbitMid"/></animateMotion>
  </g>
  <g>
    <circle r="5.5" fill="#22d3ee" filter="url(#sGlow)"/>
    <text x="0" y="-12" fill="#bae6fd">M-PESA DARAJA · FINTECH</text>
    <animateMotion dur="20s" begin="-10s" repeatCount="indefinite"><mpath href="#orbitMid"/></animateMotion>
  </g>
  <g>
    <circle r="5.5" fill="#34d399" filter="url(#sGlow)"/>
    <text x="0" y="-12" fill="#a7f3d0">REACT NATIVE · EXPO · ELECTRON</text>
    <animateMotion dur="26s" repeatCount="indefinite"><mpath href="#orbitOuter"/></animateMotion>
  </g>
  <g>
    <circle r="5.5" fill="#34d399" filter="url(#sGlow)"/>
    <text x="0" y="-12" fill="#a7f3d0">GROQ AI · THREE.JS · LINUX VPS</text>
    <animateMotion dur="26s" begin="-13s" repeatCount="indefinite"><mpath href="#orbitOuter"/></animateMotion>
  </g>
</g>
</svg>
'''
    (ASSETS / "architecture-3d.svg").write_text(svg, encoding="utf-8")
    print("architecture-3d.svg generated.")


def generate_footer_svg() -> None:
    stars = starfield_svg(1200, 140, count=45, seed=333)
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="145" viewBox="0 0 1200 145" role="img" aria-label="Engineered in Kenya. Built for scale.">
<defs>
  <linearGradient id="fBg" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%" stop-color="#02040a"/>
    <stop offset="100%" stop-color="#071224"/>
  </linearGradient>
  <linearGradient id="planetRim" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0%" stop-color="#0284c7" stop-opacity="0"/>
    <stop offset="25%" stop-color="#22d3ee" stop-opacity="0.85"/>
    <stop offset="50%" stop-color="#fef08a" stop-opacity="1"/>
    <stop offset="75%" stop-color="#10b981" stop-opacity="0.85"/>
    <stop offset="100%" stop-color="#0284c7" stop-opacity="0"/>
  </linearGradient>
  <filter id="rimGlow" x="-20%" y="-40%" width="140%" height="180%">
    <feGaussianBlur stdDeviation="6" result="b"/>
    <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
</defs>

<rect width="1200" height="145" rx="20" fill="url(#fBg)" stroke="#16243d" stroke-width="1.5"/>
<g>{stars}</g>

<!-- Curved Planetary Limb Horizon -->
<path d="M -80 155 Q 600 45 1280 155 Z" fill="#030710"/>
<path d="M -80 155 Q 600 45 1280 155" fill="none" stroke="url(#planetRim)" stroke-width="3.5" filter="url(#rimGlow)"/>

<circle r="4" fill="#fef08a" filter="url(#rimGlow)">
  <animateMotion dur="8s" repeatCount="indefinite" path="M 80 132 Q 600 52 1120 132"/>
</circle>

<text x="600" y="54" text-anchor="middle" fill="#ffffff" font-family="Inter,ui-sans-serif,system-ui,sans-serif" font-size="20" font-weight="900" letter-spacing="3">
  ELVIN OMONDI JUMA  ·  <tspan fill="#22d3ee">GTSS</tspan>  ·  <tspan fill="#fbbf24">KENYA</tspan>
</text>
<text x="600" y="78" text-anchor="middle" fill="#94a3b8" font-family="ui-monospace,SFMono-Regular,monospace" font-size="11" font-weight="700" letter-spacing="2">
  omondielvin@gmail.com  //  elvin-juma-portfolio.vercel.app
</text>
</svg>
'''
    (ASSETS / "footer.svg").write_text(svg, encoding="utf-8")
    print("footer.svg generated.")


def main() -> None:
    ASSETS.mkdir(exist_ok=True)
    generate_unified_main_card_svg()
    generate_space_orbit_svg()
    generate_footer_svg()


if __name__ == "__main__":
    main()
