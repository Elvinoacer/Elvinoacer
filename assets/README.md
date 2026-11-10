# 3D Profile Artwork & Telemetry Engine

All visual assets in this repository are **100% self-contained and procedurally generated** via [`scripts/render_assets.py`](../scripts/render_assets.py) using 3D rotation matrices, perspective projection ($f / (d - z)$), depth-sorted painter's algorithm, and isometric 3D extrusion.

## Generated Assets

| Asset | Format | Description |
| :--- | :--- | :--- |
| `hero-3d.svg` | 60fps Vector 3D SVG | True 3D perspective-projected rotating geodesic icosahedron & counter-rotating octahedron core, 3D orbital rings, isometric voxel contribution wave, and live metric cards |
| `telemetry-3d.svg` | 60fps Vector 3D SVG | 3D isometric contribution velocity bars (`5,107+` total), flagship complexity benchmarks (`57` Prisma models, `39` POS screens), and holographic stack distribution |
| `project-constellation-3d.svg` | 60fps Vector 3D SVG | 3D isometric multi-node production constellation linking the central GTSS Nexus reactor to 6 flagship systems with animated bezier data packets |
| `architecture-3d.svg` | 60fps Vector 3D SVG | 3D exploded isometric 3-tier system topology with vertical laser conduits and 4-stage execution loop |
| `profile-hero.gif` / `.png` | 3D Raster GIF + PNG | Supersampled 3D software-rendered command deck (desktop & mobile variants) with `<picture>` reduced-motion support |
| `build-loop.gif` / `.png` | 3D Raster GIF + PNG | 3D isometric 4-stage execution pipeline (desktop & mobile variants) |
| `footer.svg` | 60fps Vector 3D SVG | 3D perspective receding horizon grid and animated laser pulse |

## Regenerate

```bash
python3 -m pip install -r scripts/requirements.txt
python3 scripts/render_assets.py
```
