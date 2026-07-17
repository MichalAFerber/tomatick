// Generates raster brand assets from the SVG brand mark using the preinstalled
// Chromium (no network, no image libs). Produces:
//   public/og.png              1200x630  social card
//   public/apple-touch-icon.png 180x180
//   public/icon-512.png        512x512   (PWA manifest)
//   public/favicon-32.png      32x32     (source for favicon.ico)
// favicon.ico is packed separately by scripts/make-favicon.py (Pillow).
import { chromium } from 'playwright';
import { readFileSync, writeFileSync, mkdirSync, readdirSync, existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const here = dirname(fileURLToPath(import.meta.url));
const pub = join(here, '..', 'public');
mkdirSync(pub, { recursive: true });

const favicon = readFileSync(join(pub, 'favicon.svg'), 'utf8');

// Resolve the preinstalled Chromium (build number varies by environment).
function resolveChrome() {
  if (process.env.CHROME_BIN) return process.env.CHROME_BIN;
  const base = process.env.PLAYWRIGHT_BROWSERS_PATH || '/opt/pw-browsers';
  try {
    for (const d of readdirSync(base).filter((n) => n.startsWith('chromium-'))) {
      const p = join(base, d, 'chrome-linux', 'chrome');
      if (existsSync(p)) return p;
    }
  } catch {}
  return undefined; // fall back to Playwright's own resolution
}
const executablePath = resolveChrome();

// Embed the house display font so the OG card renders in JetBrains Mono
// (Chromium has no system copy). Base64 data URI keeps it self-contained.
const fontB64 = readFileSync(join(pub, 'fonts', 'jetbrains-mono-latin-800-normal.woff2')).toString('base64');
const fontFace = `@font-face{font-family:'JetBrains Mono';font-weight:700 800;font-display:block;src:url(data:font/woff2;base64,${fontB64}) format('woff2')}`;

const browser = await chromium.launch({
  executablePath,
  args: ['--no-sandbox', '--force-color-profile=srgb'],
});

async function shoot(html, width, height, out) {
  const page = await browser.newPage({ viewport: { width, height }, deviceScaleFactor: 1 });
  await page.setContent(html, { waitUntil: 'networkidle' });
  await page.screenshot({ path: join(pub, out), clipToViewport: true });
  await page.close();
  console.log('wrote', out, `${width}x${height}`);
}

// Icon tiles: the tomato centered on a transparent-ish tinted rounded square.
const iconHtml = (px) => `<!doctype html><html><head><meta charset="utf8">
<style>html,body{margin:0}body{width:${px}px;height:${px}px;display:flex;align-items:center;justify-content:center;background:#fffdfc}
.mark{width:${Math.round(px * 0.82)}px;height:${Math.round(px * 0.82)}px}</style></head>
<body><div class="mark">${favicon}</div></body></html>`;

await shoot(iconHtml(512), 512, 512, 'icon-512.png');
await shoot(iconHtml(180), 180, 180, 'apple-touch-icon.png');
await shoot(iconHtml(32), 32, 32, 'favicon-32.png');

// OG card — 1200x630, bold/bright brand, dark tomato background.
const og = `<!doctype html><html><head><meta charset="utf8">
<style>
  html,body{margin:0}
  __FONTFACE__
  body{width:1200px;height:630px;box-sizing:border-box;padding:80px;
    background:radial-gradient(120% 120% at 20% 10%, #2a1512 0%, #140f0e 60%);
    color:#fbeee9;font-family:'JetBrains Mono',ui-monospace,Menlo,monospace;
    display:flex;flex-direction:column;justify-content:space-between}
  .top{display:flex;align-items:center;gap:28px}
  .top .mark{width:120px;height:120px}
  .name{font-size:88px;font-weight:800;letter-spacing:-2px}
  .tag{font-size:44px;font-weight:700;line-height:1.15;max-width:1000px}
  .tag b{color:#ff6a54}
  .foot{display:flex;justify-content:space-between;align-items:center;font-size:30px;color:#cbb8b2}
  .pill{border:2px solid #3a2a26;border-radius:999px;padding:10px 26px;color:#fbeee9}
</style></head>
<body>
  <div class="top"><div class="mark">${favicon}</div><div class="name">Tomatick</div></div>
  <div class="tag">One menu bar icon. <b>Every timer you need.</b><br>Timer · Stopwatch · Alarm · Pomodoro for macOS.</div>
  <div class="foot"><span class="pill">Open source · MIT</span><span>tomatick.us</span></div>
</body></html>`.replace('__FONTFACE__', fontFace);

await shoot(og, 1200, 630, 'og.png');

await browser.close();

// Pack favicon.ico by embedding the 32x32 PNG (browsers accept PNG-in-ICO).
const png32 = readFileSync(join(pub, 'favicon-32.png'));
const header = Buffer.alloc(6);
header.writeUInt16LE(0, 0); // reserved
header.writeUInt16LE(1, 2); // type: icon
header.writeUInt16LE(1, 4); // image count
const entry = Buffer.alloc(16);
entry.writeUInt8(32, 0); // width
entry.writeUInt8(32, 1); // height
entry.writeUInt8(0, 2); // palette
entry.writeUInt8(0, 3); // reserved
entry.writeUInt16LE(1, 4); // color planes
entry.writeUInt16LE(32, 6); // bits per pixel
entry.writeUInt32LE(png32.length, 8); // size of image data
entry.writeUInt32LE(6 + 16, 12); // offset to image data
writeFileSync(join(pub, 'favicon.ico'), Buffer.concat([header, entry, png32]));
console.log('wrote favicon.ico', png32.length + 22, 'bytes');

console.log('done');
