import { defineConfig } from 'astro/config';

// tomatick.us — static Astro output for Cloudflare Pages.
// Tailwind 3 runs as a plain PostCSS plugin (postcss.config.mjs) — the
// @astrojs/tailwind integration is deprecated and tops out at Astro 6.
// Sitemap is a hand-rolled endpoint (src/pages/sitemap.xml.ts) — deterministic
// for a handful of pages and avoids the sitemap integration's build quirks.
export default defineConfig({
  site: 'https://tomatick.us',
  trailingSlash: 'ignore',
  // Astro 7 defaults to 'jsx' (React-style whitespace stripping); keep the
  // pre-v7 behavior so spacing between inline elements is unchanged.
  compressHTML: true,
  build: {
    // Emit clean directory URLs (/docs/ -> /docs/index.html).
    format: 'directory',
  },
  // No client JS framework/islands — keeps CSP tight (script-src needs only
  // 'self' 'unsafe-inline' for the theme-init snippet, plus Plausible).
});
