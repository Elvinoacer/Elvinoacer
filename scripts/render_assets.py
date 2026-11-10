"""Generate the Deep-Space & Black-Hole 3D visual suite for Elvin Omondi Juma's GitHub profile."""

from __future__ import annotations

import math
import os
import random
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"

# Deep Space Palette (ZERO purple!)
VOID = "#02040a"
SPACE = "#050a14"
PANEL = "#081121"
BORDER = "#16243d"
TEXT = "#f8fafc"
MUTED = "#94a3b8"
DIM = "#64748b"

GOLD = "#f59e0b"
BRIGHT_GOLD = "#fbbf24"
SOLAR = "#fef08a"
CYAN = "#22d3ee"
ICE = "#38bdf8"
EMERALD = "#10b981"
GREEN = "#34d399"

SCALE = 2
FRAMES = 36
DURATION_MS = 90


def find_font(candidates: list[str]) -> Path:
    search_dirs = [
        Path(os.environ["PROFILE_FONT_DIR"]) if os.environ.get("PROFILE_FONT_DIR") else None,
        Path("/usr/share/fonts/truetype/inter-zorin-os"),
        Path("/usr/share/fonts/truetype/jetbrains-mono-zorin-os"),
        Path("/usr/share/fonts/truetype/dejavu"),
        Path("/usr/local/share/fonts"),
        Path.home() / "Library/Fonts",
        Path("/Library/Fonts"),
    ]
    for name in candidates:
        for d in search_dirs:
            if d is not None and (d / name).is_file():
                return d / name
    raise FileNotFoundError(f"Could not find any of {candidates}")


FONT_PATHS = {
    "regular": find_font(["Inter-Regular.ttf", "DejaVuSans.ttf"]),
    "medium": find_font(["Inter-Medium.ttf", "DejaVuSans.ttf"]),
    "bold": find_font(["Inter-Bold.ttf", "DejaVuSans-Bold.ttf"]),
    "black": find_font(["Inter-Black.ttf", "Inter-ExtraBold.ttf", "DejaVuSans-Bold.ttf"]),
    "mono": find_font(["JetBrainsMono-Medium.ttf", "JetBrainsMono-Regular.ttf", "DejaVuSansMono.ttf"]),
    "mono_bold": find_font(["JetBrainsMono-ExtraBold.ttf", "JetBrainsMono-Bold.ttf", "DejaVuSansMono-Bold.ttf", "DejaVuSansMono.ttf"]),
}
FONTS: dict[tuple[str, int], ImageFont.FreeTypeFont] = {}


def rgb(color: str) -> tuple[int, int, int]:
    c = color.lstrip("#")
    return (int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16))


def rgba(color: str, alpha: int = 255) -> tuple[int, int, int, int]:
    r, g, b = rgb(color)
    return (r, g, b, alpha)


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
    fov: float = 280.0, dist: float = 3.8,
) -> tuple[float, float, float]:
    scale = fov / max(0.5, dist - z)
    return cx + x * scale, cy + y * scale, z


def starfield_svg(width: int, height: int, count: int = 90, seed: int = 42) -> str:
    rng = random.Random(seed)
    items = []
    palette = ["#ffffff", "#bae6fd", "#fef08a", "#67e8f9", "#a7f3d0"]
    for i in range(count):
        x = rng.uniform(12, width - 12)
        y = rng.uniform(12, height - 12)
        r = rng.choice([0.6, 0.8, 1.0, 1.3, 1.7])
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


# ---------------------------------------------------------------------------
# 1. HERO-3D.SVG: Black Hole Gravitational Lensing + Spacetime Funnel + Warp
# ---------------------------------------------------------------------------

def generate_hero_blackhole_svg() -> None:
    width, height = 1200, 540
    bh_x, bh_y = 600.0, 215.0

    # 1. 3D Warped Spacetime Gravity Well Mesh underneath the Black Hole
    mesh_lines = []
    # Concentric relativistic gravity well rings
    for r_idx, radius in enumerate([58, 82, 112, 148, 192, 246, 310, 385, 470]):
        pts = []
        steps = 64
        for s in range(steps + 1):
            theta = (s / steps) * 2.0 * math.pi
            gx = radius * math.cos(theta)
            gz = radius * math.sin(theta)
            # Gravitational potential well depth z_well = -G / sqrt(r^2 + r0^2)
            well_depth = 118.0 / math.sqrt((radius / 62.0) ** 2 + 0.75)
            # Tilt the spacetime fabric toward viewer
            px = bh_x + gx * 1.18
            py = (bh_y + 18) + gz * 0.34 + well_depth
            pts.append(f"{'M' if s == 0 else 'L'}{px:.1f},{py:.1f}")
        op = 0.32 if r_idx < 4 else 0.16
        col = GOLD if r_idx < 2 else (CYAN if r_idx < 5 else "#1e3a5f")
        mesh_lines.append(f'<path d="{"".join(pts)}" fill="none" stroke="{col}" stroke-opacity="{op}" stroke-width="1"/>')

    # Radial spacetime geodesics curving into the singularity
    num_spokes = 24
    for k in range(num_spokes):
        theta = (k / num_spokes) * 2.0 * math.pi
        pts = []
        for step in range(28):
            r = 48.0 + step * 16.5
            # Slight frame-dragging swirl near event horizon
            swirl = theta + (42.0 / (r + 20.0))
            gx = r * math.cos(swirl)
            gz = r * math.sin(swirl)
            well_depth = 118.0 / math.sqrt((r / 62.0) ** 2 + 0.75)
            px = bh_x + gx * 1.18
            py = (bh_y + 18) + gz * 0.34 + well_depth
            pts.append(f"{'M' if step == 0 else 'L'}{px:.1f},{py:.1f}")
        mesh_lines.append(f'<path d="{"".join(pts)}" fill="none" stroke="#22d3ee" stroke-opacity="0.15" stroke-width="0.9"/>')

    # 2. Warp-Speed Space Travel Star Streaks (4 staggered 3D depth waves emerging outside event horizon)
    rng = random.Random(108)
    warp_groups = []
    for g_idx in range(4):
        streaks = []
        for _ in range(18):
            angle = rng.uniform(0, 2.0 * math.pi)
            r1 = rng.uniform(145, 250)
            r2 = r1 + rng.uniform(28, 70)
            x1 = math.cos(angle) * r1 * 1.35
            y1 = math.sin(angle) * r1 * 0.72
            x2 = math.cos(angle) * r2 * 1.35
            y2 = math.sin(angle) * r2 * 0.72
            col = rng.choice(["#ffffff", "#67e8f9", "#fde68a", "#34d399"])
            w = rng.uniform(1.0, 2.2)
            streaks.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{col}" stroke-width="{w:.1f}" stroke-linecap="round"/>')
        begin = -g_idx * 1.25
        warp_groups.append(
            f'<g transform="translate({bh_x},{bh_y})">'
            f'<g>{"".join(streaks)}'
            f'<animateTransform attributeName="transform" type="scale" values="0.52;2.35" dur="5s" begin="{begin}s" repeatCount="indefinite"/>'
            f'<animate attributeName="opacity" values="0;0.85;0" dur="5s" begin="{begin}s" repeatCount="indefinite"/>'
            f'</g></g>'
        )

    stars = starfield_svg(width, height, count=120, seed=77)

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="Elvin Omondi Juma — Deep Space Black Hole Singularity Header">
<defs>
  <radialGradient id="voidBg" cx="0.5" cy="0.4" r="0.75">
    <stop offset="0%" stop-color="#0a1628"/>
    <stop offset="45%" stop-color="#040812"/>
    <stop offset="100%" stop-color="#010307"/>
  </radialGradient>
  <radialGradient id="bhCoreGlow" cx="0.5" cy="0.4" r="0.34">
    <stop offset="0%" stop-color="#fbbf24" stop-opacity="0.38"/>
    <stop offset="38%" stop-color="#f59e0b" stop-opacity="0.16"/>
    <stop offset="70%" stop-color="#22d3ee" stop-opacity="0.08"/>
    <stop offset="100%" stop-color="#010307" stop-opacity="0"/>
  </radialGradient>
  <linearGradient id="accretionMain" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0%" stop-color="#22d3ee" stop-opacity="0.1"/>
    <stop offset="18%" stop-color="#38bdf8" stop-opacity="0.85"/>
    <stop offset="38%" stop-color="#fef08a" stop-opacity="1"/>
    <stop offset="50%" stop-color="#ffffff" stop-opacity="1"/>
    <stop offset="62%" stop-color="#fbbf24" stop-opacity="1"/>
    <stop offset="82%" stop-color="#f59e0b" stop-opacity="0.85"/>
    <stop offset="100%" stop-color="#ea580c" stop-opacity="0.1"/>
  </linearGradient>
  <linearGradient id="lensArcGrad" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0%" stop-color="#38bdf8" stop-opacity="0.2"/>
    <stop offset="30%" stop-color="#fef08a" stop-opacity="0.95"/>
    <stop offset="50%" stop-color="#ffffff" stop-opacity="1"/>
    <stop offset="70%" stop-color="#f59e0b" stop-opacity="0.95"/>
    <stop offset="100%" stop-color="#22d3ee" stop-opacity="0.2"/>
  </linearGradient>
  <filter id="bloom" x="-35%" y="-35%" width="170%" height="170%">
    <feGaussianBlur stdDeviation="6" result="b1"/>
    <feGaussianBlur stdDeviation="14" result="b2"/>
    <feMerge>
      <feMergeNode in="b2"/>
      <feMergeNode in="b1"/>
      <feMergeNode in="SourceGraphic"/>
    </feMerge>
  </filter>
  <filter id="softGlow" x="-20%" y="-20%" width="140%" height="140%">
    <feGaussianBlur stdDeviation="3" result="b"/>
    <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
</defs>

<!-- Deep Cosmic Void -->
<rect width="{width}" height="{height}" rx="22" fill="url(#voidBg)"/>
<rect width="{width}" height="{height}" rx="22" fill="url(#bhCoreGlow)"/>

<!-- Starfield -->
<g>
  {stars}
</g>

<!-- 3D Curved Spacetime Gravity Funnel -->
<g>
  {"".join(mesh_lines)}
</g>

<!-- Pulsing Gravitational Wave Rings Contracting Into the Singularity -->
<g transform="translate({bh_x}, {bh_y + 24})" fill="none">
  <ellipse rx="320" ry="96" stroke="#22d3ee" stroke-width="1.5" stroke-opacity="0">
    <animate attributeName="rx" values="360;62" dur="4.5s" repeatCount="indefinite"/>
    <animate attributeName="ry" values="110;20" dur="4.5s" repeatCount="indefinite"/>
    <animate attributeName="stroke-opacity" values="0;0.45;0" dur="4.5s" repeatCount="indefinite"/>
  </ellipse>
  <ellipse rx="320" ry="96" stroke="#fbbf24" stroke-width="1.5" stroke-opacity="0">
    <animate attributeName="rx" values="360;62" dur="4.5s" begin="-2.25s" repeatCount="indefinite"/>
    <animate attributeName="ry" values="110;20" dur="4.5s" begin="-2.25s" repeatCount="indefinite"/>
    <animate attributeName="stroke-opacity" values="0;0.45;0" dur="4.5s" begin="-2.25s" repeatCount="indefinite"/>
  </ellipse>
</g>

<!-- 3D Warp-Drive Space Travel Streaks -->
{"".join(warp_groups)}

<!-- GARGANTUA BLACK HOLE & GRAVITATIONAL LENSING -->
<g transform="translate({bh_x}, {bh_y}) rotate(-11)">
  <!-- Back Half of Accretion Disk -->
  <path d="M -255 0 A 255 44 0 0 1 255 0" fill="none" stroke="url(#accretionMain)" stroke-width="18" filter="url(#bloom)" opacity="0.85"/>
  <path d="M -210 0 A 210 34 0 0 1 210 0" fill="none" stroke="#fef08a" stroke-width="5" filter="url(#softGlow)"/>

  <!-- Gravitationally Lensed Upper Relativistic Halo (Light bent over top of Black Hole) -->
  <path d="M -112 -4 A 112 96 0 0 1 112 -4" fill="none" stroke="url(#lensArcGrad)" stroke-width="8" filter="url(#bloom)"/>
  <path d="M -98 -2 A 98 84 0 0 1 98 -2" fill="none" stroke="#ffffff" stroke-width="2.2" opacity="0.9"/>

  <!-- Gravitationally Lensed Lower Relativistic Halo (Light bent under bottom of Black Hole) -->
  <path d="M -102 6 A 102 82 0 0 0 102 6" fill="none" stroke="url(#lensArcGrad)" stroke-width="5" filter="url(#bloom)" opacity="0.8"/>

  <!-- Event Horizon Shadow (The Singularity) -->
  <circle cx="0" cy="0" r="68" fill="#010206"/>
  <!-- Photon Sphere Razor Ring -->
  <circle cx="0" cy="0" r="69" fill="none" stroke="#fef08a" stroke-width="2.2" filter="url(#softGlow)">
    <animate attributeName="r" values="68.5;70.5;68.5" dur="2.8s" repeatCount="indefinite"/>
  </circle>
  <circle cx="0" cy="0" r="66" fill="none" stroke="#22d3ee" stroke-width="1" stroke-opacity="0.6"/>

  <!-- Front Half of Relativistic Accretion Disk (Occludes Front of Black Hole Shadow!) -->
  <path d="M -275 0 A 275 46 0 0 0 275 0" fill="none" stroke="url(#accretionMain)" stroke-width="22" filter="url(#bloom)"/>
  <path d="M -235 0 A 235 38 0 0 0 235 0" fill="none" stroke="#ffffff" stroke-width="4" filter="url(#softGlow)"/>

  <!-- High-Velocity Orbiting Accretion Plasma Stream (Front Arc Only so Event Horizon Stays Pitch Black) -->
  <path d="M -195 0 A 195 32 0 0 0 195 0" fill="none" stroke="#fef08a" stroke-width="2.5" stroke-dasharray="45 95" filter="url(#softGlow)">
    <animate attributeName="stroke-dashoffset" values="0;-280" dur="2.4s" repeatCount="indefinite"/>
  </path>
  <path d="M -245 0 A 245 41 0 0 0 245 0" fill="none" stroke="#38bdf8" stroke-width="2" stroke-dasharray="30 110" filter="url(#softGlow)">
    <animate attributeName="stroke-dashoffset" values="0;-280" dur="3.2s" repeatCount="indefinite"/>
  </path>
</g>

<!-- Top Orbital Status Pill -->
<g transform="translate(415, 24)">
  <rect width="370" height="30" rx="15" fill="#050d1a" fill-opacity="0.85" stroke="#22d3ee" stroke-opacity="0.4"/>
  <circle cx="18" cy="15" r="4.5" fill="#10b981" filter="url(#softGlow)">
    <animate attributeName="opacity" values="1;0.2;1" dur="1.4s" repeatCount="indefinite"/>
  </circle>
  <text x="32" y="19" fill="#bae6fd" font-family="ui-monospace,SFMono-Regular,JetBrains Mono,monospace" font-size="11" font-weight="700" letter-spacing="1.6">FOUNDING ENGINEER @ GTSS  ·  KENYA</text>
</g>

<!-- Central Typography & Meaning -->
<g font-family="Inter,ui-sans-serif,system-ui,-apple-system,Segoe UI,sans-serif" text-anchor="middle">
  <text x="600" y="378" fill="#ffffff" font-size="44" font-weight="900" letter-spacing="3">ELVIN OMONDI JUMA</text>
  <text x="600" y="406" fill="#fbbf24" font-family="ui-monospace,SFMono-Regular,monospace" font-size="13" font-weight="800" letter-spacing="3.2">
    PULLING COMPLEXITY INTO RELIABLE SYSTEMS
  </text>
</g>

<!-- 4 Minimal Deep-Space Telemetry Pods -->
<g transform="translate(108, 430)" font-family="ui-monospace,SFMono-Regular,JetBrains Mono,monospace">
  <g transform="translate(0, 0)">
    <rect width="228" height="78" rx="12" fill="#060e1c" fill-opacity="0.88" stroke="#f59e0b" stroke-opacity="0.45"/>
    <text x="114" y="36" text-anchor="middle" fill="#fbbf24" font-size="28" font-weight="900">5,107+</text>
    <text x="114" y="58" text-anchor="middle" fill="#94a3b8" font-size="10.5" font-weight="700" letter-spacing="1.5">COMMITS (+310% YoY)</text>
  </g>
  <g transform="translate(252, 0)">
    <rect width="228" height="78" rx="12" fill="#060e1c" fill-opacity="0.88" stroke="#22d3ee" stroke-opacity="0.45"/>
    <text x="114" y="36" text-anchor="middle" fill="#22d3ee" font-size="28" font-weight="900">117 / 124</text>
    <text x="114" y="58" text-anchor="middle" fill="#94a3b8" font-size="10.5" font-weight="700" letter-spacing="1.5">PUBLIC REPOSITORIES</text>
  </g>
  <g transform="translate(504, 0)">
    <rect width="228" height="78" rx="12" fill="#060e1c" fill-opacity="0.88" stroke="#10b981" stroke-opacity="0.45"/>
    <text x="114" y="36" text-anchor="middle" fill="#34d399" font-size="28" font-weight="900">6 LIVE</text>
    <text x="114" y="58" text-anchor="middle" fill="#94a3b8" font-size="10.5" font-weight="700" letter-spacing="1.5">SAAS ECOSYSTEMS</text>
  </g>
  <g transform="translate(756, 0)">
    <rect width="228" height="78" rx="12" fill="#060e1c" fill-opacity="0.88" stroke="#38bdf8" stroke-opacity="0.45"/>
    <text x="114" y="36" text-anchor="middle" fill="#38bdf8" font-size="28" font-weight="900">99.98%</text>
    <text x="114" y="58" text-anchor="middle" fill="#94a3b8" font-size="10.5" font-weight="700" letter-spacing="1.5">UPTIME · 0ms LAN POS</text>
  </g>
</g>

<rect x="1" y="1" width="{width - 2}" height="{height - 2}" rx="21" fill="none" stroke="#1e293b" stroke-width="1.5"/>
</svg>
'''
    (ASSETS / "hero-3d.svg").write_text(svg, encoding="utf-8")
    print("hero-3d.svg (Black Hole Singularity) generated.")


# ---------------------------------------------------------------------------
# 2. 6 IMPRESSIVE 3D HOLOGRAPHIC SPACE CARDS (card-01.svg .. card-06.svg)
# ---------------------------------------------------------------------------

def make_3d_wireframe_keyframes(kind: str, cx: float, cy: float, keyframes: int = 30) -> list[str]:
    paths: list[str] = []
    for f in range(keyframes + 1):
        angle = (f % keyframes) / keyframes * 2.0 * math.pi
        segs: list[str] = []

        if kind == "helix":
            # 3D Double Helix for Healthcare OS (Afyvia)
            n = 14
            strand1, strand2 = [], []
            for i in range(n):
                t = (i / (n - 1)) * 2.0 - 1.0
                theta = t * math.pi * 1.35 + angle
                x1, y1, z1 = rotate_3d(0.75 * math.cos(theta), t * 1.15, 0.75 * math.sin(theta), 0.25, 0.0, 0.2)
                x2, y2, z2 = rotate_3d(-0.75 * math.cos(theta), t * 1.15, -0.75 * math.sin(theta), 0.25, 0.0, 0.2)
                p1 = project_3d(x1, y1, z1, cx, cy, fov=155.0, dist=3.6)
                p2 = project_3d(x2, y2, z2, cx, cy, fov=155.0, dist=3.6)
                strand1.append(p1)
                strand2.append(p2)
                if i % 2 == 0:
                    segs.append(f"M{p1[0]:.1f},{p1[1]:.1f}L{p2[0]:.1f},{p2[1]:.1f}")
            for i in range(n - 1):
                segs.append(f"M{strand1[i][0]:.1f},{strand1[i][1]:.1f}L{strand1[i+1][0]:.1f},{strand1[i+1][1]:.1f}")
                segs.append(f"M{strand2[i][0]:.1f},{strand2[i][1]:.1f}L{strand2[i+1][0]:.1f},{strand2[i+1][1]:.1f}")

        elif kind == "sphere":
            # 3D Geodesic Octa-Sphere for JustInTime Marketplace
            for ring in range(3):
                pts = []
                for k in range(20):
                    th = (k / 20) * 2.0 * math.pi
                    if ring == 0:
                        vx, vy, vz = math.cos(th), math.sin(th), 0.0
                    elif ring == 1:
                        vx, vy, vz = math.cos(th), 0.0, math.sin(th)
                    else:
                        vx, vy, vz = 0.0, math.cos(th), math.sin(th)
                    rx, ry, rz = rotate_3d(vx, vy, vz, 0.5 + angle * 0.5, angle, 0.3)
                    px, py, _ = project_3d(rx, ry, rz, cx, cy, fov=155.0, dist=3.5)
                    pts.append(f"{'M' if k == 0 else 'L'}{px:.1f},{py:.1f}")
                pts.append("Z")
                segs.append("".join(pts))

        elif kind == "tesseract":
            # 3D Nested Cube / LAN Mesh for Restaurant Manager POS
            verts = []
            for s in (0.95, 0.48):
                for dx in (-s, s):
                    for dy in (-s, s):
                        for dz in (-s, s):
                            rx, ry, rz = rotate_3d(dx, dy, dz, 0.55, angle, angle * 0.5)
                            verts.append(project_3d(rx, ry, rz, cx, cy, fov=145.0, dist=3.8))
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
            # 3D Twin-Star Gyroscope for Kampus & Moi Mashinani
            for r_scale, ax_m, ay_m in ((1.05, 1.0, 1.0), (0.78, -1.0, 1.5), (0.52, 1.5, -1.0)):
                pts = []
                for k in range(24):
                    th = (k / 24) * 2.0 * math.pi
                    rx, ry, rz = rotate_3d(r_scale * math.cos(th), r_scale * math.sin(th), 0.0, angle * ax_m + 0.6, angle * ay_m, 0.4)
                    px, py, _ = project_3d(rx, ry, rz, cx, cy, fov=155.0, dist=3.5)
                    pts.append(f"{'M' if k == 0 else 'L'}{px:.1f},{py:.1f}")
                pts.append("Z")
                segs.append("".join(pts))

        elif kind == "tower":
            # 3D Architectural Prism Structure for Concept Builders
            raw_v = [
                (-0.8, 0.9, -0.8), (0.8, 0.9, -0.8), (0.8, 0.9, 0.8), (-0.8, 0.9, 0.8),
                (-0.55, -0.2, -0.55), (0.55, -0.2, -0.55), (0.55, -0.2, 0.55), (-0.55, -0.2, 0.55),
                (0.0, -1.1, 0.0),
            ]
            pverts = [
                project_3d(*rotate_3d(vx, vy, vz, 0.38, angle, 0.0), cx, cy, fov=155.0, dist=3.6)
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
            # 3D Hexagonal Bipyramid Crystal for German Virtual School
            raw_v = [(0.0, -1.1, 0.0), (0.0, 1.1, 0.0)]
            for k in range(6):
                th = (k / 6) * 2.0 * math.pi
                raw_v.append((0.95 * math.cos(th), 0.0, 0.95 * math.sin(th)))
            pverts = [
                project_3d(*rotate_3d(vx, vy, vz, 0.45, angle, 0.25), cx, cy, fov=155.0, dist=3.6)
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


def generate_space_cards() -> None:
    cards_spec = [
        (
            "card-01.svg",
            "01 // HEALTHCARE OS",
            "AFYVIA · PHARMACARE",
            "Multi-Tenant Pharmacy &amp; Patient Cloud",
            [("57", "PRISMA MODELS"), ("308", "APP ROUTES"), ("4", "PORTALS")],
            ["NEXT.JS 16", "POSTGRESQL", "GROQ AI", "M-PESA"],
            "#10b981",
            "helix",
            101,
        ),
        (
            "card-02.svg",
            "02 // GIG MARKETPLACE",
            "JUSTINTIME",
            "Real-Time Local Dispatch &amp; Escrow",
            [("22MB", "CODEBASE"), ("4", "RBAC ROLES"), ("LIVE", "SOCKET.IO")],
            ["NEXT.JS", "SOCKET.IO", "PRISMA", "M-PESA STK"],
            "#22d3ee",
            "sphere",
            202,
        ),
        (
            "card-03.svg",
            "03 // OFFLINE-FIRST POS",
            "RESTAURANT MANAGER",
            "Zero-Internet LAN Hospitality Intranet",
            [("39", "POS SCREENS"), ("5", "STAFF ROLES"), ("0ms", "CLOUD DEP.")],
            ["ELECTRON", "NODE.JS", "SOCKET.IO", "LAN WIFI"],
            "#f59e0b",
            "tesseract",
            303,
        ),
        (
            "card-04.svg",
            "04 // CAMPUS ECOSYSTEM",
            "KAMPUS &amp; MASHINANI",
            "Mobile Social Network &amp; P2P Market",
            [("18MB+", "ECOSYSTEM"), ("iOS/AND", "NATIVE EXPO"), ("P2P", "COMMERCE")],
            ["REACT NATIVE", "EXPO", "NEXT.JS", "POSTGRESQL"],
            "#38bdf8",
            "gyro",
            404,
        ),
        (
            "card-05.svg",
            "05 // ARCHITECTURAL CAD",
            "CONCEPT BUILDERS",
            "3D House Plans &amp; Live Client Studio",
            [("35MB", "PLATFORM"), ("LIVE", "PRESENCE"), ("CAD", "PIPELINE")],
            ["NEXT.JS", "TYPESCRIPT", "SOCKET.IO", "PRISMA"],
            "#fbbf24",
            "tower",
            505,
        ),
        (
            "card-06.svg",
            "06 // LIVE EDTECH OS",
            "GERMAN VIRTUAL SCHOOL",
            "Interactive Classrooms &amp; Cohort ERP",
            [("A1–C2", "6 CEFR TIERS"), ("LIVE", "CLASS SYNC"), ("3", "PORTALS")],
            ["NEXT.JS", "SOCKET.IO", "PRISMA", "WEBRTC"],
            "#34d399",
            "crystal",
            606,
        ),
    ]

    for filename, badge, title, subtitle, metrics, tags, accent, shape_kind, seed in cards_spec:
        w, h = 580, 245
        holo_cx, holo_cy = 482.0, 118.0
        wire_paths = make_3d_wireframe_keyframes(shape_kind, holo_cx, holo_cy)
        stars = starfield_svg(w, h, count=36, seed=seed)

        metrics_svg = []
        for idx, (m_val, m_lbl) in enumerate(metrics):
            mx = 26 + idx * 116
            metrics_svg.append(
                f'<g transform="translate({mx}, 118)">'
                f'<rect width="106" height="62" rx="10" fill="#071122" fill-opacity="0.9" stroke="{accent}" stroke-opacity="0.38"/>'
                f'<text x="53" y="31" text-anchor="middle" fill="{accent}" font-family="ui-monospace,SFMono-Regular,JetBrains Mono,monospace" font-size="21" font-weight="900">{m_val}</text>'
                f'<text x="53" y="49" text-anchor="middle" fill="#94a3b8" font-family="ui-monospace,SFMono-Regular,monospace" font-size="8.5" font-weight="700" letter-spacing="0.8">{m_lbl}</text>'
                f'</g>'
            )

        tags_svg = []
        tx = 26
        for tag in tags:
            tw = len(tag) * 7 + 18
            tags_svg.append(
                f'<rect x="{tx}" y="198" width="{tw}" height="24" rx="6" fill="#091528" stroke="#1e293b"/>'
                f'<text x="{tx + tw // 2}" y="214" text-anchor="middle" fill="#cbd5e1" font-family="ui-monospace,SFMono-Regular,monospace" font-size="9.5" font-weight="700">{tag}</text>'
            )
            tx += tw + 8

        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{title}">
<defs>
  <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0%" stop-color="#040812"/>
    <stop offset="60%" stop-color="#071020"/>
    <stop offset="100%" stop-color="#03060d"/>
  </linearGradient>
  <radialGradient id="holoGlow" cx="0.83" cy="0.48" r="0.32">
    <stop offset="0%" stop-color="{accent}" stop-opacity="0.24"/>
    <stop offset="100%" stop-color="#03060d" stop-opacity="0"/>
  </radialGradient>
  <filter id="glow" x="-25%" y="-25%" width="150%" height="150%">
    <feGaussianBlur stdDeviation="3" result="b"/>
    <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
</defs>

<rect width="{w}" height="{h}" rx="18" fill="url(#bg)"/>
<rect width="{w}" height="{h}" rx="18" fill="url(#holoGlow)"/>

<!-- Starfield -->
<g>{stars}</g>

<!-- Top Neon Rim Bar -->
<path d="M 28 1.5 H 260" stroke="{accent}" stroke-width="2.5"/>

<!-- Right Side 3D Hologram Pedestal & Rotating 3D Wireframe -->
<g>
  <circle cx="{holo_cx}" cy="{holo_cy}" r="74" fill="none" stroke="{accent}" stroke-opacity="0.18" stroke-dasharray="5 9"/>
  <ellipse cx="{holo_cx}" cy="{holo_cy + 74}" rx="54" ry="12" fill="none" stroke="{accent}" stroke-opacity="0.35" stroke-dasharray="6 6"/>
  <path fill="none" stroke="{accent}" stroke-width="1.65" stroke-linejoin="round" filter="url(#glow)">
    <animate attributeName="d" values="{";".join(wire_paths)}" dur="9s" repeatCount="indefinite"/>
  </path>
</g>

<!-- Left Side Content -->
<g font-family="Inter,ui-sans-serif,system-ui,-apple-system,Segoe UI,sans-serif">
  <circle cx="34" cy="31" r="4" fill="{accent}"/>
  <text x="46" y="35" fill="{accent}" font-family="ui-monospace,SFMono-Regular,monospace" font-size="11" font-weight="800" letter-spacing="1.4">{badge}</text>

  <text x="26" y="72" fill="#ffffff" font-size="25" font-weight="900" letter-spacing="-0.5">{title}</text>
  <text x="26" y="96" fill="#94a3b8" font-size="13" font-weight="500">{subtitle}</text>

  {"".join(metrics_svg)}
  {"".join(tags_svg)}
</g>

<rect x="1" y="1" width="{w - 2}" height="{h - 2}" rx="17" fill="none" stroke="{accent}" stroke-opacity="0.32" stroke-width="1.2"/>
</svg>
'''
        (ASSETS / filename).write_text(svg, encoding="utf-8")
        print(f"{filename} generated.")


# ---------------------------------------------------------------------------
# 3. SPACE-ORBIT-STACK.SVG: Single Focused 3D Orbital Solar System of Tech
# ---------------------------------------------------------------------------

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
  <!-- Inner Orbit Satellites -->
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

  <!-- Mid Orbit Satellites -->
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

  <!-- Outer Orbit Satellites -->
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
    print("architecture-3d.svg (Orbital Solar System) generated.")


# ---------------------------------------------------------------------------
# 4. FOOTER.SVG: Planetary Limb Horizon Seen From Orbit
# ---------------------------------------------------------------------------

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

<!-- Orbiting Signal Beacon Crossing Horizon -->
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
    print("footer.svg (Planetary Horizon) generated.")


def main() -> None:
    ASSETS.mkdir(exist_ok=True)
    generate_hero_blackhole_svg()
    generate_space_cards()
    generate_space_orbit_svg()
    generate_footer_svg()


if __name__ == "__main__":
    main()
