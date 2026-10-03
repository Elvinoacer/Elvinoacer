"""Generate the profile's dark/green artwork with no remote assets."""

from __future__ import annotations

import math
import os
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
BG = "#0d1117"
PANEL = "#161b22"
BORDER = "#30363d"
TEXT = "#f0f6fc"
MUTED = "#8b949e"
GREEN = "#39d353"
GREENS = ["#0e4429", "#006d32", "#26a641", GREEN]
SCALE = 2
FRAMES = 48
DURATION_MS = 160


def font_path(filename: str) -> Path:
    locations = [
        Path(os.environ["PROFILE_FONT_DIR"])
        if os.environ.get("PROFILE_FONT_DIR") else None,
        Path("/usr/share/fonts/truetype/dejavu"),
        Path("/usr/local/share/fonts"),
        Path.home() / "Library/Fonts",
        Path("/Library/Fonts"),
    ]
    for directory in locations:
        if directory is not None and (directory / filename).is_file():
            return directory / filename
    raise FileNotFoundError(
        f"Install DejaVu fonts or set PROFILE_FONT_DIR; missing {filename}"
    )


FONT_PATHS = {
    "regular": font_path("DejaVuSans.ttf"),
    "bold": font_path("DejaVuSans-Bold.ttf"),
    "mono": font_path("DejaVuSansMono.ttf"),
}
FONTS: dict[tuple[str, int], ImageFont.FreeTypeFont] = {}


def rgb(color: str) -> tuple[int, int, int]:
    return tuple(int(color[i:i + 2], 16) for i in (1, 3, 5))


def blend(a: str, b: str, amount: float) -> tuple[int, int, int]:
    return tuple(round(x + (y - x) * amount) for x, y in zip(rgb(a), rgb(b)))


class Canvas:
    def __init__(self, width: int, height: int):
        self.width, self.height = width, height
        self.image = Image.new("RGB", (width * SCALE, height * SCALE), BG)
        self.draw = ImageDraw.Draw(self.image)

    def rect(self, box, color, radius=0, outline=None, width=1):
        scaled = tuple(round(v * SCALE) for v in box)
        if radius:
            self.draw.rounded_rectangle(
                scaled, radius=radius * SCALE, fill=color,
                outline=outline, width=width * SCALE,
            )
        else:
            self.draw.rectangle(scaled, fill=color, outline=outline, width=width * SCALE)

    def line(self, points, color=BORDER, width=1):
        self.draw.line(
            [(round(x * SCALE), round(y * SCALE)) for x, y in points],
            fill=color, width=width * SCALE,
        )

    def text(self, pos, value, size, color=TEXT, style="regular", spacing=None):
        key = (style, size)
        if key not in FONTS:
            FONTS[key] = ImageFont.truetype(str(FONT_PATHS[style]), size * SCALE)
        f = FONTS[key]
        x, y = pos[0] * SCALE, pos[1] * SCALE
        if spacing is None:
            self.draw.text((x, y), value, fill=color, font=f, anchor="lt")
        else:
            for ch in value:
                self.draw.text((x, y), ch, fill=color, font=f, anchor="lt")
                x += self.draw.textlength(ch, font=f) + spacing * SCALE

    def finish(self):
        return self.image.resize((self.width, self.height), Image.Resampling.LANCZOS)


GLYPHS = [
    ["11111", "10000", "10000", "11110", "10000", "10000", "11111"],
    ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
    ["00111", "00010", "00010", "00010", "10010", "10010", "01100"],
]


def is_letter(column: int, row: int) -> bool:
    if not (1 <= row <= 7 and 1 <= column <= 17):
        return False
    glyph, offset = divmod(column - 1, 6)
    return offset < 5 and glyph < 3 and GLYPHS[glyph][row - 1][offset] == "1"


def monogram(c: Canvas, x: int, y: int, step: int, cell: int, phase: float):
    for column in range(19):
        distance = ((column / 19 - phase + 0.5) % 1) - 0.5
        sweep = math.exp(-((distance / 0.11) ** 2))
        for row in range(9):
            if is_letter(column, row):
                base = GREENS[1 + ((column + row) % 3)]
                color = blend(base, GREEN, sweep * 0.7)
            else:
                color = blend(PANEL, GREENS[0], sweep * 0.35)
            c.rect(
                (x + column * step, y + row * step,
                 x + column * step + cell, y + row * step + cell),
                color, radius=2,
            )


def hero(phase: float, mobile=False):
    if mobile:
        c = Canvas(720, 712)
        c.rect((1, 1, 718, 710), BG, radius=16, outline=BORDER)
        c.line([(44, 39), (93, 39)], GREEN, 3)
        c.text((44, 62), "FULL-STACK PRODUCT ENGINEER", 18, GREEN, "mono")
        c.text((44, 102), "Elvin Omondi Juma", 34, TEXT, "bold")
        c.text((42, 178), "Software for", 57, TEXT, "bold")
        c.text((42, 245), "the way life works.", 57, GREEN, "bold")
        c.text((44, 324), "From everyday friction to useful products.", 21, MUTED)
        c.line([(44, 376), (675, 376)], BORDER)
        monogram(c, 160, 407, 21, 16, phase)
        c.text((176, 616), "ONE COMMIT AT A TIME", 18, MUTED, "mono")
        c.text((44, 673), "KENYA  /  GTSS  /  MOI UNIVERSITY", 16, MUTED, "mono")
    else:
        c = Canvas(1200, 422)
        c.rect((1, 1, 1198, 420), BG, radius=16, outline=BORDER)
        c.line([(48, 39), (94, 39)], GREEN, 3)
        c.text((48, 61), "FULL-STACK PRODUCT ENGINEER", 15, GREEN, "mono")
        c.text((48, 96), "Elvin Omondi Juma", 32, TEXT, "bold")
        c.text((45, 164), "Software for", 52, TEXT, "bold")
        c.text((45, 228), "the way life works.", 52, GREEN, "bold")
        c.text((48, 303), "From everyday friction to useful products.", 19, MUTED)
        c.line([(717, 67), (717, 355)], BORDER)
        monogram(c, 773, 102, 19, 14, phase)
        c.text((786, 304), "ONE COMMIT AT A TIME", 16, GREEN, "mono")
        c.text((784, 337), "Products shaped by real workflows.", 14, MUTED)
        c.line([(48, 359), (660, 359)], BORDER)
        c.text((48, 382), "KENYA  /  GTSS  /  MOI UNIVERSITY", 14, MUTED, "mono")
    return c.finish()


STAGES = [
    ("Understand", "the workflow"),
    ("Build", "the useful core"),
    ("Test", "the failure paths"),
    ("Improve", "from feedback"),
]


def build_loop(phase: float, mobile=False):
    c = Canvas(720, 408) if mobile else Canvas(1200, 218)
    c.rect((1, 1, c.width - 2, c.height - 2), BG, radius=12, outline=BORDER)
    c.text((32, 23), "AN ITERATIVE PRACTICE", 17 if mobile else 15, MUTED, "mono")
    active = int(phase * 4) % 4
    progress = phase * 4 % 1
    for i, (title, subtitle) in enumerate(STAGES):
        x = 32 + (i % 2) * 346 if mobile else 42 + i * 291
        y = 81 + (i // 2) * 162 if mobile else 81
        c.text((x, y), f"0{i + 1}", 17 if mobile else 15, GREEN if i == active else MUTED, "mono")
        c.text((x, y + 31), title, 29 if mobile else 26, TEXT, "bold")
        c.text((x, y + 72), subtitle, 20 if mobile else 18, MUTED)
        for j in range(8):
            color = GREENS[0]
            if i == active and j <= int(progress * 8):
                color = GREENS[min(3, max(1, 3 - (int(progress * 8) - j) // 2))]
            c.rect((x + j * 20, y + 115, x + j * 20 + 13, y + 123), color, radius=2)
    return c.finish()


def save_animation(name: str, renderer, mobile=False):
    frames = [renderer(i / FRAMES, mobile) for i in range(FRAMES)]
    frames[0].save(ASSETS / f"{name}.png", optimize=True)
    # One palette prevents flicker between frames. Reserve half for the greens
    # and half for the anti-aliased neutral typography and panel colors.
    palette = Image.new("P", (1, 1))
    colors = []
    for i in range(128):
        colors.extend(blend(BG, TEXT, i / 127))
    for i in range(128):
        colors.extend(blend(BG, GREEN, i / 127))
    palette.putpalette(colors)
    quantized = [f.quantize(palette=palette, dither=Image.Dither.NONE) for f in frames]
    output = BytesIO()
    quantized[0].save(
        output, format="GIF", save_all=True, append_images=quantized[1:],
        duration=DURATION_MS, loop=0, optimize=True, disposal=1,
    )
    target = ASSETS / f"{name}.gif"
    temporary = ASSETS / f"{name}.gif.tmp"
    temporary.write_bytes(output.getvalue())
    temporary.replace(target)
    size = target.stat().st_size
    print(f"{name}: {frames[0].size}, {FRAMES} frames, {size:,} bytes")


def footer():
    squares = "".join(
        f'<rect x="{968 + i * 24}" y="48" width="15" height="15" rx="3" fill="{color}"/>'
        for i, color in enumerate(GREENS)
    )
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="108" viewBox="0 0 1200 108" role="img" aria-labelledby="title desc">
<title id="title">Built in Kenya. Built to be used.</title>
<desc id="desc">A quiet green signature for Elvin Omondi Juma.</desc>
<rect width="1200" height="108" rx="12" fill="{BG}"/>
<path d="M32 1H1168" stroke="{BORDER}"/>
<text x="32" y="63" fill="{TEXT}" font-family="DejaVu Sans,Segoe UI,sans-serif" font-size="24" font-weight="600">Built in Kenya. <tspan fill="{GREEN}">Built to be used.</tspan></text>
{squares}
</svg>
'''
    (ASSETS / "footer.svg").write_text(svg, encoding="utf-8")


def main():
    ASSETS.mkdir(exist_ok=True)
    save_animation("profile-hero", hero)
    save_animation("profile-hero-mobile", hero, mobile=True)
    save_animation("build-loop", build_loop)
    save_animation("build-loop-mobile", build_loop, mobile=True)
    footer()


if __name__ == "__main__":
    main()
