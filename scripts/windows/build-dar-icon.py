"""Build Docly logo PNG and multi-size .ico. Does not require a pre-existing bitmap."""
from __future__ import annotations

import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "assets"
LOGO = ASSETS / "docly-logo.png"
OUT = ASSETS / "docly-icon.ico"
WEB_PUBLIC = ROOT.parents[1] / "apps" / "web" / "public" / "docly-logo.png"


def _make_logo(size: int = 256) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    margin = size // 16
    radius = size // 5
    # Navy rounded square
    draw.rounded_rectangle(
        [margin, margin, size - margin, size - margin],
        radius=radius,
        fill=(15, 42, 71, 255),
    )
    # Document sheet
    sheet = [
        size * 0.30,
        size * 0.24,
        size * 0.70,
        size * 0.78,
    ]
    draw.rounded_rectangle(sheet, radius=size // 18, fill=(248, 250, 252, 255))
    # Folded corner
    fold = size * 0.14
    draw.polygon(
        [
            (sheet[2] - fold, sheet[1]),
            (sheet[2], sheet[1] + fold),
            (sheet[2] - fold, sheet[1] + fold),
        ],
        fill=(203, 213, 225, 255),
    )
    # Text lines
    line_color = (37, 99, 235, 255)
    y = int(size * 0.40)
    for width_ratio in (0.28, 0.22, 0.18):
        draw.rounded_rectangle(
            [size * 0.36, y, size * (0.36 + width_ratio), y + size * 0.045],
            radius=size // 40,
            fill=line_color,
        )
        y += int(size * 0.09)
    # Mark
    try:
        font = ImageFont.truetype("segoeui.ttf", size // 7)
    except OSError:
        font = ImageFont.load_default()
    draw.text((size * 0.38, size * 0.08), "D", fill=(255, 255, 255, 255), font=font)
    return img


def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    logo = _make_logo(256)
    logo.save(LOGO, format="PNG")
    sizes = [256, 128, 64, 48, 32, 16]
    imgs = [logo.resize((size, size), Image.Resampling.LANCZOS) for size in sizes]
    imgs[0].save(
        OUT,
        format="ICO",
        sizes=[(size, size) for size in sizes],
        append_images=imgs[1:],
    )
    WEB_PUBLIC.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(LOGO, WEB_PUBLIC)
    print(f"Wrote {OUT} ({OUT.stat().st_size} bytes)")
    print(f"Wrote {LOGO} and {WEB_PUBLIC}")


if __name__ == "__main__":
    main()
