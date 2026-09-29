#!/usr/bin/env python3
"""
Apply a low-opacity watermark (text or logo) over an image.

Requires: pip install pillow

Examples:
  python watermark.py photo.jpg out.jpg --text "© Jane Doe"
  python watermark.py photo.jpg out.png --logo logo.png --opacity 0.2 --position bottom-right
  python watermark.py photo.jpg out.jpg --text "CONFIDENTIAL" --position tile --angle 30
"""

import argparse
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps


KYKA_PATH = "C:\\Users\\Penelope\\Desktop\\KYKA DEVELOPEMENT\\"


POSITIONS = [
    "center", "top-left", "top-right", "bottom-left", "bottom-right", "tile",
]

FONT_CANDIDATES = [
    "DejaVuSans-Bold.ttf",
    "Arial Bold.ttf",
    "arialbd.ttf",
    "Helvetica.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "C:/Windows/Fonts/arialbd.ttf",
]


def load_font(size: int) -> ImageFont.ImageFont:
    for name in FONT_CANDIDATES:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    try:
        return ImageFont.load_default(size=size)  # Pillow >= 10.1
    except TypeError:
        return ImageFont.load_default()


def make_text_mark(text: str, font_size: int, color=(255, 255, 255)) -> Image.Image:
    font = load_font(font_size)
    left, top, right, bottom = font.getbbox(text)
    pad = max(2, font_size // 10)
    mark = Image.new("RGBA", (right - left + pad * 2, bottom - top + pad * 2), (0, 0, 0, 0))
    ImageDraw.Draw(mark).text((pad - left, pad - top), text, font=font, fill=color + (255,))
    return mark


def make_logo_mark(path: str, target_width: int) -> Image.Image:
    logo = Image.open(path).convert("RGBA")
    ratio = target_width / logo.width
    return logo.resize((target_width, max(1, int(logo.height * ratio))), Image.LANCZOS)


def set_opacity(mark: Image.Image, opacity: float) -> Image.Image:
    """Scale the existing alpha channel so transparent logos stay transparent."""
    mark = mark.copy()
    alpha = mark.getchannel("A").point(lambda p: int(p * opacity))
    mark.putalpha(alpha)
    return mark


def place(base_size, mark_size, position, margin):
    bw, bh = base_size
    mw, mh = mark_size
    return {
        "center": ((bw - mw) // 2, (bh - mh) // 2),
        "top-left": (margin, margin),
        "top-right": (bw - mw - margin, margin),
        "bottom-left": (margin, bh - mh - margin),
        "bottom-right": (bw - mw - margin, bh - mh - margin),
    }[position]


def apply_watermark(image, mark, position="center", margin=20, spacing=1.5):
    base = image.convert("RGBA")
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    mw, mh = mark.size

    if position == "tile":
        step_x, step_y = int(mw * spacing), int(mh * spacing * 2)
        row = 0
        for y in range(-mh, base.height + mh, step_y):
            offset = (step_x // 2) if row % 2 else 0  # stagger alternate rows
            for x in range(-mw + offset, base.width + mw, step_x):
                layer.paste(mark, (x, y), mark)  # PIL clips out-of-bounds pastes
            row += 1
    else:
        layer.paste(mark, place(base.size, mark.size, position, margin), mark)

    return Image.alpha_composite(base, layer)


def main():
    p = argparse.ArgumentParser(description="Apply a low-opacity watermark to an image.")
    p.add_argument("input", help="Input image path")
    p.add_argument("output", help="Output image path")
    #src = p.add_mutually_exclusive_group(required=True)
    #src.add_argument("--text", help="Watermark text")
    #src.add_argument("--logo", help="Path to watermark image (PNG with transparency works best)")
    p.add_argument("--opacity", type=float, default=0.50, help="0.0 (invisible) to 1.0 (solid). Default 0.25")
    p.add_argument("--position", choices=POSITIONS, default="center", help="Default: center")
    p.add_argument("--scale", type=float, default=0.8,
                   help="Watermark width as a fraction of image width (logo) or text width target. Default 0.3")
    p.add_argument("--angle", type=float, default=0, help="Rotation in degrees. Default 0")
    p.add_argument("--margin", type=int, default=20, help="Edge margin in px for corner positions")
    p.add_argument("--color", default="255,255,255", help="Text color as R,G,B. Default 255,255,255")
    p.add_argument("--quality", type=int, default=95, help="JPEG quality. Default 95")
    args = p.parse_args()

    args.logo = KYKA_PATH+"kyka_logo.png"

    if not 0 <= args.opacity <= 1:
        sys.exit("Error: --opacity must be between 0 and 1")

    try:
        image = ImageOps.exif_transpose(Image.open(args.input))
    except FileNotFoundError:
        sys.exit(f"Error: input file not found: {args.input}")

    target_width = max(1, int(image.width * args.scale))

    #if args.text:
    #    color = tuple(int(c) for c in args.color.split(","))
    #    mark = make_text_mark(args.text, font_size=100, color=color)
    #    # Scale the rendered text to the target width
    #    ratio = target_width / mark.width
    #    mark = mark.resize((target_width, max(1, int(mark.height * ratio))), Image.LANCZOS)
    #else:
    mark = make_logo_mark(args.logo, target_width)

    if args.angle:
        mark = mark.rotate(args.angle, expand=True, resample=Image.BICUBIC)

    mark = set_opacity(mark, args.opacity)
    result = apply_watermark(image, mark, args.position, args.margin)

    out = Path(args.output)
    save_kwargs = {}
    if out.suffix.lower() in (".jpg", ".jpeg"):
        result = result.convert("RGB")
        save_kwargs = {"quality": args.quality, "subsampling": 0}
    result.save(out, **save_kwargs)
    print(f"Saved: {out}")


if __name__ == "__main__":
    main()
