"""Generate the Central Gargantua Black Hole & Orbital Project Cards Suite with 100% seamless C-infinity periodic animations."""

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
    fov: float = 88.0, dist: float = 3.6,
) -> tuple[float, float, float]:
    scale = fov / max(0.5, dist - z)
    return cx + x * scale, cy + y * scale, z


def render_gargantua_center_b64(width: int = 1200, height: int = 880, bh_cx: float = 600.0, bh_cy: float = 435.0) -> str:
    """Raymarch a 24-bit TrueColor relativistic Gargantua Black Hole at the dead center of the Main Card."""
    y, x = np.mgrid[0:height, 0:width].astype(np.float32)
    dx = (x - bh_cx) / 185.0
    dy = (y - bh_cy) / 185.0

    # Tilt black hole axis by -12 degrees
    tilt = np.deg2rad(12.0)
    tx = dx * np.cos(tilt) - dy * np.sin(tilt)
    ty = dx * np.sin(tilt) + dy * np.cos(tilt)

    r2 = tx * tx + ty * ty
    r = np.sqrt(r2 + 1e-6)

    r_eh = 0.35
    r_photon = 0.375
    r_einstein = 0.66

    disk_in = 0.38
    disk_out = 2.35

    r_disk_front = np.sqrt(tx * tx + (ty / 0.145) ** 2 + 1e-6)
    phi_front = np.arctan2(ty / 0.145, tx)

    r_disk_lensed = np.sqrt(tx * tx + (ty / 0.80) ** 2 + 1e-6)
    phi_lensed = np.arctan2(ty / 0.80, tx)

    def accretion_spiral(rd, phi, r_peak=0.82, w_spread=0.58):
        radial = np.exp(-((rd - r_peak) / w_spread) ** 2) * (rd > disk_in) * (rd < disk_out)
        radial *= np.clip((rd - disk_in) / 0.065, 0.0, 1.0)
        twist = phi + 8.8 / (rd + 0.22)
        s1 = 0.5 + 0.5 * np.sin(twist * 3.0 + np.cos(rd * 11.0))
        s2 = 0.5 + 0.5 * np.cos(twist * 6.0 - rd * 17.0)
        turb = 0.42 + 0.58 * (0.65 * s1 + 0.35 * s2)
        doppler = 1.0 - 0.46 * (tx / (rd + 0.24))
        return radial * turb * np.clip(doppler, 0.28, 1.80)

    front_mask = (ty > -0.015) | (r > r_eh)
    I_primary = accretion_spiral(r_disk_front, phi_front, 0.84, 0.60) * front_mask
    I_lensed = accretion_spiral(r_disk_lensed, phi_lensed, 0.63, 0.29) * (r > r_eh) * 0.92
    I_photon = 2.3 * np.exp(-((r - r_photon) / 0.015) ** 2)
    I_corona = 0.65 * np.exp(-((r - r_photon) / 0.22) ** 2) * (r > r_eh)

    I_total = I_primary + I_lensed + I_photon + I_corona
    I_total = np.where((r < r_eh) & (ty < -0.01), 0.0, I_total)

    # Deep Cosmic Void Base
    R = np.full((height, width), 2.0, dtype=np.float32)
    G = np.full((height, width), 5.0, dtype=np.float32)
    B = np.full((height, width), 12.0, dtype=np.float32)

    # Gravitational lens halo + Einstein-lensed background starfield
    e_glow = np.exp(-((r - r_einstein) / 0.38) ** 2) * (r > r_eh)
    deflect = 1.0 - (r_einstein ** 2) / (r2 + 0.04)
    bx = dx * deflect
    by = dy * deflect
    inner_fade = np.clip((r - r_einstein * 0.72) / 0.22, 0.0, 1.0) ** 2
    sx_cell = np.floor(bx * 16.0)
    sy_cell = np.floor(by * 16.0)
    fx = (bx * 16.0) - sx_cell - 0.5
    fy = (by * 16.0) - sy_cell - 0.5
    star_hash = np.sin(sx_cell * 127.1 + sy_cell * 311.7) * 43758.5453
    star_prob = star_hash - np.floor(star_hash)
    stars = (star_prob > 0.942) * np.exp(-(fx * fx + fy * fy) / 0.012) * inner_fade * 0.88

    R += e_glow * 16.0 + stars * 215.0
    G += e_glow * 46.0 + stars * 238.0
    B += e_glow * 84.0 + stars * 255.0

    # Doppler relativistic plasma color mapping
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


def einstein_lensed_point(bx: float, by: float, bh_cx: float, bh_cy: float, scale: float, r_einstein: float) -> tuple[float, float]:
    """Map an un-lensed coordinate (bx, by) to its exact Einstein-lensed screen position."""
    b = math.sqrt(bx * bx + by * by + 1e-5)
    r_lensed = 0.5 * (b + math.sqrt(b * b + 4.0 * r_einstein * r_einstein))
    factor = r_lensed / b
    return bh_cx + bx * factor * scale, bh_cy + by * factor * scale


def generate_seamless_spacetime_grid_svg(bh_cx: float = 600.0, bh_cy: float = 435.0) -> str:
    """
    Generate an Einstein-lensed 3D spacetime grid that NEVER resets or jumps:
    1. Every grid geodesic sways with a pure C-infinity periodic sine/cosine wave (f / keyframes * 2*pi, so f=0 and f=N are 100% identical!).
    2. Continuous photonic energy pulses flow along the warped grid lines via exact-period stroke-dashoffset!
    """
    scale = 185.0
    r_einstein = 0.68
    spacing = 0.28
    keyframes = 20

    # Symmetric non-zero indices so no line ever sits on or crosses the b=0 singularity!
    v_indices = [-11, -10, -9, -8, -7, -6, -5, -4, -3, -2, -1.2, -0.55, 0.55, 1.2, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
    h_indices = [-8, -7, -6, -5, -4, -3, -2, -1.2, -0.55, 0.55, 1.2, 2, 3, 4, 5, 6, 7, 8]

    elements = []

    for idx in v_indices:
        d_frames = []
        for f in range(keyframes + 1):
            # Pure periodic angle theta in [0, 2*pi] -> f=0 and f=keyframes are 100.000% identical!
            theta = (f / keyframes) * 2.0 * math.pi
            pts = []
            steps = 36
            for s in range(steps + 1):
                by = -2.45 + (s / steps) * 4.90
                # Smooth gravitational tidal breathing wave along the geodesic
                tidal = 0.045 * math.sin(theta + by * 1.6 + idx * 0.4)
                r_e_breath = r_einstein + 0.035 * math.cos(theta)
                sx, sy = einstein_lensed_point(idx * spacing + tidal, by, bh_cx, bh_cy, scale, r_e_breath)
                pts.append(f"{'M' if s == 0 else 'L'}{sx:.1f},{py_clamp(sy):.1f}")
            d_frames.append("".join(pts))

        near = abs(idx) < 2.5
        col = "#38bdf8" if near else "#0284c7"
        op = 0.36 if near else 0.17
        d_joined = ";".join(d_frames)
        elements.append(
            f'<path d="{d_frames[0]}" fill="none" stroke="{col}" stroke-opacity="{op}" stroke-width="1.05">'
            f'<animate attributeName="d" values="{d_joined}" dur="6s" repeatCount="indefinite"/>'
            f'</path>'
        )
        # Add continuous zero-reset light pulse along the central warped geodesics
        if near:
            elements.append(
                f'<path d="{d_frames[0]}" fill="none" stroke="#fef08a" stroke-opacity="0.45" stroke-width="1.4" stroke-dasharray="40 200">'
                f'<animate attributeName="d" values="{d_joined}" dur="6s" repeatCount="indefinite"/>'
                f'<animate attributeName="stroke-dashoffset" from="240" to="0" dur="3s" repeatCount="indefinite"/>'
                f'</path>'
            )

    for idx in h_indices:
        d_frames = []
        for f in range(keyframes + 1):
            theta = (f / keyframes) * 2.0 * math.pi
            pts = []
            steps = 44
            for s in range(steps + 1):
                bx = -3.35 + (s / steps) * 6.70
                tidal = 0.045 * math.cos(theta + bx * 1.4 + idx * 0.4)
                r_e_breath = r_einstein + 0.035 * math.cos(theta)
                sx, sy = einstein_lensed_point(bx, idx * spacing + tidal, bh_cx, bh_cy, scale, r_e_breath)
                pts.append(f"{'M' if s == 0 else 'L'}{sx:.1f},{py_clamp(sy):.1f}")
            d_frames.append("".join(pts))

        near = abs(idx) < 2.5
        col = "#22d3ee" if near else "#0369a1"
        op = 0.34 if near else 0.15
        d_joined = ";".join(d_frames)
        elements.append(
            f'<path d="{d_frames[0]}" fill="none" stroke="{col}" stroke-opacity="{op}" stroke-width="1.05">'
            f'<animate attributeName="d" values="{d_joined}" dur="6s" repeatCount="indefinite"/>'
            f'</path>'
        )

    return "\n    ".join(elements)


def py_clamp(v: float) -> float:
    return max(-100.0, min(980.0, v))


def make_3d_wireframe_keyframes(kind: str, cx: float, cy: float, keyframes: int = 24) -> list[str]:
    """Generate 3D rotating wireframe keyframes where f=keyframes is at 2*pi (identical to f=0, zero reset!)."""
    paths: list[str] = []
    for f in range(keyframes + 1):
        # NOTE: NO modulo `% keyframes`! At f=keyframes, angle = 2*pi, so cos(2*pi)=cos(0) & sin(2*pi)=sin(0)!
        angle = (f / keyframes) * 2.0 * math.pi
        segs: list[str] = []

        if kind == "helix":
            n = 12
            strand1, strand2 = [], []
            for i in range(n):
                t = (i / (n - 1)) * 2.0 - 1.0
                theta = t * math.pi * 1.3 + angle
                x1, y1, z1 = rotate_3d(0.72 * math.cos(theta), t * 1.05, 0.72 * math.sin(theta), 0.25, 0.0, 0.2)
                x2, y2, z2 = rotate_3d(-0.72 * math.cos(theta), t * 1.05, -0.72 * math.sin(theta), 0.25, 0.0, 0.2)
                p1 = project_3d(x1, y1, z1, cx, cy, fov=84.0, dist=3.6)
                p2 = project_3d(x2, y2, z2, cx, cy, fov=84.0, dist=3.6)
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
                    rx, ry, rz = rotate_3d(vx, vy, vz, 0.5, angle, 0.3)
                    px, py, _ = project_3d(rx, ry, rz, cx, cy, fov=84.0, dist=3.5)
                    pts.append(f"{'M' if k == 0 else 'L'}{px:.1f},{py:.1f}")
                pts.append("Z")
                segs.append("".join(pts))

        elif kind == "tesseract":
            verts = []
            for s in (0.92, 0.46):
                for dx in (-s, s):
                    for dy in (-s, s):
                        for dz in (-s, s):
                            rx, ry, rz = rotate_3d(dx, dy, dz, 0.55, angle, angle)
                            verts.append(project_3d(rx, ry, rz, cx, cy, fov=80.0, dist=3.8))
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
            for r_scale, ax_m, ay_m in ((1.02, 1.0, 1.0), (0.76, -1.0, 1.0), (0.50, 1.0, -1.0)):
                pts = []
                for k in range(20):
                    th = (k / 20) * 2.0 * math.pi
                    rx, ry, rz = rotate_3d(r_scale * math.cos(th), r_scale * math.sin(th), 0.0, angle * ax_m + 0.6, angle * ay_m, 0.4)
                    px, py, _ = project_3d(rx, ry, rz, cx, cy, fov=84.0, dist=3.5)
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
                project_3d(*rotate_3d(vx, vy, vz, 0.38, angle, 0.0), cx, cy, fov=84.0, dist=3.6)
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
                project_3d(*rotate_3d(vx, vy, vz, 0.45, angle, 0.25), cx, cy, fov=84.0, dist=3.6)
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
    width, height = 1200, 880
    bh_cx, bh_cy = 600.0, 435.0

    b64_backdrop = render_gargantua_center_b64(width, height, bh_cx, bh_cy)
    lensed_grid_svg = generate_seamless_spacetime_grid_svg(bh_cx, bh_cy)

    # 6 Project Sub-Cards Orbiting Around the Central Black Hole (3 on Left Wing, 3 on Right Wing)
    # Left Wing: x=28..356 (width 328)
    # Right Wing: x=844..1172 (width 328)
    # Center (x=356..844) is wide open for the Gargantua Black Hole Singularity!
    subcards_spec = [
        # Left Wing (col=0)
        (
            28, 138,
            "01 // HEALTHCARE OS",
            "AFYVIA · PHARMACARE",
            [("57", "MODELS"), ("308", "ROUTES"), ("4", "PORTALS")],
            "NEXT.JS 16 · PRISMA · GROQ AI · M-PESA",
            "#10b981",
            "helix",
            (356, 224, 495, 390),
        ),
        (
            28, 348,
            "03 // OFFLINE-FIRST POS",
            "RESTAURANT POS",
            [("39", "SCREENS"), ("5", "ROLES"), ("0ms", "CLOUD")],
            "ELECTRON · NODE.JS · SOCKET.IO · LAN",
            "#f59e0b",
            "tesseract",
            (356, 434, 475, 435),
        ),
        (
            28, 558,
            "05 // ARCHITECTURAL CAD",
            "CONCEPT BUILDERS",
            [("35MB", "SUITE"), ("3D", "PLANS"), ("LIVE", "SOCKETS")],
            "NEXT.JS · TYPESCRIPT · SOCKET.IO",
            "#fbbf24",
            "tower",
            (356, 644, 495, 480),
        ),
        # Right Wing (col=1)
        (
            844, 138,
            "02 // GIG MARKETPLACE",
            "JUSTINTIME",
            [("22MB", "CORE"), ("4", "ROLES"), ("LIVE", "SOCKETS")],
            "NEXT.JS · SOCKET.IO · PRISMA · M-PESA",
            "#22d3ee",
            "sphere",
            (844, 224, 705, 390),
        ),
        (
            844, 348,
            "04 // CAMPUS ECOSYSTEM",
            "KAMPUS &amp; MASHINANI",
            [("18MB+", "SUITE"), ("EXPO", "iOS/AND"), ("P2P", "MARKET")],
            "REACT NATIVE · EXPO · NEXT.JS · PGSQL",
            "#38bdf8",
            "gyro",
            (844, 434, 725, 435),
        ),
        (
            844, 558,
            "06 // LIVE EDTECH OS",
            "GERMAN SCHOOL",
            [("A1–C2", "6 TIERS"), ("LIVE", "SYNC"), ("3", "PORTALS")],
            "NEXT.JS · SOCKET.IO · PRISMA · WEBRTC",
            "#34d399",
            "crystal",
            (844, 644, 705, 480),
        ),
    ]

    conduits_svg = []
    subcards_svg = []

    for idx, (cx_card, cy_card, badge, title, metrics, stack_line, accent, shape_kind, (x1, y1, x2, y2)) in enumerate(subcards_spec):
        cw, ch = 328, 184
        # Curved gravitational energy filament connecting card into the central Black Hole
        ctrl_x = (x1 + x2) * 0.5
        ctrl_y = y1
        d_conduit = f"M{x1},{y1} Q{ctrl_x:.1f},{ctrl_y:.1f} {x2},{y2}"
        conduits_svg.append(
            f'<path d="{d_conduit}" fill="none" stroke="{accent}" stroke-opacity="0.28" stroke-width="1.4" stroke-dasharray="6 6"/>'
            f'<path d="{d_conduit}" fill="none" stroke="{accent}" stroke-opacity="0.85" stroke-width="2.2" stroke-dasharray="24 156">'
            f'<animate attributeName="stroke-dashoffset" from="180" to="0" dur="{2.4 + (idx % 3) * 0.4:.1f}s" repeatCount="indefinite"/>'
            f'</path>'
        )

        holo_x = cx_card + cw - 48
        holo_y = cy_card + 52
        wire_paths = make_3d_wireframe_keyframes(shape_kind, holo_x, holo_y)

        m_blocks = []
        for m_i, (m_val, m_lbl) in enumerate(metrics):
            mx = cx_card + 16 + m_i * 99
            my = cy_card + 90
            m_blocks.append(
                f'<rect x="{mx}" y="{my}" width="92" height="50" rx="8" fill="#040a15" fill-opacity="0.88" stroke="{accent}" stroke-opacity="0.38"/>'
                f'<text x="{mx + 46}" y="{my + 25}" text-anchor="middle" fill="{accent}" font-family="ui-monospace,SFMono-Regular,JetBrains Mono,monospace" font-size="16.5" font-weight="900">{m_val}</text>'
                f'<text x="{mx + 46}" y="{my + 41}" text-anchor="middle" fill="#94a3b8" font-family="ui-monospace,SFMono-Regular,monospace" font-size="7.5" font-weight="700" letter-spacing="0.7">{m_lbl}</text>'
            )

        subcards_svg.append(f'''
  <g>
    <rect x="{cx_card}" y="{cy_card}" width="{cw}" height="{ch}" rx="14" fill="#050c19" fill-opacity="0.82" stroke="{accent}" stroke-opacity="0.48" stroke-width="1.2"/>
    <path d="M {cx_card + 18} {cy_card + 1} H {cx_card + 150}" stroke="{accent}" stroke-width="2.2"/>
    <circle cx="{cx_card + 22}" cy="{cy_card + 23}" r="3.5" fill="{accent}"/>
    <text x="{cx_card + 33}" y="{cy_card + 27}" fill="{accent}" font-family="ui-monospace,SFMono-Regular,monospace" font-size="9.5" font-weight="800" letter-spacing="1.1">{badge}</text>
    <text x="{cx_card + 16}" y="{cy_card + 60}" fill="#ffffff" font-family="Inter,ui-sans-serif,system-ui,sans-serif" font-size="18.5" font-weight="900" letter-spacing="-0.4">{title}</text>
    <circle cx="{holo_x}" cy="{holo_y}" r="34" fill="none" stroke="{accent}" stroke-opacity="0.18" stroke-dasharray="4 6"/>
    <path fill="none" stroke="{accent}" stroke-width="1.35" stroke-linejoin="round">
      <animate attributeName="d" values="{";".join(wire_paths)}" dur="8s" repeatCount="indefinite"/>
    </path>
    {"".join(m_blocks)}
    <text x="{cx_card + 16}" y="{cy_card + 164}" fill="#64748b" font-family="ui-monospace,SFMono-Regular,monospace" font-size="9" font-weight="700" letter-spacing="0.6">{stack_line}</text>
  </g>''')

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="Elvin Omondi Juma — Central Gargantua Black Hole &amp; Orbiting Systems">
<defs>
  <clipPath id="cardClip">
    <rect width="{width}" height="{height}" rx="24"/>
  </clipPath>
  <radialGradient id="gridFadeGrad" cx="{bh_cx}" cy="{bh_cy}" r="165" gradientUnits="userSpaceOnUse">
    <stop offset="0%" stop-color="#000000"/>
    <stop offset="52%" stop-color="#000000"/>
    <stop offset="80%" stop-color="#ffffff"/>
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
  <!-- 1. 24-Bit TrueColor Raymarched Gargantua Black Hole at Dead Center (600, 435) -->
  <image href="data:image/png;base64,{b64_backdrop}" width="{width}" height="{height}"/>

  <!-- 2. 60fps Seamless C-Infinity Periodic Einstein-Lensed Spacetime Grid (ZERO Reset!) -->
  <g mask="url(#gridMask)">
    {lensed_grid_svg}
  </g>

  <!-- 3. Continuous 360-Degree Relativistic Plasma Streams in Tilted 3D Perspective (ZERO Reset!) -->
  <g transform="translate({bh_cx}, {bh_cy}) rotate(-12)">
    <path d="M -255 0 A 255 37 0 0 0 255 0" fill="none" stroke="#fef08a" stroke-width="2.2" stroke-opacity="0.88" stroke-dasharray="60 120" filter="url(#softGlow)">
      <animate attributeName="stroke-dashoffset" from="360" to="0" dur="2.4s" repeatCount="indefinite"/>
    </path>
    <path d="M -198 0 A 198 29 0 0 0 198 0" fill="none" stroke="#ffffff" stroke-width="1.8" stroke-opacity="0.92" stroke-dasharray="45 95" filter="url(#softGlow)">
      <animate attributeName="stroke-dashoffset" from="280" to="0" dur="1.8s" repeatCount="indefinite"/>
    </path>
    <path d="M -305 0 A 305 44 0 0 0 305 0" fill="none" stroke="#38bdf8" stroke-width="1.5" stroke-opacity="0.75" stroke-dasharray="40 140" filter="url(#softGlow)">
      <animate attributeName="stroke-dashoffset" from="360" to="0" dur="3.0s" repeatCount="indefinite"/>
    </path>
  </g>

  <!-- 4. Gravitational Energy Conduits Pulling All 6 Orbiting Cards Into the Black Hole -->
  <g filter="url(#softGlow)">
    {"".join(conduits_svg)}
  </g>

  <!-- 5. Top Hero Identity Floating Above the Central Black Hole -->
  <g transform="translate(415, 22)">
    <rect width="370" height="28" rx="14" fill="#040a16" fill-opacity="0.85" stroke="#22d3ee" stroke-opacity="0.45"/>
    <circle cx="18" cy="14" r="4" fill="#10b981" filter="url(#softGlow)">
      <animate attributeName="opacity" values="1;0.2;1" dur="1.6s" repeatCount="indefinite"/>
    </circle>
    <text x="32" y="18" fill="#bae6fd" font-family="ui-monospace,SFMono-Regular,JetBrains Mono,monospace" font-size="10.5" font-weight="800" letter-spacing="1.6">FOUNDING ENGINEER @ GTSS  ·  KENYA</text>
  </g>

  <g font-family="Inter,ui-sans-serif,system-ui,-apple-system,Segoe UI,sans-serif" text-anchor="middle" filter="url(#textShadow)">
    <text x="600" y="96" fill="#ffffff" font-size="44" font-weight="900" letter-spacing="3.5">ELVIN OMONDI JUMA</text>
    <text x="600" y="122" fill="#fbbf24" font-family="ui-monospace,SFMono-Regular,monospace" font-size="12" font-weight="800" letter-spacing="3.2">
      PULLING COMPLEXITY INTO RELIABLE SYSTEMS
    </text>
  </g>

  <!-- 6. 6 Orbiting Flagship Sub-Cards (3 Left Wing, 3 Right Wing Surrounding the Black Hole) -->
  {"".join(subcards_svg)}

  <!-- 7. 4 Translucent Telemetry Pods Docked Along the Bottom Horizon -->
  <g transform="translate(28, 774)" font-family="ui-monospace,SFMono-Regular,JetBrains Mono,monospace">
    <g transform="translate(0, 0)">
      <rect width="272" height="74" rx="12" fill="#050c1a" fill-opacity="0.86" stroke="#f59e0b" stroke-opacity="0.48"/>
      <text x="136" y="35" text-anchor="middle" fill="#fbbf24" font-size="26" font-weight="900">5,107+</text>
      <text x="136" y="55" text-anchor="middle" fill="#cbd5e1" font-size="10" font-weight="700" letter-spacing="1.4">COMMITS (+310% YoY)</text>
    </g>
    <g transform="translate(290, 0)">
      <rect width="272" height="74" rx="12" fill="#050c1a" fill-opacity="0.86" stroke="#22d3ee" stroke-opacity="0.48"/>
      <text x="136" y="35" text-anchor="middle" fill="#22d3ee" font-size="26" font-weight="900">117 / 124</text>
      <text x="136" y="55" text-anchor="middle" fill="#cbd5e1" font-size="10" font-weight="700" letter-spacing="1.4">PUBLIC REPOSITORIES</text>
    </g>
    <g transform="translate(580, 0)">
      <rect width="272" height="74" rx="12" fill="#050c1a" fill-opacity="0.86" stroke="#10b981" stroke-opacity="0.48"/>
      <text x="136" y="35" text-anchor="middle" fill="#34d399" font-size="26" font-weight="900">6 LIVE</text>
      <text x="136" y="55" text-anchor="middle" fill="#cbd5e1" font-size="10" font-weight="700" letter-spacing="1.4">SAAS ECOSYSTEMS</text>
    </g>
    <g transform="translate(870, 0)">
      <rect width="274" height="74" rx="12" fill="#050c1a" fill-opacity="0.86" stroke="#38bdf8" stroke-opacity="0.48"/>
      <text x="137" y="35" text-anchor="middle" fill="#38bdf8" font-size="26" font-weight="900">99.98%</text>
      <text x="137" y="55" text-anchor="middle" fill="#cbd5e1" font-size="10" font-weight="700" letter-spacing="1.4">UPTIME · 0ms LAN POS</text>
    </g>
  </g>
</g>

<rect x="1" y="1" width="{width - 2}" height="{height - 2}" rx="23" fill="none" stroke="#38bdf8" stroke-opacity="0.35" stroke-width="1.5"/>
</svg>
'''
    (ASSETS / "hero-3d.svg").write_text(svg, encoding="utf-8")
    print("hero-3d.svg (Central Black Hole & 6 Orbiting Sub-Cards) generated.")


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

<g fill="none">
  <path id="orbitInner" d="M 410 165 A 190 48 0 1 0 790 165 A 190 48 0 1 0 410 165" stroke="#f59e0b" stroke-opacity="0.25" stroke-width="1.2" stroke-dasharray="6 8"/>
  <path id="orbitMid" d="M 280 165 A 320 78 0 1 1 920 165 A 320 78 0 1 1 280 165" stroke="#22d3ee" stroke-opacity="0.22" stroke-width="1.2" stroke-dasharray="8 10"/>
  <path id="orbitOuter" d="M 150 165 A 450 108 0 1 0 1050 165 A 450 108 0 1 0 150 165" stroke="#10b981" stroke-opacity="0.20" stroke-width="1.2" stroke-dasharray="10 12"/>
</g>

<g transform="translate({cx}, {cy})">
  <circle r="44" fill="#071426" stroke="#fbbf24" stroke-width="2.2" filter="url(#sGlow)"/>
  <circle r="52" fill="none" stroke="#22d3ee" stroke-opacity="0.4" stroke-dasharray="4 8"/>
  <text y="-3" text-anchor="middle" fill="#ffffff" font-family="ui-monospace,SFMono-Regular,monospace" font-size="13" font-weight="900">92% TS</text>
  <text y="14" text-anchor="middle" fill="#fbbf24" font-family="ui-monospace,SFMono-Regular,monospace" font-size="9.5" font-weight="700">CORE ENGINE</text>
</g>

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
