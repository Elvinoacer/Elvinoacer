"""Generate the Deep-Space Gargantua Black Hole, Passing Comets, and Sequential Card Awakening Suite."""

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


def render_deep_space_backdrop_b64(width: int = 1200, height: int = 880, bh_cx: float = 600.0, bh_cy: float = 435.0) -> str:
    """Render the deep-space cosmic void & Einstein-lensed distant starfield (Layer 1, behind everything)."""
    y, x = np.mgrid[0:height, 0:width].astype(np.float32)
    dx = (x - bh_cx) / 195.0
    dy = (y - bh_cy) / 195.0
    r2 = dx * dx + dy * dy
    r = np.sqrt(r2 + 1e-6)

    r_eh = 0.35
    r_einstein = 0.68

    # Deep Cosmic Void Base with subtle nebula depth
    R = np.full((height, width), 2.0, dtype=np.float32)
    G = np.full((height, width), 5.0, dtype=np.float32)
    B = np.full((height, width), 12.0, dtype=np.float32)

    # Subtle deep-space cosmic dust clouds in the far background
    nebula = (
        0.5 * (1.0 + np.sin(dx * 1.1 + np.cos(dy * 1.4)))
        * np.exp(-((dy * 0.55) ** 2))
        * np.clip(r / 1.4, 0.2, 1.0)
    )
    R += nebula * 4.0
    G += nebula * 14.0
    B += nebula * 26.0

    # Einstein gravitational lens glow + lensed background starfield
    e_glow = np.exp(-((r - r_einstein) / 0.45) ** 2) * (r > r_eh)
    deflect = 1.0 - (r_einstein ** 2) / (r2 + 0.04)
    bx = dx * deflect
    by = dy * deflect
    inner_fade = np.clip((r - r_einstein * 0.70) / 0.22, 0.0, 1.0) ** 2

    sx_cell = np.floor(bx * 16.0)
    sy_cell = np.floor(by * 16.0)
    fx = (bx * 16.0) - sx_cell - 0.5
    fy = (by * 16.0) - sy_cell - 0.5
    star_hash = np.sin(sx_cell * 127.1 + sy_cell * 311.7) * 43758.5453
    star_prob = star_hash - np.floor(star_hash)
    stars = (star_prob > 0.938) * np.exp(-(fx * fx + fy * fy) / 0.013) * inner_fade * 0.92

    R += e_glow * 14.0 + stars * 220.0
    G += e_glow * 42.0 + stars * 240.0
    B += e_glow * 78.0 + stars * 255.0

    rgb_arr = np.stack([np.clip(R, 0, 255), np.clip(G, 0, 255), np.clip(B, 0, 255)], axis=-1).astype(np.uint8)
    img = Image.fromarray(rgb_arr)
    buf = BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def render_gargantua_foreground_rgba_b64(width: int = 1200, height: int = 880, bh_cx: float = 600.0, bh_cy: float = 435.0) -> str:
    """
    Raymarch the foreground Gargantua Black Hole as a 32-bit RGBA PNG!
    - The Event Horizon shadow is 100% opaque pitch black (occluding comets & deep space behind it).
    - Rich golden-amber & Doppler-cyan Keplerian spiral arms with high-contrast dark dust lanes.
    - Smooth front equatorial plasma belt slicing across the Event Horizon shadow.
    - Translucent outer spiral wings sweep IN FRONT OF the dormant deep-space project cards!
    """
    y, x = np.mgrid[0:height, 0:width].astype(np.float32)
    dx = (x - bh_cx) / 195.0
    dy = (y - bh_cy) / 195.0

    # Tilt black hole axis by -13 degrees so the equatorial plasma wings sweep across the left/right card sectors
    tilt = np.deg2rad(13.0)
    tx = dx * np.cos(tilt) - dy * np.sin(tilt)
    ty = dx * np.sin(tilt) + dy * np.cos(tilt)

    r2 = tx * tx + ty * ty
    r = np.sqrt(r2 + 1e-6)

    r_eh = 0.36
    r_photon = 0.382

    disk_in = 0.385
    disk_out = 2.75

    # Front equatorial disk slightly offset vertically due to inclination angle
    ty_front = ty - 0.028
    r_disk_front = np.sqrt(tx * tx + (ty_front / 0.135) ** 2 + 1e-6)
    phi_front = np.arctan2(ty_front / 0.135, tx)

    # Gravitationally lensed upper & lower arches of the back disk
    r_disk_lensed = np.sqrt(tx * tx + (ty / 0.78) ** 2 + 1e-6)
    phi_lensed = np.arctan2(ty / 0.78, tx)

    def accretion_spiral(rd, phi, r_peak=0.80, w_spread=0.58, outer_boost=0.26):
        core_radial = np.exp(-((rd - r_peak) / w_spread) ** 2) * (rd > disk_in) * (rd < disk_out)
        core_radial *= np.clip((rd - disk_in) / 0.06, 0.0, 1.0)
        # Extended translucent spiral wings that sweep across the background cards
        wing_radial = outer_boost * np.exp(-((rd - 1.58) / 0.75) ** 2) * (rd > 0.75) * (rd < disk_out)
        radial = np.maximum(core_radial, wing_radial)

        twist = phi + 9.2 / (rd + 0.20)
        s1 = 0.5 + 0.5 * np.sin(twist * 3.0 + np.cos(rd * 12.0))
        s2 = 0.5 + 0.5 * np.cos(twist * 7.0 - rd * 19.0)
        s3 = 0.5 + 0.5 * np.sin(twist * 11.0 + rd * 27.0)
        # High-contrast spiral filaments with dark dust lanes so it never washes out to flat white
        turb = 0.18 + 0.82 * (0.50 * (s1 ** 1.6) + 0.35 * (s2 ** 1.8) + 0.15 * s3)
        doppler = 1.0 - 0.36 * (tx / (rd + 0.28))
        return radial * turb * np.clip(doppler, 0.38, 1.42)

    # Smooth transition across the front of the Event Horizon (no sharp horizontal line!)
    eh_blend = np.clip((r - r_eh) / 0.022, 0.0, 1.0)
    front_equatorial_bridge = np.exp(-((ty_front) / 0.048) ** 2) * np.clip((r_disk_front - 0.42) / 0.18, 0.0, 1.0)
    front_visibility = np.maximum(eh_blend, front_equatorial_bridge * 0.92)

    I_primary = accretion_spiral(r_disk_front, phi_front, 0.82, 0.58, 0.28) * front_visibility
    I_lensed = accretion_spiral(r_disk_lensed, phi_lensed, 0.62, 0.25, 0.08) * eh_blend * 0.82
    I_photon = 1.45 * np.exp(-((r - r_photon) / 0.011) ** 2) * np.clip(eh_blend + 0.35, 0.0, 1.0)
    I_corona = 0.28 * np.exp(-((r - r_photon) / 0.22) ** 2) * eh_blend

    I_total = I_primary + I_lensed + I_photon + I_corona

    # Filmic HDR tone curve on intensity so golden/amber/cyan colors stay rich and saturated
    I_toned = I_total / (1.0 + 0.42 * I_total)

    # Relativistic Doppler color grading:
    # - Approaching left wing (tx < 0) shifts warmer-white / ice-cyan on outer filaments
    # - Core & right wing glow in rich Interstellar solar gold & deep amber
    blue_shift = np.clip(-tx * 0.45 + 0.20, 0.0, 1.0)
    hot_core = np.clip((I_total - 0.85) * 0.85, 0.0, 1.0)

    R = I_toned * (255.0 * (1.0 - 0.06 * blue_shift)) + hot_core * 45.0
    G = I_toned * (152.0 + 64.0 * blue_shift) + hot_core * 78.0
    B = I_toned * (34.0 + 165.0 * blue_shift) + hot_core * 110.0

    # Subtle outer cyan relativistic magnetic halo
    outer_halo = 0.22 * np.exp(-((r - 0.95) / 0.55) ** 2) * eh_blend
    R += outer_halo * 18.0
    G += outer_halo * 95.0
    B += outer_halo * 165.0

    # Event Horizon interior (where not covered by the front equatorial plasma bridge)
    shadow_weight = (1.0 - eh_blend) * (1.0 - front_equatorial_bridge * 0.88)
    R = R * (1.0 - shadow_weight) + 1.0 * shadow_weight
    G = G * (1.0 - shadow_weight) + 2.0 * shadow_weight
    B = B * (1.0 - shadow_weight) + 5.0 * shadow_weight

    # Compute Alpha channel:
    # - 1.0 inside the Event Horizon shadow (completely eclipses comets behind it!)
    # - Proportional to tone-mapped luminance in the accretion disk wings so background cards shine through
    lum = np.maximum(R, np.maximum(G, B)) / 255.0
    plasma_alpha = np.clip(lum * 1.08, 0.0, 1.0)
    core_shadow_alpha = np.clip((r_photon + 0.02 - r) / 0.03, 0.0, 1.0)
    A_norm = np.maximum(core_shadow_alpha, plasma_alpha)

    # Un-premultiply RGB cleanly without blowing out midtones
    denom = np.maximum(A_norm, 0.08)
    R_out = np.where(core_shadow_alpha > 0.8, R, np.clip(R / denom, 0, 255))
    G_out = np.where(core_shadow_alpha > 0.8, G, np.clip(G / denom, 0, 255))
    B_out = np.where(core_shadow_alpha > 0.8, B, np.clip(B / denom, 0, 255))

    rgba_arr = np.stack([R_out, G_out, B_out, np.clip(A_norm * 255.0, 0, 255)], axis=-1).astype(np.uint8)
    img = Image.fromarray(rgba_arr)
    buf = BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def make_3d_wireframe_keyframes(kind: str, cx: float, cy: float, keyframes: int = 24) -> list[str]:
    """Generate 3D rotating wireframe keyframes where f=keyframes is at 2*pi (identical to f=0, zero reset!)."""
    paths: list[str] = []
    for f in range(keyframes + 1):
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


def make_comet_svg(path_id: str, k_times: str, k_points: str, op_times: str, op_vals: str, tail_col: str, begin_offset: str = "-1.6s") -> str:
    """Build a realistic blazing deep-space comet with white-hot nucleus, glowing coma, and tapered ion + dust tails."""
    return f'''
    <g opacity="0">
      <animate attributeName="opacity" values="{op_vals}" keyTimes="{op_times}" dur="24s" begin="{begin_offset}" repeatCount="indefinite"/>
      <!-- Outer Ion Tail -->
      <path d="M 0,-7 L -210,0 L 0,7 Z" fill="url(#cometIonTail_{tail_col})"/>
      <!-- Curved Golden Dust Tail -->
      <path d="M 0,-4 Q -85,-14 -165,-26 L -145,-3 Q -70,2 0,4 Z" fill="url(#cometDustTail)"/>
      <!-- Inner High-Energy Plasma Core Tail -->
      <path d="M 0,-3 L -115,0 L 0,3 Z" fill="url(#cometCoreTail)"/>
      <!-- Glowing Coma Halo -->
      <circle cx="0" cy="0" r="14" fill="url(#cometComa_{tail_col})" filter="url(#softGlow)"/>
      <!-- White-Hot Comet Nucleus -->
      <circle cx="0" cy="0" r="4.5" fill="#ffffff" filter="url(#cometGlow)"/>
      <!-- Trailing Sparkle Particles -->
      <circle cx="-32" cy="-3" r="1.5" fill="#fef08a" opacity="0.85"/>
      <circle cx="-64" cy="2" r="1.2" fill="#bae6fd" opacity="0.75"/>
      <circle cx="-98" cy="-4" r="1.0" fill="#ffffff" opacity="0.65"/>
      <animateMotion dur="24s" begin="{begin_offset}" repeatCount="indefinite" rotate="auto" calcMode="linear" keyPoints="{k_points}" keyTimes="{k_times}">
        <mpath href="#{path_id}"/>
      </animateMotion>
    </g>'''


def generate_unified_main_card_svg() -> None:
    width, height = 1200, 880
    bh_cx, bh_cy = 600.0, 435.0
    begin_offset = "-1.6s"

    b64_backdrop = render_deep_space_backdrop_b64(width, height, bh_cx, bh_cy)
    b64_bh_foreground = render_gargantua_foreground_rgba_b64(width, height, bh_cx, bh_cy)

    # 6 Deep-Space Project Cards (positioned closer to center so the Black Hole's outer accretion disk wings
    # visibly pass IN FRONT of their inner edges when dormant!)
    # Each tuple includes:
    # (cx_card, cy_card, badge, title, metrics, stack_line, accent, shape_kind, active_keytimes, sweep_dir)
    # Schedule over 24s cycle (W = 1/3 = 0.3333 per comet slingshot):
    # - Comet Alpha (t = 0.000..0.333): hits Card 01 (Top-Left) -> slingshots behind BH -> hits Card 02 (Top-Right)
    # - Comet Beta  (t = 0.333..0.667): hits Card 04 (Mid-Right) -> slingshots behind BH -> hits Card 03 (Mid-Left)
    # - Comet Gamma (t = 0.667..1.000): hits Card 05 (Bot-Left) -> slingshots behind BH -> hits Card 06 (Bot-Right)
    subcards_spec = [
        # Card 01: Top-Left (active in Comet Alpha first half: t = 0.035 .. 0.165)
        (
            68, 138,
            "01 // HEALTHCARE OS",
            "AFYVIA · PHARMACARE",
            [("57", "MODELS"), ("308", "ROUTES"), ("4", "PORTALS")],
            "NEXT.JS 16 · PRISMA · GROQ AI · M-PESA",
            "#10b981",
            "helix",
            "0;0.032;0.052;0.150;0.172;1",
            ("0;0.032;0.155;1", "-180;-180;380;380"),
        ),
        # Card 02: Top-Right (active in Comet Alpha second half: t = 0.195 .. 0.325)
        (
            804, 138,
            "02 // GIG MARKETPLACE",
            "JUSTINTIME",
            [("22MB", "CORE"), ("4", "ROLES"), ("LIVE", "SOCKETS")],
            "NEXT.JS · SOCKET.IO · PRISMA · M-PESA",
            "#22d3ee",
            "sphere",
            "0;0.192;0.212;0.310;0.332;1",
            ("0;0.192;0.315;1", "-180;-180;380;380"),
        ),
        # Card 04: Mid-Right (active in Comet Beta first half: t = 0.365 .. 0.495)
        (
            804, 348,
            "04 // CAMPUS ECOSYSTEM",
            "KAMPUS &amp; MASHINANI",
            [("18MB+", "SUITE"), ("EXPO", "iOS/AND"), ("P2P", "MARKET")],
            "REACT NATIVE · EXPO · NEXT.JS · PGSQL",
            "#38bdf8",
            "gyro",
            "0;0.365;0.385;0.483;0.505;1",
            ("0;0.365;0.488;1", "380;380;-180;-180"),
        ),
        # Card 03: Mid-Left (active in Comet Beta second half: t = 0.525 .. 0.655)
        (
            68, 348,
            "03 // OFFLINE-FIRST POS",
            "RESTAURANT POS",
            [("39", "SCREENS"), ("5", "ROLES"), ("0ms", "CLOUD")],
            "ELECTRON · NODE.JS · SOCKET.IO · LAN",
            "#f59e0b",
            "tesseract",
            "0;0.525;0.545;0.643;0.665;1",
            ("0;0.525;0.648;1", "380;380;-180;-180"),
        ),
        # Card 05: Bottom-Left (active in Comet Gamma first half: t = 0.698 .. 0.828)
        (
            68, 558,
            "05 // ARCHITECTURAL CAD",
            "CONCEPT BUILDERS",
            [("35MB", "SUITE"), ("3D", "PLANS"), ("LIVE", "SOCKETS")],
            "NEXT.JS · TYPESCRIPT · SOCKET.IO",
            "#fbbf24",
            "tower",
            "0;0.698;0.718;0.816;0.838;1",
            ("0;0.698;0.821;1", "-180;-180;380;380"),
        ),
        # Card 06: Bottom-Right (active in Comet Gamma second half: t = 0.858 .. 0.988)
        (
            804, 558,
            "06 // LIVE EDTECH OS",
            "GERMAN SCHOOL",
            [("A1–C2", "6 TIERS"), ("LIVE", "SYNC"), ("3", "PORTALS")],
            "NEXT.JS · SOCKET.IO · PRISMA · WEBRTC",
            "#34d399",
            "crystal",
            "0;0.858;0.878;0.976;0.996;1",
            ("0;0.858;0.981;1", "-180;-180;380;380"),
        ),
    ]

    dormant_cards_svg = []
    active_cards_svg = []
    clip_defs_svg = []

    for idx, (cx_card, cy_card, badge, title, metrics, stack_line, accent, shape_kind, active_kt, (sweep_kt, sweep_vals)) in enumerate(subcards_spec):
        cw, ch = 328, 184
        holo_x = cx_card + cw - 48
        holo_y = cy_card + 52
        wire_paths = make_3d_wireframe_keyframes(shape_kind, holo_x, holo_y)
        wire_d_joined = ";".join(wire_paths)

        clip_defs_svg.append(f'<clipPath id="subClip_{idx}"><rect x="{cx_card}" y="{cy_card}" width="{cw}" height="{ch}" rx="14"/></clipPath>')

        # Metric pods for Dormant state (recessed deep-space monolith)
        m_blocks_dormant = []
        # Metric pods for Active state (high-contrast comet-energized card)
        m_blocks_active = []
        for m_i, (m_val, m_lbl) in enumerate(metrics):
            mx = cx_card + 16 + m_i * 99
            my = cy_card + 90
            m_blocks_dormant.append(
                f'<rect x="{mx}" y="{my}" width="92" height="50" rx="8" fill="#030812" fill-opacity="0.75" stroke="{accent}" stroke-opacity="0.22"/>'
                f'<text x="{mx + 46}" y="{my + 25}" text-anchor="middle" fill="{accent}" font-family="ui-monospace,SFMono-Regular,JetBrains Mono,monospace" font-size="16.5" font-weight="900">{m_val}</text>'
                f'<text x="{mx + 46}" y="{my + 41}" text-anchor="middle" fill="#64748b" font-family="ui-monospace,SFMono-Regular,monospace" font-size="7.5" font-weight="700" letter-spacing="0.7">{m_lbl}</text>'
            )
            m_blocks_active.append(
                f'<rect x="{mx}" y="{my}" width="92" height="50" rx="8" fill="#061226" fill-opacity="0.95" stroke="{accent}" stroke-opacity="0.85" stroke-width="1.3"/>'
                f'<text x="{mx + 46}" y="{my + 25}" text-anchor="middle" fill="#ffffff" font-family="ui-monospace,SFMono-Regular,JetBrains Mono,monospace" font-size="17" font-weight="900">{m_val}</text>'
                f'<text x="{mx + 46}" y="{my + 41}" text-anchor="middle" fill="{accent}" font-family="ui-monospace,SFMono-Regular,monospace" font-size="7.5" font-weight="800" letter-spacing="0.8">{m_lbl}</text>'
            )

        # 1. DORMANT CARD (Layer 2: Deep in space BEHIND the Black Hole's outer accretion disk wings, noticeable at 0.34 opacity)
        dormant_cards_svg.append(f'''
  <g opacity="0.34">
    <rect x="{cx_card}" y="{cy_card}" width="{cw}" height="{ch}" rx="14" fill="#030710" fill-opacity="0.80" stroke="{accent}" stroke-opacity="0.32" stroke-width="1.0"/>
    <circle cx="{cx_card + 22}" cy="{cy_card + 23}" r="3" fill="{accent}" opacity="0.7"/>
    <text x="{cx_card + 33}" y="{cy_card + 27}" fill="{accent}" font-family="ui-monospace,SFMono-Regular,monospace" font-size="9.5" font-weight="800" letter-spacing="1.1">{badge}</text>
    <text x="{cx_card + 16}" y="{cy_card + 60}" fill="#cbd5e1" font-family="Inter,ui-sans-serif,system-ui,sans-serif" font-size="18.5" font-weight="900" letter-spacing="-0.4">{title}</text>
    <circle cx="{holo_x}" cy="{holo_y}" r="34" fill="none" stroke="{accent}" stroke-opacity="0.15" stroke-dasharray="4 6"/>
    <path d="{wire_paths[0]}" fill="none" stroke="{accent}" stroke-opacity="0.65" stroke-width="1.1" stroke-linejoin="round">
      <animate attributeName="d" values="{wire_d_joined}" dur="8s" repeatCount="indefinite"/>
    </path>
    {"".join(m_blocks_dormant)}
    <text x="{cx_card + 16}" y="{cy_card + 164}" fill="#475569" font-family="ui-monospace,SFMono-Regular,monospace" font-size="9" font-weight="700" letter-spacing="0.6">{stack_line}</text>
  </g>''')

        # 2. ACTIVE ILLUMINATED CARD (Layer 4: Ignites to 100% visibility & clarity ONLY when the Comet passes through it!)
        active_cards_svg.append(f'''
  <g opacity="0">
    <animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="{active_kt}" dur="24s" begin="{begin_offset}" repeatCount="indefinite"/>
    <!-- Outer Comet-Strike Energy Halo -->
    <rect x="{cx_card - 3}" y="{cy_card - 3}" width="{cw + 6}" height="{ch + 6}" rx="17" fill="none" stroke="{accent}" stroke-opacity="0.75" stroke-width="2.6" filter="url(#softGlow)"/>
    <!-- Translucent High-Contrast Active Card Body (Comet shines through the glass while metrics stay 100% crisp on top!) -->
    <rect x="{cx_card}" y="{cy_card}" width="{cw}" height="{ch}" rx="14" fill="#040c1b" fill-opacity="0.70" stroke="{accent}" stroke-opacity="1.0" stroke-width="2.0"/>
    <!-- Internal Comet Shockwave Shimmer Sweep -->
    <g clip-path="url(#subClip_{idx})">
      <rect x="{cx_card}" y="{cy_card - 20}" width="130" height="{ch + 40}" fill="url(#cometSweepGrad)" transform="skewX(-20)">
        <animate attributeName="x" values="{sweep_vals}" keyTimes="{sweep_kt}" dur="24s" begin="{begin_offset}" repeatCount="indefinite"/>
      </rect>
    </g>
    <path d="M {cx_card + 16} {cy_card + 1} H {cx_card + 190}" stroke="#ffffff" stroke-width="2.6" filter="url(#softGlow)"/>
    <circle cx="{cx_card + 22}" cy="{cy_card + 23}" r="4.2" fill="#ffffff" filter="url(#softGlow)"/>
    <text x="{cx_card + 34}" y="{cy_card + 27}" fill="{accent}" font-family="ui-monospace,SFMono-Regular,monospace" font-size="9.5" font-weight="900" letter-spacing="1.2">{badge}  ·  ACTIVE</text>
    <text x="{cx_card + 16}" y="{cy_card + 60}" fill="#ffffff" font-family="Inter,ui-sans-serif,system-ui,sans-serif" font-size="19" font-weight="900" letter-spacing="-0.4" filter="url(#textShadow)">{title}</text>
    <circle cx="{holo_x}" cy="{holo_y}" r="35" fill="#07162e" fill-opacity="0.78" stroke="{accent}" stroke-opacity="0.60" stroke-dasharray="5 5"/>
    <path d="{wire_paths[0]}" fill="none" stroke="#ffffff" stroke-width="1.65" stroke-linejoin="round" filter="url(#softGlow)">
      <animate attributeName="d" values="{wire_d_joined}" dur="8s" repeatCount="indefinite"/>
    </path>
    {"".join(m_blocks_active)}
    <text x="{cx_card + 16}" y="{cy_card + 164}" fill="#e2e8f0" font-family="ui-monospace,SFMono-Regular,monospace" font-size="9" font-weight="800" letter-spacing="0.6">{stack_line}</text>
  </g>''')

    # Build the 3 Gravitational Slingshot Comets
    # Comet Alpha: 0.000..0.333 (Card 01 -> behind Black Hole -> Card 02)
    comet_alpha_bg = make_comet_svg(
        "cometPathAlpha",
        "0;0.333;1",
        "0;1;1",
        "0;0.015;0.318;0.333;1",
        "0;1;1;0;0",
        "cyan",
        begin_offset,
    )
    # Comet Beta: 0.333..0.667 (Card 04 -> behind Black Hole -> Card 03)
    comet_beta_bg = make_comet_svg(
        "cometPathBeta",
        "0;0.333;0.667;1",
        "0;0;1;1",
        "0;0.333;0.348;0.652;0.667;1",
        "0;0;1;1;0;0",
        "gold",
        begin_offset,
    )
    # Comet Gamma: 0.667..1.000 (Card 05 -> behind Black Hole -> Card 06)
    comet_gamma_bg = make_comet_svg(
        "cometPathGamma",
        "0;0.667;1",
        "0;0;1",
        "0;0.667;0.682;0.985;1",
        "0;0;1;1;0",
        "emerald",
        begin_offset,
    )

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="Elvin Omondi Juma — Gargantua Black Hole, Deep-Space Cards &amp; Passing Comets">
<defs>
  <clipPath id="cardClip">
    <rect width="{width}" height="{height}" rx="24"/>
  </clipPath>
  {"".join(clip_defs_svg)}

  <!-- Mask so Foreground Comet Streak is visible over the Active Cards but ECLIPSED behind the Black Hole Center -->
  <radialGradient id="bhEclipseGrad" cx="{bh_cx}" cy="{bh_cy}" r="175" gradientUnits="userSpaceOnUse">
    <stop offset="0%" stop-color="#000000"/>
    <stop offset="62%" stop-color="#000000"/>
    <stop offset="88%" stop-color="#ffffff"/>
    <stop offset="100%" stop-color="#ffffff"/>
  </radialGradient>
  <mask id="outsideBlackHoleMask">
    <rect width="{width}" height="{height}" fill="url(#bhEclipseGrad)"/>
  </mask>

  <!-- Comet Tail & Coma Gradients -->
  <linearGradient id="cometIonTail_cyan" x1="1" y1="0" x2="0" y2="0">
    <stop offset="0%" stop-color="#ffffff" stop-opacity="0.95"/>
    <stop offset="25%" stop-color="#22d3ee" stop-opacity="0.75"/>
    <stop offset="65%" stop-color="#0284c7" stop-opacity="0.28"/>
    <stop offset="100%" stop-color="#0284c7" stop-opacity="0"/>
  </linearGradient>
  <linearGradient id="cometIonTail_gold" x1="1" y1="0" x2="0" y2="0">
    <stop offset="0%" stop-color="#ffffff" stop-opacity="0.95"/>
    <stop offset="25%" stop-color="#fbbf24" stop-opacity="0.78"/>
    <stop offset="65%" stop-color="#f59e0b" stop-opacity="0.28"/>
    <stop offset="100%" stop-color="#f59e0b" stop-opacity="0"/>
  </linearGradient>
  <linearGradient id="cometIonTail_emerald" x1="1" y1="0" x2="0" y2="0">
    <stop offset="0%" stop-color="#ffffff" stop-opacity="0.95"/>
    <stop offset="25%" stop-color="#34d399" stop-opacity="0.78"/>
    <stop offset="65%" stop-color="#10b981" stop-opacity="0.28"/>
    <stop offset="100%" stop-color="#10b981" stop-opacity="0"/>
  </linearGradient>
  <linearGradient id="cometDustTail" x1="1" y1="0" x2="0" y2="0">
    <stop offset="0%" stop-color="#fef08a" stop-opacity="0.65"/>
    <stop offset="45%" stop-color="#f59e0b" stop-opacity="0.25"/>
    <stop offset="100%" stop-color="#f59e0b" stop-opacity="0"/>
  </linearGradient>
  <linearGradient id="cometCoreTail" x1="1" y1="0" x2="0" y2="0">
    <stop offset="0%" stop-color="#ffffff" stop-opacity="1"/>
    <stop offset="50%" stop-color="#bae6fd" stop-opacity="0.7"/>
    <stop offset="100%" stop-color="#22d3ee" stop-opacity="0"/>
  </linearGradient>
  <radialGradient id="cometComa_cyan">
    <stop offset="0%" stop-color="#ffffff" stop-opacity="1"/>
    <stop offset="40%" stop-color="#22d3ee" stop-opacity="0.65"/>
    <stop offset="100%" stop-color="#22d3ee" stop-opacity="0"/>
  </radialGradient>
  <radialGradient id="cometComa_gold">
    <stop offset="0%" stop-color="#ffffff" stop-opacity="1"/>
    <stop offset="40%" stop-color="#fbbf24" stop-opacity="0.65"/>
    <stop offset="100%" stop-color="#f59e0b" stop-opacity="0"/>
  </radialGradient>
  <radialGradient id="cometComa_emerald">
    <stop offset="0%" stop-color="#ffffff" stop-opacity="1"/>
    <stop offset="40%" stop-color="#34d399" stop-opacity="0.65"/>
    <stop offset="100%" stop-color="#10b981" stop-opacity="0"/>
  </radialGradient>
  <linearGradient id="cometSweepGrad" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0%" stop-color="#ffffff" stop-opacity="0"/>
    <stop offset="50%" stop-color="#38bdf8" stop-opacity="0.26"/>
    <stop offset="100%" stop-color="#ffffff" stop-opacity="0"/>
  </linearGradient>

  <!-- Gravitational Slingshot Trajectories Passing Through the Cards & Behind the Central Black Hole -->
  <path id="cometPathAlpha" d="M -140 145 C 80 195, 380 415, 600 415 C 820 415, 1120 195, 1340 145" fill="none"/>
  <path id="cometPathBeta" d="M 1340 385 C 1100 430, 820 455, 600 445 C 380 435, 100 445, -140 495" fill="none"/>
  <path id="cometPathGamma" d="M -140 735 C 80 685, 380 460, 600 460 C 820 460, 1120 685, 1340 735" fill="none"/>

  <filter id="softGlow" x="-25%" y="-25%" width="150%" height="150%">
    <feGaussianBlur stdDeviation="3.5" result="b"/>
    <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
  <filter id="cometGlow" x="-50%" y="-50%" width="200%" height="200%">
    <feGaussianBlur stdDeviation="5" result="b"/>
    <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
  <filter id="textShadow" x="-20%" y="-20%" width="140%" height="140%">
    <feDropShadow dx="0" dy="2" stdDeviation="6" flood-color="#000000" flood-opacity="0.95"/>
  </filter>
</defs>

<g clip-path="url(#cardClip)">
  <!-- LAYER 1: Deep-Space Void & Einstein-Lensed Starfield Backdrop (NO Grids!) -->
  <image href="data:image/png;base64,{b64_backdrop}" width="{width}" height="{height}"/>

  <!-- LAYER 2: The 6 Deep-Space Project Cards in Dormant State (Resting Behind the Black Hole!) -->
  {"".join(dormant_cards_svg)}

  <!-- LAYER 2.5: Deep-Space Comets Slingshotting Behind the Black Hole's Event Horizon -->
  {comet_alpha_bg}
  {comet_beta_bg}
  {comet_gamma_bg}

  <!-- LAYER 3: Foreground 32-Bit RGBA Gargantua Black Hole (Event Horizon & Accretion Disk Wings IN FRONT of Background Cards!) -->
  <image href="data:image/png;base64,{b64_bh_foreground}" width="{width}" height="{height}"/>

  <!-- Subtle Relativistic Plasma Streams Along the Black Hole's Tilted Accretion Disk -->
  <g transform="translate({bh_cx}, {bh_cy}) rotate(-13)">
    <path d="M -275 0 A 275 38 0 0 0 275 0" fill="none" stroke="#fef08a" stroke-width="2.0" stroke-opacity="0.82" stroke-dasharray="60 120" filter="url(#softGlow)">
      <animate attributeName="stroke-dashoffset" from="360" to="0" dur="2.4s" repeatCount="indefinite"/>
    </path>
    <path d="M -205 0 A 205 29 0 0 0 205 0" fill="none" stroke="#ffffff" stroke-width="1.6" stroke-opacity="0.88" stroke-dasharray="45 95" filter="url(#softGlow)">
      <animate attributeName="stroke-dashoffset" from="280" to="0" dur="1.8s" repeatCount="indefinite"/>
    </path>
  </g>

  <!-- LAYER 3.5: Foreground Comet Streak (Shines Through the Translucent Glass of the Active Card, Eclipsed Behind the Black Hole Core!) -->
  <g mask="url(#outsideBlackHoleMask)">
    {comet_alpha_bg}
    {comet_beta_bg}
    {comet_gamma_bg}
  </g>

  <!-- LAYER 4: Comet-Triggered Active Card Illumination (Lights Up 1 Card at a Time as Comet Passes Through!) -->
  {"".join(active_cards_svg)}

  <!-- LAYER 5: Top Hero Identity Floating Above the Central Black Hole -->
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

  <!-- LAYER 6: 4 Translucent Telemetry Pods Docked Along the Bottom Horizon -->
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
    print("hero-3d.svg (Foreground Black Hole + Deep-Space Background Cards + Passing Comets) generated.")


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
