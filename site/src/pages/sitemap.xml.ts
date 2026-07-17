import type { APIRoute } from 'astro';
import { SITE } from '../consts';

// Indexable URLs. Keep in sync with pages (noindex 404 excluded).
const PATHS = ['/', '/docs/', '/privacy/', '/terms/'];

export const GET: APIRoute = () => {
  const urls = PATHS.map(
    (p) => `  <url><loc>${new URL(p, SITE.url).href}</loc></url>`,
  ).join('\n');
  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${urls}
</urlset>
`;
  return new Response(xml, {
    headers: { 'Content-Type': 'application/xml; charset=utf-8' },
  });
};
