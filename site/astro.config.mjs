import { defineConfig } from 'astro/config';
import tailwind from '@astrojs/tailwind';

// tomatick.us — static Astro output for Cloudflare Pages.
// Sitemap is a hand-rolled endpoint (src/pages/sitemap.xml.ts) — deterministic
// for a handful of pages and avoids the sitemap integration's build quirks.
export default defineConfig({
  site: 'https://tomatick.us',
  trailingSlash: 'ignore',
  integrations: [
    tailwind({ applyBaseStyles: false }), // base styles live in src/styles/global.css
  ],
  build: {
    // Emit clean directory URLs (/docs/ -> /docs/index.html).
    format: 'directory',
  },
  // No client JS framework/islands — keeps CSP tight (script-src needs only
  // 'self' 'unsafe-inline' for the theme-init snippet, plus Plausible).
});
