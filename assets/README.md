# Profile artwork

The profile uses GitHub's familiar dark background and contribution greens:

| Use | Color |
| --- | --- |
| Background | `#0d1117` |
| Panel | `#161b22` |
| Border | `#30363d` |
| Main text | `#f0f6fc` |
| Secondary text | `#8b949e` |
| Contribution greens | `#0e4429`, `#006d32`, `#26a641`, `#39d353` |

The animated grid spells **EOJ**. It is decorative artwork inspired by contribution cells, not a chart of activity or a claim about commit counts. The second animation follows the four stages described in the README.

All profile images are served from this repository. Desktop and mobile layouts each have a GIF and a static PNG. The README's `<picture>` elements select static artwork when the browser reports `prefers-reduced-motion: reduce`.

## Regenerate

Use Python 3.10 or newer, Pillow, and DejaVu Sans / DejaVu Sans Mono fonts:

```bash
python -m pip install -r scripts/requirements.txt
python scripts/render_assets.py
```

The renderer looks for DejaVu fonts in standard Linux and macOS font directories. Set `PROFILE_FONT_DIR` to a directory containing `DejaVuSans.ttf`, `DejaVuSans-Bold.ttf`, and `DejaVuSansMono.ttf` if they are elsewhere. Committed image files make font installation unnecessary for viewing the profile.
