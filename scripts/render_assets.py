"""Generate state-of-the-art 3D SVG & raster animations for Elvin Omondi Juma's profile."""

from __future__ import annotations

import math
import os
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"

BG = "#060911"
BG_ALT = "#0b1120"
PANEL = "#0f172a"
BORDER = "#1e293b"
TEXT = "#f8fafc"
MUTED = "#94a3b8"
DIM = "#64748b"
GREEN = "#39d353"
CYAN = "#22d3ee"
BLUE = "#38bdf8"
VIOLET = "#a78bfa"
AMBER = "#f59e0b"
ROSE = "#f43f5e"
GREENS = ["#0e4429", "#006d32", "#26a641", "#39d353"]

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


def blend(a: str, b: str, t: float) -> tuple[int, int, int]:
    t = max(0.0, min(1.0, t))
    return tuple(round(x + (y - x) * t) for x, y in zip(rgb(a), rgb(b)))


def hex_blend(a: str, b: str, t: float) -> str:
    r, g, bl = blend(a, b, t)
    return f"#{r:02x}{g:02x}{bl:02x}"


# ---------------------------------------------------------------------------
# 3D Math & Projection Helpers
# ---------------------------------------------------------------------------

def rotate_3d(x: float, y: float, z: float, ax: float, ay: float, az: float) -> tuple[float, float, float]:
    # Rotate around X
    cy, sy = math.cos(ax), math.sin(ax)
    y, z = y * cy - z * sy, y * sy + z * cy
    # Rotate around Y
    cx, sx = math.cos(ay), math.sin(ay)
    x, z = x * cx + z * sx, -x * sx + z * cx
    # Rotate around Z
    cz, sz = math.cos(az), math.sin(az)
    x, y = x * cz - y * sz, x * sz + y * cz
    return x, y, z


def project_3d(
    x: float, y: float, z: float,
    cx: float, cy: float,
    fov: float = 340.0, dist: float = 4.2,
) -> tuple[float, float, float]:
    scale = fov / max(0.5, dist - z)
    return cx + x * scale, cy + y * scale, z


def iso_project(gx: float, gy: float, gz: float, ox: float, oy: float, tile_w: float = 24.0, tile_h: float = 12.0) -> tuple[float, float]:
    sx = ox + (gx - gy) * (tile_w * 0.5)
    sy = oy + (gx + gy) * (tile_h * 0.5) - gz
    return sx, sy


def icosahedron_geometry() -> tuple[list[tuple[float, float, float]], list[tuple[int, int]], list[tuple[int, int, int]]]:
    phi = (1.0 + math.sqrt(5.0)) / 2.0
    raw = [
        (-1,  phi, 0), ( 1,  phi, 0), (-1, -phi, 0), ( 1, -phi, 0),
        ( 0, -1,  phi), ( 0,  1,  phi), ( 0, -1, -phi), ( 0,  1, -phi),
        ( phi, 0, -1), ( phi, 0,  1), (-phi, 0, -1), (-phi, 0,  1),
    ]
    verts = []
    for x, y, z in raw:
        length = math.sqrt(x * x + y * y + z * z)
        verts.append((x / length, y / length, z / length))
    faces = [
        (0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11),
        (1, 5, 9), (5, 11, 4), (11, 10, 2), (10, 7, 6), (7, 1, 8),
        (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9),
        (4, 9, 5), (2, 4, 11), (6, 2, 10), (8, 6, 7), (9, 8, 1),
    ]
    edges_set: set[tuple[int, int]] = set()
    for a, b, c in faces:
        for u, v in ((a, b), (b, c), (c, a)):
            edges_set.add((min(u, v), max(u, v)))
    return verts, sorted(edges_set), faces


def octahedron_geometry(scale: float = 0.56) -> tuple[list[tuple[float, float, float]], list[tuple[int, int]]]:
    verts = [
        (scale, 0, 0), (-scale, 0, 0),
        (0, scale, 0), (0, -scale, 0),
        (0, 0, scale), (0, 0, -scale),
    ]
    edges = [
        (0, 2), (0, 3), (0, 4), (0, 5),
        (1, 2), (1, 3), (1, 4), (1, 5),
        (2, 4), (4, 3), (3, 5), (5, 2),
    ]
    return verts, edges


def svg_3d_cube_faces(cx: float, cy: float, w: float, h: float, depth: float, top_c: str, left_c: str, right_c: str, stroke: str = "#38bdf8", stroke_op: float = 0.35) -> str:
    hw = w * 0.5
    hh = h * 0.5
    top = f"M{cx:.1f},{cy - depth - hh:.1f} L{cx + hw:.1f},{cy - depth:.1f} L{cx:.1f},{cy - depth + hh:.1f} L{cx - hw:.1f},{cy - depth:.1f} Z"
    left = f"M{cx - hw:.1f},{cy - depth:.1f} L{cx:.1f},{cy - depth + hh:.1f} L{cx:.1f},{cy + hh:.1f} L{cx - hw:.1f},{cy:.1f} Z"
    right = f"M{cx:.1f},{cy - depth + hh:.1f} L{cx + hw:.1f},{cy - depth:.1f} L{cx + hw:.1f},{cy:.1f} L{cx:.1f},{cy + hh:.1f} Z"
    return (
        f'<path d="{left}" fill="{left_c}" stroke="{stroke}" stroke-opacity="{stroke_op}" stroke-width="0.8"/>'
        f'<path d="{right}" fill="{right_c}" stroke="{stroke}" stroke-opacity="{stroke_op}" stroke-width="0.8"/>'
        f'<path d="{top}" fill="{top_c}" stroke="{stroke}" stroke-opacity="{min(1.0, stroke_op + 0.25)}" stroke-width="1"/>'
    )


# ---------------------------------------------------------------------------
# 1. HERO-3D.SVG: 60fps Vector 3D Command Deck & Rotating Icosahedral Reactor
# ---------------------------------------------------------------------------

def generate_hero_3d_svg() -> None:
    verts, edges, _ = icosahedron_geometry()
    oct_verts, oct_edges = octahedron_geometry(0.54)

    cx, cy = 975.0, 232.0
    keyframes = 36

    outer_paths: list[str] = []
    inner_paths: list[str] = []
    ring1_paths: list[str] = []
    ring2_paths: list[str] = []

    ring_pts = 32
    for frame in range(keyframes + 1):
        t = (frame % keyframes) / keyframes
        angle = t * 2.0 * math.pi

        # Outer icosahedron path
        segs = []
        pverts = [
            project_3d(*rotate_3d(vx, vy, vz, angle * 0.7 + 0.35, angle, angle * 0.4), cx, cy, fov=315.0, dist=3.6)
            for vx, vy, vz in verts
        ]
        for u, v in edges:
            x1, y1, _ = pverts[u]
            x2, y2, _ = pverts[v]
            segs.append(f"M{x1:.1f},{y1:.1f}L{x2:.1f},{y2:.1f}")
        outer_paths.append("".join(segs))

        # Inner counter-rotating octahedron path
        isegs = []
        ipverts = [
            project_3d(*rotate_3d(vx, vy, vz, -angle, -angle * 1.3 + 0.5, angle * 0.8), cx, cy, fov=315.0, dist=3.6)
            for vx, vy, vz in oct_verts
        ]
        for u, v in oct_edges:
            x1, y1, _ = ipverts[u]
            x2, y2, _ = ipverts[v]
            isegs.append(f"M{x1:.1f},{y1:.1f}L{x2:.1f},{y2:.1f}")
        inner_paths.append("".join(isegs))

        # 3D Tilted Orbital Ring 1
        r1 = []
        for k in range(ring_pts):
            theta = (k / ring_pts) * 2.0 * math.pi
            rx, ry, rz = rotate_3d(1.32 * math.cos(theta), 1.32 * math.sin(theta), 0.0, 1.05, angle * 0.5, 0.35)
            px, py, _ = project_3d(rx, ry, rz, cx, cy, fov=315.0, dist=3.6)
            r1.append(f"{'M' if k == 0 else 'L'}{px:.1f},{py:.1f}")
        r1.append("Z")
        ring1_paths.append("".join(r1))

        # 3D Tilted Orbital Ring 2
        r2 = []
        for k in range(ring_pts):
            theta = (k / ring_pts) * 2.0 * math.pi
            rx, ry, rz = rotate_3d(1.52 * math.cos(theta), 0.0, 1.52 * math.sin(theta), -0.55, -angle * 0.5, 0.8)
            px, py, _ = project_3d(rx, ry, rz, cx, cy, fov=315.0, dist=3.6)
            r2.append(f"{'M' if k == 0 else 'L'}{px:.1f},{py:.1f}")
        r2.append("Z")
        ring2_paths.append("".join(r2))

    # Build 3D Isometric Voxel Wave Ribbon across bottom-center/right
    voxels_svg = []
    cols, rows = 15, 3
    base_ox, base_oy = 420.0, 442.0
    for r in range(rows):
        for c in range(cols):
            sx = base_ox + c * 21.0 + r * 11.0
            sy = base_oy + r * 6.5
            wave_val = math.sin(c * 0.52 + r * 0.75) * 0.5 + 0.5
            h_base = 5.0 + wave_val * 16.0
            h_peak = 5.0 + (1.0 - wave_val) * 20.0
            delay = (c * 0.14 + r * 0.22)
            if wave_val > 0.65:
                tc, lc, rc, sc = "#39d353", "#006d32", "#0e4429", "#39d353"
            elif wave_val > 0.35:
                tc, lc, rc, sc = "#22d3ee", "#0284c7", "#0f172a", "#22d3ee"
            else:
                tc, lc, rc, sc = "#1e293b", "#0f172a", "#090d16", "#334155"
            cube = svg_3d_cube_faces(sx, sy, 18.0, 8.5, h_base, tc, lc, rc, sc, 0.45)
            voxels_svg.append(
                f'<g>{cube}'
                f'<animateTransform attributeName="transform" type="translate" '
                f'values="0,0; 0,{- (h_peak - h_base) * 0.45:.1f}; 0,0" '
                f'dur="3.2s" begin="-{delay:.2f}s" repeatCount="indefinite"/>'
                f'</g>'
            )

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="485" viewBox="0 0 1200 485" role="img" aria-label="Elvin Omondi Juma — Founding Engineer &amp; Full-Stack Systems Architect">
<defs>
  <linearGradient id="bgGrad" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0%" stop-color="#050811"/>
    <stop offset="52%" stop-color="#09101f"/>
    <stop offset="100%" stop-color="#050b14"/>
  </linearGradient>
  <radialGradient id="coreGlow" cx="0.81" cy="0.48" r="0.36">
    <stop offset="0%" stop-color="#22d3ee" stop-opacity="0.28"/>
    <stop offset="45%" stop-color="#39d353" stop-opacity="0.10"/>
    <stop offset="100%" stop-color="#050811" stop-opacity="0"/>
  </radialGradient>
  <radialGradient id="leftGlow" cx="0.18" cy="0.28" r="0.42">
    <stop offset="0%" stop-color="#39d353" stop-opacity="0.14"/>
    <stop offset="60%" stop-color="#38bdf8" stop-opacity="0.05"/>
    <stop offset="100%" stop-color="#050811" stop-opacity="0"/>
  </radialGradient>
  <linearGradient id="cyberAccent" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0%" stop-color="#39d353"/>
    <stop offset="50%" stop-color="#22d3ee"/>
    <stop offset="100%" stop-color="#a78bfa"/>
  </linearGradient>
  <linearGradient id="titleGrad" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0%" stop-color="#ffffff"/>
    <stop offset="65%" stop-color="#e2e8f0"/>
    <stop offset="100%" stop-color="#67e8f9"/>
  </linearGradient>
  <linearGradient id="cardGrad" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%" stop-color="#0f172a" stop-opacity="0.9"/>
    <stop offset="100%" stop-color="#090d16" stop-opacity="0.95"/>
  </linearGradient>
  <filter id="neonGlow" x="-25%" y="-25%" width="150%" height="150%">
    <feGaussianBlur stdDeviation="4" result="blur"/>
    <feMerge>
      <feMergeNode in="blur"/>
      <feMergeNode in="SourceGraphic"/>
    </feMerge>
  </filter>
  <filter id="heavyGlow" x="-40%" y="-40%" width="180%" height="180%">
    <feGaussianBlur stdDeviation="9" result="blur"/>
    <feMerge>
      <feMergeNode in="blur"/>
      <feMergeNode in="SourceGraphic"/>
    </feMerge>
  </filter>
  <pattern id="isoGrid" width="40" height="40" patternUnits="userSpaceOnUse">
    <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#1e293b" stroke-width="0.7" stroke-opacity="0.45"/>
  </pattern>
</defs>

<!-- Deep Space & Cyber Grid Background -->
<rect width="1200" height="485" rx="22" fill="url(#bgGrad)"/>
<rect width="1200" height="485" rx="22" fill="url(#isoGrid)"/>
<rect width="1200" height="485" rx="22" fill="url(#coreGlow)"/>
<rect width="1200" height="485" rx="22" fill="url(#leftGlow)"/>

<!-- 3D Perspective Floor Grid Lines -->
<g stroke="#22d3ee" stroke-opacity="0.10" stroke-width="1">
  <line x1="0" y1="440" x2="1200" y2="440"/>
  <line x1="0" y1="462" x2="1200" y2="462"/>
  <line x1="600" y1="320" x2="120" y2="485"/>
  <line x1="600" y1="320" x2="360" y2="485"/>
  <line x1="600" y1="320" x2="600" y2="485"/>
  <line x1="600" y1="320" x2="840" y2="485"/>
  <line x1="600" y1="320" x2="1080" y2="485"/>
</g>

<!-- Scanning Horizon Laser -->
<line x1="2" y1="0" x2="1198" y2="0" stroke="url(#cyberAccent)" stroke-width="1.5" stroke-opacity="0.35">
  <animate attributeName="y1" values="18;468;18" dur="9s" repeatCount="indefinite"/>
  <animate attributeName="y2" values="18;468;18" dur="9s" repeatCount="indefinite"/>
</line>

<!-- 3D Isometric Voxel Contribution Wave -->
<g opacity="0.92">
  {"".join(voxels_svg)}
</g>

<!-- RIGHT SIDE: True 3D Projected Geodesic Icosahedron & Octahedron Reactor -->
<g>
  <!-- Outer HUD Rings -->
  <circle cx="{cx}" cy="{cy}" r="182" fill="none" stroke="#1e293b" stroke-width="1"/>
  <circle cx="{cx}" cy="{cy}" r="170" fill="none" stroke="#38bdf8" stroke-opacity="0.22" stroke-width="1.5" stroke-dasharray="6 14">
    <animateTransform attributeName="transform" type="rotate" from="0 {cx} {cy}" to="360 {cx} {cy}" dur="28s" repeatCount="indefinite"/>
  </circle>
  <circle cx="{cx}" cy="{cy}" r="144" fill="none" stroke="#39d353" stroke-opacity="0.25" stroke-width="1.2" stroke-dasharray="18 10 4 10">
    <animateTransform attributeName="transform" type="rotate" from="360 {cx} {cy}" to="0 {cx} {cy}" dur="18s" repeatCount="indefinite"/>
  </circle>

  <!-- 3D Perspective Orbital Rings -->
  <path fill="none" stroke="#a78bfa" stroke-width="1.4" stroke-opacity="0.45" stroke-dasharray="8 6">
    <animate attributeName="d" values="{";".join(ring1_paths)}" dur="11s" repeatCount="indefinite"/>
  </path>
  <path fill="none" stroke="#39d353" stroke-width="1.4" stroke-opacity="0.45" stroke-dasharray="10 8">
    <animate attributeName="d" values="{";".join(ring2_paths)}" dur="11s" repeatCount="indefinite"/>
  </path>

  <!-- True 3D Projected Rotating Geodesic Icosahedron Wireframe -->
  <path fill="none" stroke="#22d3ee" stroke-width="1.85" stroke-opacity="0.88" stroke-linejoin="round" filter="url(#neonGlow)">
    <animate attributeName="d" values="{";".join(outer_paths)}" dur="11s" repeatCount="indefinite"/>
  </path>

  <!-- True 3D Counter-Rotating Inner Octahedron Core -->
  <path fill="none" stroke="#39d353" stroke-width="2.2" stroke-opacity="0.95" stroke-linejoin="round" filter="url(#neonGlow)">
    <animate attributeName="d" values="{";".join(inner_paths)}" dur="8s" repeatCount="indefinite"/>
  </path>

  <!-- Glowing Energy Singularity Center -->
  <circle cx="{cx}" cy="{cy}" r="24" fill="#071526" stroke="url(#cyberAccent)" stroke-width="2" filter="url(#neonGlow)">
    <animate attributeName="r" values="21;27;21" dur="2.6s" repeatCount="indefinite"/>
  </circle>
  <text x="{cx}" y="{cy + 5}" text-anchor="middle" fill="#f8fafc" font-family="ui-monospace,SFMono-Regular,JetBrains Mono,monospace" font-size="14" font-weight="800" letter-spacing="1.5">3D·OS</text>

  <!-- Floating 3D Telemetry Callout Badges Around Core -->
  <g transform="translate(770, 56)">
    <rect width="142" height="32" rx="8" fill="#0b1324" fill-opacity="0.9" stroke="#39d353" stroke-opacity="0.5"/>
    <circle cx="15" cy="16" r="4" fill="#39d353"><animate attributeName="opacity" values="1;0.2;1" dur="1.4s" repeatCount="indefinite"/></circle>
    <text x="27" y="20" fill="#d1fae5" font-family="ui-monospace,SFMono-Regular,monospace" font-size="11" font-weight="700">5,107+ COMMITS</text>
  </g>
  <g transform="translate(1038, 62)">
    <rect width="134" height="32" rx="8" fill="#0b1324" fill-opacity="0.9" stroke="#22d3ee" stroke-opacity="0.5"/>
    <text x="14" y="20" fill="#cffafe" font-family="ui-monospace,SFMono-Regular,monospace" font-size="11" font-weight="700">124 REPOS SHIP</text>
  </g>
  <g transform="translate(765, 382)">
    <rect width="152" height="32" rx="8" fill="#0b1324" fill-opacity="0.9" stroke="#a78bfa" stroke-opacity="0.5"/>
    <text x="14" y="20" fill="#ede9fe" font-family="ui-monospace,SFMono-Regular,monospace" font-size="11" font-weight="700">57 PRISMA MODELS</text>
  </g>
  <g transform="translate(1022, 382)">
    <rect width="150" height="32" rx="8" fill="#0b1324" fill-opacity="0.9" stroke="#f59e0b" stroke-opacity="0.5"/>
    <text x="14" y="20" fill="#fef3c7" font-family="ui-monospace,SFMono-Regular,monospace" font-size="11" font-weight="700">0ms LAN OFFLINE</text>
  </g>
</g>

<!-- LEFT SIDE: Identity, Role & Live Metric Matrix -->
<g font-family="Inter,ui-sans-serif,system-ui,-apple-system,Segoe UI,sans-serif">
  <!-- Status Pill -->
  <g transform="translate(48, 36)">
    <rect width="382" height="32" rx="16" fill="#091526" stroke="#39d353" stroke-opacity="0.45"/>
    <circle cx="18" cy="16" r="5" fill="#39d353" filter="url(#neonGlow)">
      <animate attributeName="opacity" values="1;0.25;1" dur="1.2s" repeatCount="indefinite"/>
    </circle>
    <text x="32" y="20" fill="#86efac" font-family="ui-monospace,SFMono-Regular,monospace" font-size="11.5" font-weight="700" letter-spacing="1.3">FOUNDING ENGINEER @ GTSS  ·  KENYA (NBO / ELD)</text>
  </g>

  <!-- Main Name & Animated Gradient Bar -->
  <text x="48" y="128" fill="url(#titleGrad)" font-size="52" font-weight="900" letter-spacing="-1.5">ELVIN OMONDI JUMA</text>
  <rect x="48" y="144" width="640" height="4" rx="2" fill="url(#cyberAccent)" filter="url(#neonGlow)">
    <animate attributeName="width" values="180;660;520;660" dur="6s" repeatCount="indefinite"/>
  </rect>

  <!-- Headline -->
  <text x="48" y="186" fill="#22d3ee" font-family="ui-monospace,SFMono-Regular,monospace" font-size="16" font-weight="800" letter-spacing="2.4">FULL-STACK PRODUCT ARCHITECT  //  SYSTEMS ENGINEER</text>
  <text x="48" y="218" fill="#cbd5e1" font-size="17" font-weight="500">Architecting multi-tenant SaaS, offline-first POS &amp; real-time financial ecosystems.</text>

  <!-- 4 High-Impact 3D Metric Cards -->
  <g transform="translate(48, 248)">
    <!-- Metric 1 -->
    <g transform="translate(0, 0)">
      <rect width="162" height="92" rx="12" fill="url(#cardGrad)" stroke="#39d353" stroke-opacity="0.45"/>
      <path d="M12 1 L150 1" stroke="#39d353" stroke-width="2"/>
      <text x="18" y="38" fill="#39d353" font-family="ui-monospace,SFMono-Regular,monospace" font-size="28" font-weight="900">5,100+</text>
      <text x="18" y="60" fill="#f8fafc" font-size="11.5" font-weight="700" letter-spacing="0.8">CONTRIBUTIONS</text>
      <text x="18" y="78" fill="#64748b" font-family="ui-monospace,SFMono-Regular,monospace" font-size="10">+310% YoY velocity</text>
    </g>
    <!-- Metric 2 -->
    <g transform="translate(176, 0)">
      <rect width="162" height="92" rx="12" fill="url(#cardGrad)" stroke="#22d3ee" stroke-opacity="0.45"/>
      <path d="M12 1 L150 1" stroke="#22d3ee" stroke-width="2"/>
      <text x="18" y="38" fill="#22d3ee" font-family="ui-monospace,SFMono-Regular,monospace" font-size="28" font-weight="900">124</text>
      <text x="84" y="34" fill="#0891b2" font-family="ui-monospace,SFMono-Regular,monospace" font-size="12" font-weight="800">REPOS</text>
      <text x="18" y="60" fill="#f8fafc" font-size="11.5" font-weight="700" letter-spacing="0.8">116+ OPEN SOURCE</text>
      <text x="18" y="78" fill="#64748b" font-family="ui-monospace,SFMono-Regular,monospace" font-size="10">80+ Cloud Deploys</text>
    </g>
    <!-- Metric 3 -->
    <g transform="translate(352, 0)">
      <rect width="162" height="92" rx="12" fill="url(#cardGrad)" stroke="#a78bfa" stroke-opacity="0.45"/>
      <path d="M12 1 L150 1" stroke="#a78bfa" stroke-width="2"/>
      <text x="18" y="38" fill="#a78bfa" font-family="ui-monospace,SFMono-Regular,monospace" font-size="28" font-weight="900">6 LIVE</text>
      <text x="18" y="60" fill="#f8fafc" font-size="11.5" font-weight="700" letter-spacing="0.8">SAAS PLATFORMS</text>
      <text x="18" y="78" fill="#64748b" font-family="ui-monospace,SFMono-Regular,monospace" font-size="10">Health · POS · FinTech</text>
    </g>
    <!-- Metric 4 -->
    <g transform="translate(528, 0)">
      <rect width="162" height="92" rx="12" fill="url(#cardGrad)" stroke="#f59e0b" stroke-opacity="0.45"/>
      <path d="M12 1 L150 1" stroke="#f59e0b" stroke-width="2"/>
      <text x="18" y="38" fill="#f59e0b" font-family="ui-monospace,SFMono-Regular,monospace" font-size="28" font-weight="900">99.98%</text>
      <text x="18" y="60" fill="#f8fafc" font-size="11.5" font-weight="700" letter-spacing="0.8">UPTIME &amp; SLA</text>
      <text x="18" y="78" fill="#64748b" font-family="ui-monospace,SFMono-Regular,monospace" font-size="10">Offline-First + Cloud</text>
    </g>
  </g>

  <!-- Tech Pill Strip -->
  <g transform="translate(48, 366)" font-family="ui-monospace,SFMono-Regular,monospace" font-size="11.5" font-weight="700">
    <rect x="0" y="0" width="108" height="28" rx="6" fill="#0d1b2a" stroke="#38bdf8" stroke-opacity="0.35"/>
    <text x="54" y="18" text-anchor="middle" fill="#7dd3fc">NEXT.JS 16</text>

    <rect x="118" y="0" width="108" height="28" rx="6" fill="#0d1b2a" stroke="#22d3ee" stroke-opacity="0.35"/>
    <text x="172" y="18" text-anchor="middle" fill="#67e8f9">TYPESCRIPT</text>

    <rect x="236" y="0" width="124" height="28" rx="6" fill="#0d1b2a" stroke="#39d353" stroke-opacity="0.35"/>
    <text x="298" y="18" text-anchor="middle" fill="#86efac">PRISMA + PGSQL</text>

    <rect x="370" y="0" width="108" height="28" rx="6" fill="#0d1b2a" stroke="#a78bfa" stroke-opacity="0.35"/>
    <text x="424" y="18" text-anchor="middle" fill="#c4b5fd">SOCKET.IO</text>

    <rect x="488" y="0" width="118" height="28" rx="6" fill="#0d1b2a" stroke="#f59e0b" stroke-opacity="0.35"/>
    <text x="547" y="18" text-anchor="middle" fill="#fcd34d">M-PESA DARAJA</text>
  </g>

  <text x="48" y="452" fill="#64748b" font-family="ui-monospace,SFMono-Regular,monospace" font-size="11" letter-spacing="1.6">
    MOI UNIVERSITY (CS)  //  GREAT THUMBS SOFTWARE SOLUTIONS  //  PRODUCTION TELEMETRY ACTIVE
  </text>
</g>

<!-- Outer Neon Frame -->
<rect x="1" y="1" width="1198" height="483" rx="21" fill="none" stroke="url(#cyberAccent)" stroke-opacity="0.35" stroke-width="1.5"/>
</svg>
'''
    (ASSETS / "hero-3d.svg").write_text(svg, encoding="utf-8")
    print("hero-3d.svg generated.")


# ---------------------------------------------------------------------------
# 2. TELEMETRY-3D.SVG: 60fps 3D Isometric Engineering Metrics & Velocity HUD
# ---------------------------------------------------------------------------

def generate_telemetry_3d_svg() -> None:
    # 3D Isometric bar chart for contribution growth & domain velocity
    bars_data = [
        ("2024", 18, "#1e293b", "#0f172a", "#090d16", "#38bdf8"),
        ("Q1'25", 42, "#0e4429", "#092e1c", "#051b10", "#26a641"),
        ("Q3'25", 68, "#006d32", "#0e4429", "#082918", "#39d353"),
        ("Q1'26", 104, "#26a641", "#006d32", "#0e4429", "#39d353"),
        ("Q3'26", 132, "#39d353", "#26a641", "#006d32", "#86efac"),
        ("NOW", 156, "#22d3ee", "#0284c7", "#0369a1", "#67e8f9"),
    ]
    iso_bars = []
    for i, (lbl, h, tc, lc, rc, sc) in enumerate(bars_data):
        bx = 92 + i * 44
        by = 248
        cube = svg_3d_cube_faces(bx, by, 28, 13, h, tc, lc, rc, sc, 0.65)
        iso_bars.append(
            f'<g>{cube}'
            f'<text x="{bx}" y="{by - h - 12}" text-anchor="middle" fill="{sc}" font-family="ui-monospace,monospace" font-size="9.5" font-weight="700">{lbl}</text>'
            f'</g>'
        )

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="310" viewBox="0 0 1200 310" role="img" aria-label="3D Engineering Telemetry and System Scale Metrics">
<defs>
  <linearGradient id="tBg" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0%" stop-color="#060a14"/>
    <stop offset="100%" stop-color="#0a1122"/>
  </linearGradient>
  <linearGradient id="tAccent" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0%" stop-color="#39d353"/>
    <stop offset="50%" stop-color="#22d3ee"/>
    <stop offset="100%" stop-color="#a78bfa"/>
  </linearGradient>
  <filter id="tGlow" x="-20%" y="-20%" width="140%" height="140%">
    <feGaussianBlur stdDeviation="3.5" result="b"/>
    <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
</defs>

<rect width="1200" height="310" rx="20" fill="url(#tBg)" stroke="#1e293b" stroke-width="1.5"/>

<!-- Header Bar -->
<g font-family="ui-monospace,SFMono-Regular,JetBrains Mono,monospace" font-size="11.5" font-weight="800" letter-spacing="1.6">
  <circle cx="36" cy="28" r="4.5" fill="#39d353" filter="url(#tGlow)">
    <animate attributeName="opacity" values="1;0.2;1" dur="1.4s" repeatCount="indefinite"/>
  </circle>
  <text x="50" y="32" fill="#94a3b8">ENGINEERING TELEMETRY  //  VERIFIED PRODUCTION METRICS (2024–2026)</text>
  <text x="1164" y="32" text-anchor="end" fill="#39d353">STATUS: OPTIMAL · 60FPS</text>
</g>
<line x1="28" y1="48" x2="1172" y2="48" stroke="#1e293b"/>

<!-- PANEL 1: 3D Isometric Contribution Velocity (x=28..370) -->
<g transform="translate(28, 62)">
  <rect width="352" height="224" rx="14" fill="#09101f" stroke="#39d353" stroke-opacity="0.32"/>
  <text x="20" y="28" fill="#86efac" font-family="ui-monospace,monospace" font-size="11" font-weight="800" letter-spacing="1.2">01 // COMMIT &amp; SHIP VELOCITY</text>
  <text x="332" y="28" text-anchor="end" fill="#39d353" font-family="ui-monospace,monospace" font-size="13" font-weight="900">5,107 TOTAL</text>
  {"".join(iso_bars)}
  <text x="20" y="210" fill="#64748b" font-family="ui-monospace,monospace" font-size="10.5">2024: 21  →  2025: 998  →  2026: 4,088+ (+310%)</text>
</g>

<!-- PANEL 2: Flagship Healthcare OS Scale (x=396..784) -->
<g transform="translate(396, 62)">
  <rect width="388" height="224" rx="14" fill="#09101f" stroke="#22d3ee" stroke-opacity="0.32"/>
  <text x="20" y="28" fill="#67e8f9" font-family="ui-monospace,monospace" font-size="11" font-weight="800" letter-spacing="1.2">02 // DEEP SYSTEM COMPLEXITY (BENCHMARKS)</text>

  <!-- 4 Metric Progress Rows -->
  <g transform="translate(20, 48)" font-family="ui-monospace,monospace">
    <text x="0" y="14" fill="#e2e8f0" font-size="11.5" font-weight="700">Afyvia / PharmaCare OS</text>
    <text x="348" y="14" text-anchor="end" fill="#22d3ee" font-size="11.5" font-weight="800">57 Models · 308 Routes</text>
    <rect x="0" y="22" width="348" height="7" rx="3.5" fill="#1e293b"/>
    <rect x="0" y="22" width="330" height="7" rx="3.5" fill="url(#tAccent)" filter="url(#tGlow)">
      <animate attributeName="width" values="240;330;310;330" dur="5s" repeatCount="indefinite"/>
    </rect>

    <g transform="translate(0, 44)">
      <text x="0" y="14" fill="#e2e8f0" font-size="11.5" font-weight="700">Restaurant Manager POS (LAN)</text>
      <text x="348" y="14" text-anchor="end" fill="#39d353" font-size="11.5" font-weight="800">39 Screens · 5 Roles</text>
      <rect x="0" y="22" width="348" height="7" rx="3.5" fill="#1e293b"/>
      <rect x="0" y="22" width="308" height="7" rx="3.5" fill="#39d353" filter="url(#tGlow)">
        <animate attributeName="width" values="210;308;290;308" dur="5.6s" repeatCount="indefinite"/>
      </rect>
    </g>

    <g transform="translate(0, 88)">
      <text x="0" y="14" fill="#e2e8f0" font-size="11.5" font-weight="700">JustInTime Gig Marketplace</text>
      <text x="348" y="14" text-anchor="end" fill="#a78bfa" font-size="11.5" font-weight="800">Real-Time Socket + M-Pesa</text>
      <rect x="0" y="22" width="348" height="7" rx="3.5" fill="#1e293b"/>
      <rect x="0" y="22" width="295" height="7" rx="3.5" fill="#a78bfa" filter="url(#tGlow)">
        <animate attributeName="width" values="200;295;275;295" dur="4.8s" repeatCount="indefinite"/>
      </rect>
    </g>

    <g transform="translate(0, 132)">
      <text x="0" y="14" fill="#e2e8f0" font-size="11.5" font-weight="700">Concept Builders + Kampus + GVS</text>
      <text x="348" y="14" text-anchor="end" fill="#f59e0b" font-size="11.5" font-weight="800">65MB+ Production Code</text>
      <rect x="0" y="22" width="348" height="7" rx="3.5" fill="#1e293b"/>
      <rect x="0" y="22" width="320" height="7" rx="3.5" fill="#f59e0b" filter="url(#tGlow)">
        <animate attributeName="width" values="230;320;300;320" dur="6.2s" repeatCount="indefinite"/>
      </rect>
    </g>
  </g>
</g>

<!-- PANEL 3: 3D Orbital Language & Architecture Distribution (x=800..1172) -->
<g transform="translate(800, 62)">
  <rect width="372" height="224" rx="14" fill="#09101f" stroke="#a78bfa" stroke-opacity="0.32"/>
  <text x="20" y="28" fill="#ddd6fe" font-family="ui-monospace,monospace" font-size="11" font-weight="800" letter-spacing="1.2">03 // CODEBASE &amp; INFRASTRUCTURE</text>

  <!-- Animated Holographic Ring Gauge -->
  <g transform="translate(96, 128)">
    <circle r="62" fill="none" stroke="#1e293b" stroke-width="12"/>
    <circle r="62" fill="none" stroke="#22d3ee" stroke-width="12" stroke-dasharray="310 390" stroke-linecap="round" filter="url(#tGlow)">
      <animateTransform attributeName="transform" type="rotate" from="0" to="360" dur="14s" repeatCount="indefinite"/>
    </circle>
    <circle r="44" fill="none" stroke="#39d353" stroke-width="6" stroke-dasharray="180 280" stroke-linecap="round">
      <animateTransform attributeName="transform" type="rotate" from="360" to="0" dur="9s" repeatCount="indefinite"/>
    </circle>
    <text text-anchor="middle" y="4" fill="#f8fafc" font-family="ui-monospace,monospace" font-size="18" font-weight="900">92%</text>
    <text text-anchor="middle" y="19" fill="#67e8f9" font-family="ui-monospace,monospace" font-size="8.5" font-weight="700">TYPESCRIPT</text>
  </g>

  <!-- Right Legend -->
  <g transform="translate(182, 62)" font-family="ui-monospace,monospace" font-size="11">
    <circle cx="8" cy="10" r="4" fill="#22d3ee"/>
    <text x="20" y="14" fill="#f8fafc" font-weight="700">TypeScript / Next</text>
    <text x="170" y="14" text-anchor="end" fill="#22d3ee" font-weight="800">94 Repos</text>

    <circle cx="8" cy="42" r="4" fill="#39d353"/>
    <text x="20" y="46" fill="#f8fafc" font-weight="700">Node / Socket.IO</text>
    <text x="170" y="46" text-anchor="end" fill="#39d353" font-weight="800">18 Repos</text>

    <circle cx="8" cy="74" r="4" fill="#a78bfa"/>
    <text x="20" y="78" fill="#f8fafc" font-weight="700">Prisma + Postgres</text>
    <text x="170" y="78" text-anchor="end" fill="#a78bfa" font-weight="800">150+ Tbls</text>

    <circle cx="8" cy="106" r="4" fill="#f59e0b"/>
    <text x="20" y="110" fill="#f8fafc" font-weight="700">M-Pesa / FinTech</text>
    <text x="170" y="110" text-anchor="end" fill="#f59e0b" font-weight="800">12 Live</text>

    <circle cx="8" cy="138" r="4" fill="#f43f5e"/>
    <text x="20" y="142" fill="#f8fafc" font-weight="700">Expo / Electron</text>
    <text x="170" y="142" text-anchor="end" fill="#f43f5e" font-weight="800">Cross-OS</text>
  </g>
</g>
</svg>
'''
    (ASSETS / "telemetry-3d.svg").write_text(svg, encoding="utf-8")
    print("telemetry-3d.svg generated.")


# ---------------------------------------------------------------------------
# 3. PROJECT-CONSTELLATION-3D.SVG: 60fps 3D Isometric Production Ecosystem
# ---------------------------------------------------------------------------

def generate_constellation_3d_svg() -> None:
    nodes = [
        (210, 118, "01 // AFYVIA · PHARMACARE OS", "57 Prisma Models · 4 Portals · FEFO + AI Triage", "afyvia.gtss.software", "#39d353"),
        (990, 118, "02 // JUSTINTIME MARKETPLACE", "Geo-Match · Socket.IO Proposals · M-Pesa Escrow", "justintime.gtss.software", "#22d3ee"),
        (170, 260, "03 // RESTAURANT MANAGER POS", "39 Screens · 5 Roles · 0ms LAN Offline-First KDS", "hotel-intranet (LAN + Cloud)", "#f59e0b"),
        (1030, 260, "04 // KAMPUS &amp; MOI MASHINANI", "React Native · Expo · Campus P2P Marketplace", "moimashinani.gtss.software", "#a78bfa"),
        (230, 392, "05 // CONCEPT BUILDERS", "33MB CAD/3D Plan Store · Live Client Sockets", "conceptbuilders.co.ke", "#38bdf8"),
        (970, 392, "06 // GERMAN VIRTUAL SCHOOL", "CEFR A1–C2 Live Cohorts · Real-Time Class Sync", "germanvirtualschool.com", "#f43f5e"),
    ]

    cx, cy = 600, 250
    conduits = []
    cards = []

    for idx, (nx, ny, title, metrics, url, color) in enumerate(nodes):
        # Curved 3D Bezier Conduit from center reactor to node
        ctrl_x = (cx + nx) * 0.5
        ctrl_y = cy + (ny - cy) * 0.25
        path_id = f"conduit{idx}"
        d_str = f"M{cx},{cy} Q{ctrl_x:.1f},{ctrl_y:.1f} {nx},{ny}"
        conduits.append(
            f'<path id="{path_id}" d="{d_str}" fill="none" stroke="{color}" stroke-width="1.8" stroke-opacity="0.32" stroke-dasharray="6 8"/>'
            f'<circle r="4" fill="{color}" filter="url(#cGlow)">'
            f'<animateMotion dur="{2.6 + idx * 0.35:.2f}s" repeatCount="indefinite"><mpath href="#{path_id}"/></animateMotion>'
            f'</circle>'
            f'<circle r="3" fill="#ffffff">'
            f'<animateMotion dur="{2.6 + idx * 0.35:.2f}s" begin="-1.3s" repeatCount="indefinite"><mpath href="#{path_id}"/></animateMotion>'
            f'</circle>'
        )

        # Node Card with 3D Isometric Pedestal Cube
        card_w, card_h = 328, 86
        card_x = nx - card_w // 2
        card_y = ny - card_h // 2
        cube_x = card_x + 28
        cube_y = card_y + 54
        cube = svg_3d_cube_faces(cube_x, cube_y, 26, 12, 18, color, "#0f172a", "#1e293b", color, 0.8)

        cards.append(f'''
        <g>
          <rect x="{card_x}" y="{card_y}" width="{card_w}" height="{card_h}" rx="12" fill="#091121" fill-opacity="0.94" stroke="{color}" stroke-opacity="0.55" stroke-width="1.4"/>
          {cube}
          <text x="{card_x + 54}" y="{card_y + 28}" fill="{color}" font-family="ui-monospace,SFMono-Regular,monospace" font-size="11.5" font-weight="800" letter-spacing="0.8">{title}</text>
          <text x="{card_x + 54}" y="{card_y + 49}" fill="#f1f5f9" font-family="Inter,ui-sans-serif,sans-serif" font-size="11.5" font-weight="600">{metrics}</text>
          <text x="{card_x + 54}" y="{card_y + 69}" fill="#64748b" font-family="ui-monospace,SFMono-Regular,monospace" font-size="10.5">↗ {url}</text>
        </g>''')

    # Central 3D Isometric Multi-Layer Core
    center_cubes = (
        svg_3d_cube_faces(cx, cy + 36, 130, 62, 16, "#0f172a", "#090d16", "#050811", "#38bdf8", 0.5)
        + svg_3d_cube_faces(cx, cy + 12, 104, 50, 16, "#0e4429", "#006d32", "#092e1c", "#39d353", 0.7)
        + svg_3d_cube_faces(cx, cy - 12, 78, 38, 18, "#22d3ee", "#0284c7", "#0369a1", "#67e8f9", 0.9)
    )

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="465" viewBox="0 0 1200 465" role="img" aria-label="3D Production Ecosystem Constellation">
<defs>
  <radialGradient id="cBg" cx="0.5" cy="0.54" r="0.65">
    <stop offset="0%" stop-color="#0d1f38"/>
    <stop offset="55%" stop-color="#081020"/>
    <stop offset="100%" stop-color="#050811"/>
  </radialGradient>
  <filter id="cGlow" x="-30%" y="-30%" width="160%" height="160%">
    <feGaussianBlur stdDeviation="4" result="b"/>
    <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
</defs>

<rect width="1200" height="465" rx="20" fill="url(#cBg)" stroke="#1e293b" stroke-width="1.5"/>

<!-- Header -->
<g font-family="ui-monospace,SFMono-Regular,monospace" font-size="11.5" font-weight="800" letter-spacing="1.5">
  <text x="36" y="34" fill="#94a3b8">3D PRODUCTION CONSTELLATION  //  FLAGSHIP MULTI-TENANT &amp; OFFLINE-FIRST ECOSYSTEMS</text>
  <text x="1164" y="34" text-anchor="end" fill="#22d3ee">GTSS CORE ENGINE</text>
</g>
<line x1="28" y1="48" x2="1172" y2="48" stroke="#1e293b"/>

<!-- Central Orbital Radar Rings -->
<g transform="translate({cx}, {cy})" fill="none">
  <ellipse rx="210" ry="115" stroke="#38bdf8" stroke-opacity="0.14" stroke-width="1.2" stroke-dasharray="8 8"/>
  <ellipse rx="150" ry="82" stroke="#39d353" stroke-opacity="0.20" stroke-width="1.2" stroke-dasharray="14 6"/>
  <circle r="118" stroke="#22d3ee" stroke-opacity="0.18" stroke-dasharray="6 12">
    <animateTransform attributeName="transform" type="rotate" from="0" to="360" dur="20s" repeatCount="indefinite"/>
  </circle>
  <circle r="86" stroke="#a78bfa" stroke-opacity="0.25" stroke-dasharray="18 10">
    <animateTransform attributeName="transform" type="rotate" from="360" to="0" dur="12s" repeatCount="indefinite"/>
  </circle>
</g>

<!-- Animated 3D Conduits & Data Packets -->
{"".join(conduits)}

<!-- Central 3D Stacked Isometric Reactor -->
<g filter="url(#cGlow)">
  {center_cubes}
  <animateTransform attributeName="transform" type="translate" values="0,0; 0,-7; 0,0" dur="3.4s" repeatCount="indefinite"/>
</g>
<text x="{cx}" y="{cy + 66}" text-anchor="middle" fill="#f8fafc" font-family="ui-monospace,monospace" font-size="13" font-weight="900" letter-spacing="2">GTSS · NEXUS</text>
<text x="{cx}" y="{cy + 82}" text-anchor="middle" fill="#39d353" font-family="ui-monospace,monospace" font-size="10" font-weight="700">6 LIVE PLATFORMS</text>

<!-- 6 Flagship System Cards -->
{"".join(cards)}
</svg>
'''
    (ASSETS / "project-constellation-3d.svg").write_text(svg, encoding="utf-8")
    print("project-constellation-3d.svg generated.")


# ---------------------------------------------------------------------------
# 4. ARCHITECTURE-3D.SVG: 60fps 3D Isometric Exploded Stack & Execution Loop
# ---------------------------------------------------------------------------

def generate_architecture_3d_svg() -> None:
    def iso_plane(cx: float, cy: float, w: float, h: float, thickness: float, top_fill: str, side_fill: str, stroke: str) -> str:
        hw, hh = w * 0.5, h * 0.5
        top = f"M{cx},{cy - hh} L{cx + hw},{cy} L{cx},{cy + hh} L{cx - hw},{cy} Z"
        left = f"M{cx - hw},{cy} L{cx},{cy + hh} L{cx},{cy + hh + thickness} L{cx - hw},{cy + thickness} Z"
        right = f"M{cx},{cy + hh} L{cx + hw},{cy} L{cx + hw},{cy + thickness} L{cx},{cy + hh + thickness} Z"
        return (
            f'<path d="{left}" fill="{side_fill}" stroke="{stroke}" stroke-opacity="0.5"/>'
            f'<path d="{right}" fill="{side_fill}" stroke="{stroke}" stroke-opacity="0.65"/>'
            f'<path d="{top}" fill="{top_fill}" stroke="{stroke}" stroke-width="1.6"/>'
        )

    px = 285
    p1 = iso_plane(px, 118, 390, 96, 14, "#0c1f38", "#071324", "#22d3ee")
    p2 = iso_plane(px, 212, 390, 96, 14, "#0b2622", "#061715", "#39d353")
    p3 = iso_plane(px, 306, 390, 96, 14, "#191536", "#0e0b20", "#a78bfa")

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="390" viewBox="0 0 1200 390" role="img" aria-label="3D Exploded Isometric Architecture and Execution Pipeline">
<defs>
  <linearGradient id="aBg" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0%" stop-color="#050811"/>
    <stop offset="100%" stop-color="#0a1224"/>
  </linearGradient>
  <filter id="aGlow" x="-25%" y="-25%" width="150%" height="150%">
    <feGaussianBlur stdDeviation="3.5" result="b"/>
    <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
</defs>

<rect width="1200" height="390" rx="20" fill="url(#aBg)" stroke="#1e293b" stroke-width="1.5"/>

<!-- Header -->
<g font-family="ui-monospace,SFMono-Regular,monospace" font-size="11.5" font-weight="800" letter-spacing="1.5">
  <text x="36" y="34" fill="#94a3b8">3D ISOMETRIC SYSTEM ARCHITECTURE  //  FULL-STACK EXECUTION TOPOLOGY</text>
  <text x="1164" y="34" text-anchor="end" fill="#a78bfa">ZERO-SINGLE-POINT-OF-FAILURE</text>
</g>
<line x1="28" y1="48" x2="1172" y2="48" stroke="#1e293b"/>

<!-- LEFT: 3D Exploded Isometric 3-Layer Stack -->
<g>
  <!-- Vertical Laser Conduits Connecting Isometric Layers -->
  <g stroke="#38bdf8" stroke-opacity="0.35" stroke-width="1.4" stroke-dasharray="4 6">
    <line x1="150" y1="118" x2="150" y2="306"/>
    <line x1="285" y1="70" x2="285" y2="354"/>
    <line x1="420" y1="118" x2="420" y2="306"/>
  </g>

  <!-- Plane 3 (Bottom): Data & FinTech Core -->
  <g>
    {p3}
    <text x="{px}" y="302" text-anchor="middle" fill="#ddd6fe" font-family="ui-monospace,monospace" font-size="12" font-weight="900">LAYER 03 // DATA &amp; FINTECH CORE</text>
    <text x="{px}" y="321" text-anchor="middle" fill="#a78bfa" font-family="ui-monospace,monospace" font-size="10" font-weight="700">PostgreSQL · 57-Model Prisma · M-Pesa STK · R2</text>
  </g>

  <!-- Plane 2 (Middle): Real-Time & Intelligence Mesh -->
  <g>
    {p2}
    <text x="{px}" y="208" text-anchor="middle" fill="#d1fae5" font-family="ui-monospace,monospace" font-size="12" font-weight="900">LAYER 02 // REAL-TIME &amp; AI MESH</text>
    <text x="{px}" y="227" text-anchor="middle" fill="#39d353" font-family="ui-monospace,monospace" font-size="10" font-weight="700">Socket.IO · Offline LAN Sync · Groq AI · RBAC</text>
  </g>

  <!-- Plane 1 (Top): Edge & Client Surfaces -->
  <g>
    {p1}
    <text x="{px}" y="114" text-anchor="middle" fill="#cffafe" font-family="ui-monospace,monospace" font-size="12" font-weight="900">LAYER 01 // CLIENT &amp; 3D EDGE</text>
    <text x="{px}" y="133" text-anchor="middle" fill="#22d3ee" font-family="ui-monospace,monospace" font-size="10" font-weight="700">Next.js 16 · React 19 · Expo · Electron · WebGL</text>
  </g>

  <!-- Animated Vertical Data Pulses Between 3D Layers -->
  <circle cx="150" r="4" fill="#22d3ee" filter="url(#aGlow)">
    <animate attributeName="cy" values="118;306;118" dur="3.2s" repeatCount="indefinite"/>
  </circle>
  <circle cx="285" r="4.5" fill="#39d353" filter="url(#aGlow)">
    <animate attributeName="cy" values="354;70;354" dur="2.8s" repeatCount="indefinite"/>
  </circle>
  <circle cx="420" r="4" fill="#a78bfa" filter="url(#aGlow)">
    <animate attributeName="cy" values="118;306;118" dur="3.6s" begin="-1.4s" repeatCount="indefinite"/>
  </circle>
</g>

<!-- RIGHT: 4-Stage Engineering & Production Loop (x=540..1168) -->
<g transform="translate(540, 68)">
  <!-- Stage 01 -->
  <g transform="translate(0, 0)">
    <rect width="300" height="138" rx="14" fill="#091121" stroke="#39d353" stroke-opacity="0.45"/>
    <text x="20" y="30" fill="#39d353" font-family="ui-monospace,monospace" font-size="12" font-weight="900">01 // WORKFLOW DECONSTRUCTION</text>
    <text x="20" y="56" fill="#f8fafc" font-family="Inter,sans-serif" font-size="14" font-weight="700">Map real operational bottlenecks</text>
    <text x="20" y="78" fill="#94a3b8" font-family="Inter,sans-serif" font-size="11.5">Pharmacist queues, kitchen tickets, M-Pesa</text>
    <text x="20" y="96" fill="#94a3b8" font-family="Inter,sans-serif" font-size="11.5">callbacks &amp; multi-tenant permissions.</text>
    <text x="20" y="122" fill="#86efac" font-family="ui-monospace,monospace" font-size="10.5" font-weight="700">✓ 100% Domain-First Schema Design</text>
  </g>

  <!-- Stage 02 -->
  <g transform="translate(320, 0)">
    <rect width="308" height="138" rx="14" fill="#091121" stroke="#22d3ee" stroke-opacity="0.45"/>
    <text x="20" y="30" fill="#22d3ee" font-family="ui-monospace,monospace" font-size="12" font-weight="900">02 // TYPE-SAFE CORE &amp; RBAC</text>
    <text x="20" y="56" fill="#f8fafc" font-family="Inter,sans-serif" font-size="14" font-weight="700">End-to-end strict contracts</text>
    <text x="20" y="78" fill="#94a3b8" font-family="Inter,sans-serif" font-size="11.5">Prisma + PostgreSQL + Zod + Server Actions</text>
    <text x="20" y="96" fill="#94a3b8" font-family="Inter,sans-serif" font-size="11.5">with strict tenant &amp; role isolation.</text>
    <text x="20" y="122" fill="#67e8f9" font-family="ui-monospace,monospace" font-size="10.5" font-weight="700">✓ 150+ Production DB Models Shipped</text>
  </g>

  <!-- Stage 03 -->
  <g transform="translate(0, 156)">
    <rect width="300" height="138" rx="14" fill="#091121" stroke="#f59e0b" stroke-opacity="0.45"/>
    <text x="20" y="30" fill="#f59e0b" font-family="ui-monospace,monospace" font-size="12" font-weight="900">03 // OFFLINE &amp; FAILURE RESILIENCE</text>
    <text x="20" y="56" fill="#f8fafc" font-family="Inter,sans-serif" font-size="14" font-weight="700">Survives zero-internet &amp; retries</text>
    <text x="20" y="78" fill="#94a3b8" font-family="Inter,sans-serif" font-size="11.5">Local-network Socket.IO rooms, idempotent</text>
    <text x="20" y="96" fill="#94a3b8" font-family="Inter,sans-serif" font-size="11.5">webhook reconciliation &amp; state recovery.</text>
    <text x="20" y="122" fill="#fcd34d" font-family="ui-monospace,monospace" font-size="10.5" font-weight="700">✓ 0ms Cloud Dependency on LAN POS</text>
  </g>

  <!-- Stage 04 -->
  <g transform="translate(320, 156)">
    <rect width="308" height="138" rx="14" fill="#091121" stroke="#a78bfa" stroke-opacity="0.45"/>
    <text x="20" y="30" fill="#a78bfa" font-family="ui-monospace,monospace" font-size="12" font-weight="900">04 // AI-ACCELERATED SHIPPING</text>
    <text x="20" y="56" fill="#f8fafc" font-family="Inter,sans-serif" font-size="14" font-weight="700">High-velocity autonomous delivery</text>
    <text x="20" y="78" fill="#94a3b8" font-family="Inter,sans-serif" font-size="11.5">Agentic workflows + embedded AI features</text>
    <text x="20" y="96" fill="#94a3b8" font-family="Inter,sans-serif" font-size="11.5">(Groq symptom triage, OCR/vision, CRM bots).</text>
    <text x="20" y="122" fill="#ddd6fe" font-family="ui-monospace,monospace" font-size="10.5" font-weight="700">✓ 80+ Production Deployments Live</text>
  </g>
</g>
</svg>
'''
    (ASSETS / "architecture-3d.svg").write_text(svg, encoding="utf-8")
    print("architecture-3d.svg generated.")


# ---------------------------------------------------------------------------
# 5. FOOTER.SVG: 60fps 3D Perspective Synth-Grid Horizon Signature
# ---------------------------------------------------------------------------

def generate_footer_svg() -> None:
    svg = '''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="130" viewBox="0 0 1200 130" role="img" aria-label="Engineered in Kenya. Built for real-world scale.">
<defs>
  <linearGradient id="fBg" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0%" stop-color="#050811"/>
    <stop offset="50%" stop-color="#091326"/>
    <stop offset="100%" stop-color="#050811"/>
  </linearGradient>
  <linearGradient id="fLine" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0%" stop-color="#39d353" stop-opacity="0"/>
    <stop offset="25%" stop-color="#39d353"/>
    <stop offset="50%" stop-color="#22d3ee"/>
    <stop offset="75%" stop-color="#a78bfa"/>
    <stop offset="100%" stop-color="#a78bfa" stop-opacity="0"/>
  </linearGradient>
</defs>

<rect width="1200" height="130" rx="18" fill="url(#fBg)" stroke="#1e293b" stroke-width="1.5"/>

<!-- 3D Perspective Horizon Grid -->
<g stroke="#22d3ee" stroke-opacity="0.14" stroke-width="1">
  <line x1="0" y1="82" x2="1200" y2="82"/>
  <line x1="0" y1="98" x2="1200" y2="98"/>
  <line x1="0" y1="116" x2="1200" y2="116"/>
  <line x1="600" y1="20" x2="80" y2="130"/>
  <line x1="600" y1="20" x2="260" y2="130"/>
  <line x1="600" y1="20" x2="430" y2="130"/>
  <line x1="600" y1="20" x2="600" y2="130"/>
  <line x1="600" y1="20" x2="770" y2="130"/>
  <line x1="600" y1="20" x2="940" y2="130"/>
  <line x1="600" y1="20" x2="1120" y2="130"/>
</g>

<path d="M40 2 H1160" stroke="url(#fLine)" stroke-width="2"/>
<circle r="4" cy="2" fill="#22d3ee">
  <animate attributeName="cx" values="80;1120;80" dur="6s" repeatCount="indefinite"/>
</circle>

<text x="600" y="54" text-anchor="middle" fill="#f8fafc" font-family="Inter,ui-sans-serif,system-ui,sans-serif" font-size="22" font-weight="800" letter-spacing="0.5">
  ENGINEERED IN KENYA  ·  <tspan fill="#39d353">SHIPPED TO PRODUCTION</tspan>  ·  <tspan fill="#22d3ee">BUILT FOR SCALE</tspan>
</text>
<text x="600" y="84" text-anchor="middle" fill="#94a3b8" font-family="ui-monospace,SFMono-Regular,monospace" font-size="11.5" font-weight="700" letter-spacing="2">
  ELVIN OMONDI JUMA  //  FOUNDING ENGINEER @ GTSS  //  5,100+ CONTRIBUTIONS  //  124 REPOSITORIES
</text>
</svg>
'''
    (ASSETS / "footer.svg").write_text(svg, encoding="utf-8")
    print("footer.svg generated.")


# ---------------------------------------------------------------------------
# 6. TRUE 3D SOFTWARE-RENDERED GIFS + PNG FALLBACKS (profile-hero & build-loop)
# ---------------------------------------------------------------------------

class Canvas3D:
    def __init__(self, width: int, height: int):
        self.width, self.height = width, height
        self.image = Image.new("RGB", (width * SCALE, height * SCALE), BG)
        self.draw = ImageDraw.Draw(self.image, "RGBA")

    def rect(self, box, fill=None, radius=0, outline=None, width=1):
        scaled = tuple(round(v * SCALE) for v in box)
        if radius:
            self.draw.rounded_rectangle(
                scaled, radius=round(radius * SCALE), fill=fill,
                outline=outline, width=max(1, round(width * SCALE)),
            )
        else:
            self.draw.rectangle(scaled, fill=fill, outline=outline, width=max(1, round(width * SCALE)))

    def polygon(self, pts, fill=None, outline=None):
        spts = [(round(x * SCALE), round(y * SCALE)) for x, y in pts]
        self.draw.polygon(spts, fill=fill, outline=outline)

    def line(self, pts, fill=BORDER, width=1):
        spts = [(round(x * SCALE), round(y * SCALE)) for x, y in pts]
        self.draw.line(spts, fill=fill, width=max(1, round(width * SCALE)))

    def circle(self, cx: float, cy: float, r: float, fill=None, outline=None, width=1):
        box = (
            round((cx - r) * SCALE), round((cy - r) * SCALE),
            round((cx + r) * SCALE), round((cy + r) * SCALE),
        )
        self.draw.ellipse(box, fill=fill, outline=outline, width=max(1, round(width * SCALE)))

    def text(self, pos, value: str, size: int, color=TEXT, style="regular", anchor="lt"):
        key = (style, size)
        if key not in FONTS:
            FONTS[key] = ImageFont.truetype(str(FONT_PATHS[style]), round(size * SCALE))
        f = FONTS[key]
        self.draw.text((round(pos[0] * SCALE), round(pos[1] * SCALE)), value, fill=color, font=f, anchor=anchor)

    def iso_prism(self, cx: float, cy: float, w: float, h: float, depth: float, top_c, left_c, right_c, outline=None):
        hw, hh = w * 0.5, h * 0.5
        top = [(cx, cy - depth - hh), (cx + hw, cy - depth), (cx, cy - depth + hh), (cx - hw, cy - depth)]
        left = [(cx - hw, cy - depth), (cx, cy - depth + hh), (cx, cy + hh), (cx - hw, cy)]
        right = [(cx, cy - depth + hh), (cx + hw, cy - depth), (cx + hw, cy), (cx, cy + hh)]
        self.polygon(left, fill=left_c, outline=outline)
        self.polygon(right, fill=right_c, outline=outline)
        self.polygon(top, fill=top_c, outline=outline)

    def finish(self) -> Image.Image:
        return self.image.resize((self.width, self.height), Image.Resampling.LANCZOS)


def render_3d_core(c: Canvas3D, cx: float, cy: float, phase: float, radius_scale: float = 1.0):
    verts, edges, faces = icosahedron_geometry()
    oct_v, oct_e = octahedron_geometry(0.55)
    angle = phase * 2.0 * math.pi

    # Outer orbital rings
    c.circle(cx, cy, 138 * radius_scale, outline=rgba(BLUE, 50), width=1.2)
    c.circle(cx, cy, 108 * radius_scale, outline=rgba(GREEN, 65), width=1.2)

    fov = 260.0 * radius_scale
    pverts = [
        project_3d(*rotate_3d(vx, vy, vz, angle * 0.7 + 0.35, angle, angle * 0.4), cx, cy, fov=fov, dist=3.4)
        for vx, vy, vz in verts
    ]

    # Depth-sorted semi-transparent 3D faces (painter's algorithm)
    face_list = []
    for a, b, d_idx in faces:
        za = (pverts[a][2] + pverts[b][2] + pverts[d_idx][2]) / 3.0
        face_list.append((za, a, b, d_idx))
    face_list.sort(key=lambda item: item[0])

    for za, a, b, d_idx in face_list:
        shade = max(0.0, min(1.0, (za + 1.0) * 0.5))
        col = blend("#08182e", CYAN, shade * 0.45)
        pts = [(pverts[a][0], pverts[a][1]), (pverts[b][0], pverts[b][1]), (pverts[d_idx][0], pverts[d_idx][1])]
        c.polygon(pts, fill=(*col, int(35 + shade * 65)))

    # Depth-sorted 3D edges
    for u, v in edges:
        x1, y1, z1 = pverts[u]
        x2, y2, z2 = pverts[v]
        depth_t = max(0.0, min(1.0, ((z1 + z2) * 0.5 + 1.0) * 0.5))
        ecol = hex_blend("#1e3a5f", CYAN, 0.35 + depth_t * 0.65)
        c.line([(x1, y1), (x2, y2)], fill=ecol, width=1.2 + depth_t * 1.1)

    # Counter-rotating inner octahedron
    ipverts = [
        project_3d(*rotate_3d(vx, vy, vz, -angle, -angle * 1.2, angle * 0.6), cx, cy, fov=fov, dist=3.4)
        for vx, vy, vz in oct_v
    ]
    for u, v in oct_e:
        x1, y1, _ = ipverts[u]
        x2, y2, _ = ipverts[v]
        c.line([(x1, y1), (x2, y2)], fill=GREEN, width=1.8)

    # Glowing vertices
    for x, y, z in pverts:
        if z > -0.2:
            r = 2.2 + (z + 0.2) * 2.0
            c.circle(x, y, r, fill=CYAN if z > 0.3 else GREEN)


def hero_raster(phase: float, mobile: bool = False) -> Image.Image:
    if mobile:
        c = Canvas3D(720, 720)
        c.rect((1, 1, 718, 718), fill=BG, radius=18, outline=BORDER, width=1.5)
        c.rect((40, 32, 430, 62), fill="#09192c", radius=15, outline=rgba(GREEN, 120))
        c.circle(58, 47, 5, fill=GREEN)
        c.text((72, 39), "FOUNDING ENGINEER @ GTSS · KENYA", 12, GREEN, "mono_bold")

        c.text((40, 82), "ELVIN OMONDI JUMA", 36, TEXT, "black")
        c.rect((40, 132, 520, 136), fill=CYAN, radius=2)
        c.text((40, 150), "FULL-STACK ARCHITECT · 3D & DISTRIBUTED SYSTEMS", 13, CYAN, "mono_bold")

        metrics = [
            ("5,100+", "CONTRIBUTIONS", GREEN),
            ("124", "REPOS (116 PUB)", CYAN),
            ("6 LIVE", "SAAS PLATFORMS", VIOLET),
            ("99.98%", "UPTIME / LAN POS", AMBER),
        ]
        for i, (val, lbl, col) in enumerate(metrics):
            mx = 40 + (i % 2) * 324
            my = 188 + (i // 2) * 86
            c.rect((mx, my, mx + 308, my + 74), fill=PANEL, radius=10, outline=rgba(col, 120))
            c.text((mx + 16, my + 12), val, 24, col, "mono_bold")
            c.text((mx + 16, my + 46), lbl, 11, MUTED, "bold")

        render_3d_core(c, 360, 525, phase, radius_scale=0.95)
        c.text((360, 686), "57 PRISMA MODELS  ·  39 POS SCREENS  ·  M-PESA STK", 12, MUTED, "mono", anchor="mt")
    else:
        c = Canvas3D(1200, 430)
        c.rect((1, 1, 1198, 428), fill=BG, radius=18, outline=BORDER, width=1.5)
        c.rect((44, 30, 446, 58), fill="#09192c", radius=14, outline=rgba(GREEN, 120))
        c.circle(62, 44, 5, fill=GREEN)
        c.text((76, 36), "FOUNDING ENGINEER @ GTSS · KENYA (NBO / ELD)", 12, GREEN, "mono_bold")

        c.text((44, 76), "ELVIN OMONDI JUMA", 44, TEXT, "black")
        c.rect((44, 134, 620, 138), fill=CYAN, radius=2)
        c.text((44, 152), "FULL-STACK PRODUCT ARCHITECT  //  3D & OFFLINE-FIRST SYSTEMS", 14, CYAN, "mono_bold")
        c.text((44, 180), "Architecting multi-tenant SaaS, LAN POS & real-time FinTech ecosystems.", 15, MUTED, "medium")

        metrics = [
            ("5,100+", "CONTRIBUTIONS", "+310% YoY", GREEN),
            ("124", "REPOSITORIES", "116+ Public", CYAN),
            ("6 LIVE", "SAAS PLATFORMS", "Multi-Tenant", VIOLET),
            ("99.98%", "UPTIME & SLA", "0ms LAN POS", AMBER),
        ]
        for i, (val, lbl, sub, col) in enumerate(metrics):
            mx = 44 + i * 172
            my = 216
            c.rect((mx, my, mx + 160, my + 92), fill=PANEL, radius=10, outline=rgba(col, 130))
            c.text((mx + 14, my + 12), val, 24, col, "mono_bold")
            c.text((mx + 14, my + 46), lbl, 11, TEXT, "bold")
            c.text((mx + 14, my + 66), sub, 10, MUTED, "mono")

        # 3D Isometric Voxel Wave ribbon along bottom left
        for row_idx in range(3):
            for col_idx in range(18):
                sx = 58 + col_idx * 22 + row_idx * 11
                sy = 372 + row_idx * 7
                w = math.sin(col_idx * 0.52 + row_idx * 0.7 - phase * 2.0 * math.pi) * 0.5 + 0.5
                h = 5 + w * 18
                tc = hex_blend("#0e4429", GREEN, w) if w > 0.4 else hex_blend("#0f172a", CYAN, w * 1.5)
                lc = hex_blend("#090d16", "#006d32", w)
                rc = hex_blend("#050811", "#0e4429", w)
                c.iso_prism(sx, sy, 17, 8, h, tc, lc, rc)

        render_3d_core(c, 965, 215, phase, radius_scale=1.02)
        c.text((965, 382), "3D GEODESIC CORE · 60FPS", 12, CYAN, "mono_bold", anchor="mt")

    return c.finish()


STAGES = [
    ("01 // DECONSTRUCT", "Map Workflow Friction", "100% Domain Schema", GREEN),
    ("02 // ARCHITECT", "Type-Safe Multi-Tenant", "57+ Prisma Models", CYAN),
    ("03 // HARDEN", "Offline LAN & Retries", "0ms Cloud Dependency", AMBER),
    ("04 // ACCELERATE", "AI & Telemetry Loops", "80+ Cloud Deploys", VIOLET),
]


def build_loop_raster(phase: float, mobile: bool = False) -> Image.Image:
    c = Canvas3D(720, 420) if mobile else Canvas3D(1200, 235)
    c.rect((1, 1, c.width - 2, c.height - 2), fill=BG, radius=16, outline=BORDER, width=1.5)
    c.text((32, 20), "3D EXECUTION PIPELINE  //  ARCHITECTURE TO PRODUCTION", 12, MUTED, "mono_bold")

    active = int(phase * 4) % 4
    progress = (phase * 4) % 1.0

    for i, (code, title, metric, col) in enumerate(STAGES):
        x = 32 + (i % 2) * 336 if mobile else 32 + i * 288
        y = 62 + (i // 2) * 168 if mobile else 56
        w = 316 if mobile else 272
        h = 148 if mobile else 154

        is_act = (i == active)
        c.rect((x, y, x + w, y + h), fill=PANEL, radius=12, outline=col if is_act else BORDER, width=1.8 if is_act else 1.0)

        # 3D Isometric Cube in top-right of each stage card
        cube_h = 12 + (math.sin(phase * 2 * math.pi + i) * 0.5 + 0.5) * 10
        c.iso_prism(x + w - 28, y + 36, 22, 10, cube_h, col if is_act else "#1e293b", "#0f172a", "#090d16", outline=col)

        c.text((x + 16, y + 16), code, 11, col, "mono_bold")
        c.text((x + 16, y + 46), title, 16, TEXT, "bold")
        c.text((x + 16, y + 76), metric, 12, col if is_act else MUTED, "mono")

        for j in range(10):
            seg_col = "#1e293b"
            if is_act and j <= int(progress * 10):
                seg_col = col
            elif i < active:
                seg_col = hex_blend("#0f172a", col, 0.55)
            c.rect((x + 16 + j * 22, y + 112, x + 16 + j * 22 + 16, y + 122), fill=seg_col, radius=3)

    return c.finish()


def save_animation(name: str, renderer, mobile: bool = False) -> None:
    frames = [renderer(i / FRAMES, mobile) for i in range(FRAMES)]
    frames[0].save(ASSETS / f"{name}.png", optimize=True)
    master_palette = frames[0].quantize(colors=256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    quantized = [f.quantize(palette=master_palette, dither=Image.Dither.NONE) for f in frames]
    output = BytesIO()
    quantized[0].save(
        output, format="GIF", save_all=True, append_images=quantized[1:],
        duration=DURATION_MS, loop=0, optimize=True, disposal=2,
    )
    target = ASSETS / f"{name}.gif"
    temporary = ASSETS / f"{name}.gif.tmp"
    temporary.write_bytes(output.getvalue())
    temporary.replace(target)
    print(f"{name}: {frames[0].size}, {FRAMES} frames, {target.stat().st_size:,} bytes")


def main() -> None:
    ASSETS.mkdir(exist_ok=True)
    generate_hero_3d_svg()
    generate_telemetry_3d_svg()
    generate_constellation_3d_svg()
    generate_architecture_3d_svg()
    generate_footer_svg()
    save_animation("profile-hero", hero_raster, mobile=False)
    save_animation("profile-hero-mobile", hero_raster, mobile=True)
    save_animation("build-loop", build_loop_raster, mobile=False)
    save_animation("build-loop-mobile", build_loop_raster, mobile=True)


if __name__ == "__main__":
    main()
