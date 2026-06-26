# Assets

Drop the menu bar icons here. Until they exist, the app falls back to emoji in
the menu bar title, so it runs without them.

| File             | Purpose                              | Notes |
|------------------|--------------------------------------|-------|
| `idle.png`       | Menu bar icon when nothing is active | ~18–22px, black on transparent (template image) |
| `running.png`    | Menu bar icon when a session is live | the "running clock" Flaticon favorite |
| `tomatick.icns`  | App bundle icon (Dock/Finder)        | generated from a 1024px PNG |

## Getting the icons

The favorites are from Flaticon's clock set:
<https://www.flaticon.com/free-icons/clock>

**Flaticon's free license requires attribution** (already credited in the app's
About box and the project README). Premium accounts can skip attribution.

### Make template menu-bar PNGs
Menu-bar icons should be small, black, and transparent so macOS can tint them
for light/dark menu bars (the app already sets `template = True`):

```bash
sips -z 22 22 source.png --out idle.png      # resize to 22x22
```

### Make the .icns bundle icon
```bash
mkdir tomatick.iconset
sips -z 16 16   source.png --out tomatick.iconset/icon_16x16.png
sips -z 32 32   source.png --out tomatick.iconset/icon_16x16@2x.png
sips -z 128 128 source.png --out tomatick.iconset/icon_128x128.png
sips -z 256 256 source.png --out tomatick.iconset/icon_256x256.png
sips -z 512 512 source.png --out tomatick.iconset/icon_512x512.png
iconutil -c icns tomatick.iconset -o tomatick.icns
```
