// Site-wide constants — single source of truth for identity & SEO.
export const SITE = {
  name: 'Tomatick',
  domain: 'tomatick.us',
  url: 'https://tomatick.us',
  tagline: 'A menu bar timer, stopwatch, alarm & pomodoro — now a single Go binary.',
  description:
    'A menu bar timer, stopwatch, alarm and pomodoro in one icon, with a timestamped ' +
    'history of every run. Rewritten in Go as a single binary. Open source, MIT, no tracking.',
  // The Go rewrite (tomatick2) is the current product and where releases ship from.
  // This repo (tomatick) still hosts the site and the original macOS-only Python app.
  repo: 'https://github.com/MichalAFerber/tomatick2',
  releases: 'https://github.com/MichalAFerber/tomatick2/releases',
  legacyRepo: 'https://github.com/MichalAFerber/tomatick',
  author: 'Michal Ferber',
  authorUrl: 'https://michalferber.dev/',
  brandUrl: 'https://techguywithabeard.com/',
  twitterCreator: '@michalaferber',
  plausibleSrc:
    'https://plausible.thompsonblack.us/js/script.outbound-links.file-downloads.tagged-events.js',
  ogImage: '/og.png',
} as const;

// Contact routing. SUPPORT_EMAIL is what the page shows when the form is not
// yet active; MAILER_PRODUCT is the herald registry slug the mailer keys its
// per-product config on (from address, recipient, Origin allowlist, Turnstile
// secret). Both must match the registry row for slug `tomatick_us`.
export const SUPPORT_EMAIL = 'support@tomatick.us';
export const MAILER_PRODUCT = 'tomatick_us';

// Product footer nav (§1 product-site footer variant).
export const NAV = {
  product: [
    { label: 'Quick Start', href: '/docs/' },
    { label: 'Download', href: SITE.releases, external: true },
    { label: 'Source', href: SITE.repo, external: true },
  ],
  about: [
    { label: 'Contact', href: '/contact/' },
    { label: 'Privacy', href: '/privacy/' },
    { label: 'Terms', href: '/terms/' },
  ],
} as const;
