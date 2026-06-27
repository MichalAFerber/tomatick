"""Generate the Tomatick app icon (tomatick/assets/tomatick.icns).

Draws an original flat tomato on a soft rounded-rect background with AppKit
(no external assets), renders a 1024px master PNG, then uses sips + iconutil to
build the .icns. Run on macOS with the project venv active:

    python scripts/make_icon.py
"""

from __future__ import annotations

import math
import subprocess
import tempfile
from pathlib import Path

import AppKit
from Foundation import NSMakeRect, NSMakePoint

SIZE = 1024
ASSETS = Path(__file__).resolve().parent.parent / "tomatick" / "assets"


def _color(r, g, b, a=1.0):
    return AppKit.NSColor.colorWithCalibratedRed_green_blue_alpha_(r, g, b, a)


def _star_path(cx, cy, outer, inner, points=5, rotation=-math.pi / 2):
    path = AppKit.NSBezierPath.bezierPath()
    for i in range(points * 2):
        radius = outer if i % 2 == 0 else inner
        angle = rotation + i * math.pi / points
        x = cx + radius * math.cos(angle)
        y = cy + radius * math.sin(angle)
        pt = NSMakePoint(x, y)
        if i == 0:
            path.moveToPoint_(pt)
        else:
            path.lineToPoint_(pt)
    path.closePath()
    return path


def _draw():
    # Background: rounded-rect squircle with a warm vertical gradient.
    inset = 80
    bg = AppKit.NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(
        NSMakeRect(inset, inset, SIZE - 2 * inset, SIZE - 2 * inset), 200, 200)
    gradient = AppKit.NSGradient.alloc().initWithStartingColor_endingColor_(
        _color(1.0, 0.97, 0.93), _color(1.0, 0.88, 0.78))
    gradient.drawInBezierPath_angle_(bg, -90.0)

    # Tomato body (slightly squat) with a soft highlight.
    body = AppKit.NSBezierPath.bezierPathWithOvalInRect_(
        NSMakeRect(192, 180, 640, 580))
    _color(0.85, 0.20, 0.16).set()
    body.fill()

    highlight = AppKit.NSBezierPath.bezierPathWithOvalInRect_(
        NSMakeRect(300, 540, 240, 150))
    _color(1.0, 0.58, 0.48, 0.45).set()
    highlight.fill()

    # Green calyx (5-point star) and stem on top.
    calyx = _star_path(512, 700, 165, 70, points=5)
    _color(0.36, 0.62, 0.27).set()
    calyx.fill()

    stem = AppKit.NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(
        NSMakeRect(494, 740, 36, 110), 18, 18)
    _color(0.30, 0.46, 0.22).set()
    stem.fill()


def render_master(path: Path):
    rep = AppKit.NSBitmapImageRep.alloc().initWithBitmapDataPlanes_pixelsWide_pixelsHigh_bitsPerSample_samplesPerPixel_hasAlpha_isPlanar_colorSpaceName_bytesPerRow_bitsPerPixel_(
        None, SIZE, SIZE, 8, 4, True, False,
        AppKit.NSCalibratedRGBColorSpace, 0, 0)
    ctx = AppKit.NSGraphicsContext.graphicsContextWithBitmapImageRep_(rep)
    AppKit.NSGraphicsContext.saveGraphicsState()
    AppKit.NSGraphicsContext.setCurrentContext_(ctx)
    _draw()
    AppKit.NSGraphicsContext.restoreGraphicsState()
    png = rep.representationUsingType_properties_(
        AppKit.NSBitmapImageFileTypePNG, {})
    png.writeToFile_atomically_(str(path), True)


def build_icns():
    ASSETS.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        master = tmp / "icon_1024.png"
        render_master(master)

        iconset = tmp / "tomatick.iconset"
        iconset.mkdir()
        # (size, filename) entries for a complete iconset.
        sizes = [
            (16, "icon_16x16.png"), (32, "icon_16x16@2x.png"),
            (32, "icon_32x32.png"), (64, "icon_32x32@2x.png"),
            (128, "icon_128x128.png"), (256, "icon_128x128@2x.png"),
            (256, "icon_256x256.png"), (512, "icon_256x256@2x.png"),
            (512, "icon_512x512.png"), (1024, "icon_512x512@2x.png"),
        ]
        for px, name in sizes:
            subprocess.run(
                ["sips", "-z", str(px), str(px), str(master),
                 "--out", str(iconset / name)],
                check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        out = ASSETS / "tomatick.icns"
        subprocess.run(["iconutil", "-c", "icns", str(iconset), "-o", str(out)],
                       check=True)
        print(f"wrote {out}")


if __name__ == "__main__":
    build_icns()
