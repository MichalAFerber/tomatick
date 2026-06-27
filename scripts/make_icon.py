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

# Menu-bar icon: small canvas (rendered crisp, displayed small). Padding leaves
# room so the alarm frames (rotation + scale) don't clip. Each alarm frame is
# (shake_angle_degrees, pulse_scale) — together they rock AND bulge out.
MB_SIZE = 44
ALARM_FRAMES = [
    (-9, 1.05), (-4, 1.12), (0, 1.16), (4, 1.12),
    (9, 1.05), (4, 1.10), (0, 1.14), (-4, 1.10),
]


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


def _render_png(size, draw_fn, path):
    rep = AppKit.NSBitmapImageRep.alloc().initWithBitmapDataPlanes_pixelsWide_pixelsHigh_bitsPerSample_samplesPerPixel_hasAlpha_isPlanar_colorSpaceName_bytesPerRow_bitsPerPixel_(
        None, size, size, 8, 4, True, False,
        AppKit.NSCalibratedRGBColorSpace, 0, 0)
    ctx = AppKit.NSGraphicsContext.graphicsContextWithBitmapImageRep_(rep)
    AppKit.NSGraphicsContext.saveGraphicsState()
    AppKit.NSGraphicsContext.setCurrentContext_(ctx)
    draw_fn()
    AppKit.NSGraphicsContext.restoreGraphicsState()
    png = rep.representationUsingType_properties_(
        AppKit.NSBitmapImageFileTypePNG, {})
    png.writeToFile_atomically_(str(path), True)


def render_master(path: Path):
    _render_png(SIZE, _draw, path)


def _draw_menubar(spec, angle_deg=0.0, scale=1.0):
    """Draw a plump, round menu-bar tomato glyph, rotated + scaled about center.

    Wider-than-tall body; red theme uses a radial gradient + specular shine for a
    glossy look, white/black are solid silhouettes. Prominent green calyx + stem.
    """
    S = MB_SIZE
    if angle_deg or scale != 1.0:
        t = AppKit.NSAffineTransform.transform()
        t.translateXBy_yBy_(S / 2.0, S / 2.0)
        if angle_deg:
            t.rotateByDegrees_(angle_deg)
        if scale != 1.0:
            t.scaleBy_(scale)
        t.translateXBy_yBy_(-S / 2.0, -S / 2.0)
        t.concat()

    # Plump body: wider than tall, filling most of the canvas (the remaining
    # padding leaves room for the rotation + pulse on the alarm frames).
    body = AppKit.NSBezierPath.bezierPathWithOvalInRect_(NSMakeRect(5, 7, 34, 23))
    if spec.get("grad"):
        grad = AppKit.NSGradient.alloc().initWithColors_(spec["grad"])
        # Light source upper-left for a glossy 3-D sphere feel.
        grad.drawInBezierPath_relativeCenterPosition_(body, (-0.35, 0.35))
    else:
        spec["body"].set()
        body.fill()

    if spec.get("shine") is not None:
        shine = AppKit.NSBezierPath.bezierPathWithOvalInRect_(NSMakeRect(11, 23, 12, 6))
        spec["shine"].set()
        shine.fill()

    # Prominent green calyx (pointy leaves) + a stem nub on top.
    calyx = _star_path(22, 30, 8.0, 3.3, points=5)
    spec["calyx"].set()
    calyx.fill()

    stem = AppKit.NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(
        NSMakeRect(20, 33, 4, 5), 1.8, 1.8)
    spec["stem"].set()
    stem.fill()


def _menubar_themes():
    return {
        "red": {"grad": [_color(1.0, 0.46, 0.36), _color(0.91, 0.18, 0.14),
                         _color(0.70, 0.07, 0.06)],
                "shine": _color(1, 1, 1, 0.55), "calyx": _color(0.33, 0.62, 0.27),
                "stem": _color(0.28, 0.45, 0.20)},
        "white": {"body": _color(1, 1, 1), "shine": None,
                  "calyx": _color(1, 1, 1), "stem": _color(1, 1, 1)},
        "black": {"body": _color(0, 0, 0), "shine": None,
                  "calyx": _color(0, 0, 0), "stem": _color(0, 0, 0)},
    }


def build_about_image():
    """Render a large, crisp version of the red tomato for the About tab."""
    ASSETS.mkdir(parents=True, exist_ok=True)
    spec = _menubar_themes()["red"]
    S = 256

    def draw():
        t = AppKit.NSAffineTransform.transform()
        t.scaleBy_(S / float(MB_SIZE))  # draw the 44-unit glyph filling 256px
        t.concat()
        _draw_menubar(spec, 0.0, 1.0)

    _render_png(S, draw, ASSETS / "about.png")
    print("wrote about.png")


def build_extlink_icon():
    """Render an original external-link glyph (box + out-arrow) for link buttons."""
    ASSETS.mkdir(parents=True, exist_ok=True)
    S = 36
    col = _color(0.5, 0.5, 0.5)

    def draw():
        col.set()
        box = AppKit.NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(
            NSMakeRect(5, 4, 17, 17), 3, 3)
        box.setLineWidth_(3.0)
        box.stroke()
        arrow = AppKit.NSBezierPath.bezierPath()
        arrow.setLineWidth_(3.0)
        arrow.moveToPoint_(NSMakePoint(17, 17))
        arrow.lineToPoint_(NSMakePoint(30, 30))
        arrow.moveToPoint_(NSMakePoint(30, 30))
        arrow.lineToPoint_(NSMakePoint(21, 30))
        arrow.moveToPoint_(NSMakePoint(30, 30))
        arrow.lineToPoint_(NSMakePoint(30, 21))
        arrow.stroke()

    _render_png(S, draw, ASSETS / "extlink.png")
    print("wrote extlink.png")


def build_menubar_icons():
    """Render idle + shake frames for each selectable theme into assets/."""
    ASSETS.mkdir(parents=True, exist_ok=True)
    themes = _menubar_themes()
    for name, spec in themes.items():
        _render_png(MB_SIZE, lambda s=spec: _draw_menubar(s, 0.0, 1.0),
                    ASSETS / f"mb_{name}.png")
        for j, (ang, sc) in enumerate(ALARM_FRAMES):
            _render_png(MB_SIZE, lambda s=spec, a=ang, z=sc: _draw_menubar(s, a, z),
                        ASSETS / f"mb_{name}_{j}.png")
    print(f"wrote menu-bar frames for: {', '.join(themes)}")


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
    build_menubar_icons()
    build_about_image()
    build_extlink_icon()
