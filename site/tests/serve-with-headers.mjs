// Static server for dist/ that applies the real Cloudflare Pages `_headers`
// (CSP etc.) to every response — so the Playwright harness exercises the site
// under production security headers. §15
import { createServer } from 'node:http';
import { readFile, stat } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { dirname, join, normalize, extname } from 'node:path';

const here = dirname(fileURLToPath(import.meta.url));
const dist = join(here, '..', 'dist');
const PORT = Number(process.env.PORT || 4321);

const TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.ico': 'image/x-icon',
  '.woff2': 'font/woff2',
  '.xml': 'application/xml; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.webmanifest': 'application/manifest+json',
  '.txt': 'text/plain; charset=utf-8',
};

// Parse the /* header block out of dist/_headers.
async function loadGlobalHeaders() {
  const headers = {};
  try {
    const raw = await readFile(join(dist, '_headers'), 'utf8');
    const lines = raw.split('\n');
    let inStar = false;
    for (const line of lines) {
      if (/^\S/.test(line)) {
        inStar = line.trim() === '/*';
        continue;
      }
      if (inStar && line.includes(':')) {
        const idx = line.indexOf(':');
        headers[line.slice(0, idx).trim()] = line.slice(idx + 1).trim();
      }
    }
  } catch {}
  return headers;
}

const GLOBAL_HEADERS = await loadGlobalHeaders();

async function resolvePath(urlPath) {
  let p = decodeURIComponent(urlPath.split('?')[0]);
  p = normalize(p).replace(/^(\.\.[/\\])+/, '');
  let file = join(dist, p);
  try {
    const s = await stat(file);
    if (s.isDirectory()) file = join(file, 'index.html');
    return file;
  } catch {
    // Directory URL without trailing slash, or clean route.
    try {
      const idx = join(dist, p, 'index.html');
      await stat(idx);
      return idx;
    } catch {
      return null;
    }
  }
}

const server = createServer(async (req, res) => {
  const filePath = await resolvePath(req.url || '/');
  const send = (status, body, type) => {
    res.writeHead(status, { ...GLOBAL_HEADERS, 'Content-Type': type });
    res.end(body);
  };
  if (!filePath) {
    try {
      const body = await readFile(join(dist, '404.html'));
      return send(404, body, TYPES['.html']);
    } catch {
      return send(404, 'Not found', 'text/plain');
    }
  }
  try {
    const body = await readFile(filePath);
    send(200, body, TYPES[extname(filePath)] || 'application/octet-stream');
  } catch {
    send(500, 'Server error', 'text/plain');
  }
});

server.listen(PORT, () => {
  console.log(`serving dist/ with production headers on http://localhost:${PORT}`);
});
