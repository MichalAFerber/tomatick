import type { APIRoute } from 'astro';
import { SITE } from '../consts';

// Sitemap index pointing at the hand-rolled /sitemap.xml (see sitemap.xml.ts).
// §11 expects robots.txt and Search Console to consume /sitemap-index.xml.
export const GET: APIRoute = () => {
  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <sitemap><loc>${new URL('/sitemap.xml', SITE.url).href}</loc></sitemap>
</sitemapindex>
`;
  return new Response(xml, {
    headers: { 'Content-Type': 'application/xml; charset=utf-8' },
  });
};
