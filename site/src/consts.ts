// Site-wide constants — single source of truth for identity & SEO.
export const SITE = {
  name: 'Tomatick',
  domain: 'tomatick.us',
  url: 'https://tomatick.us',
  tagline: 'A macOS menu bar timer, stopwatch, alarm & pomodoro.',
  description:
    'A macOS menu bar timer, stopwatch, alarm and pomodoro in one icon, with a timestamped ' +
    'history of every run. Open source, MIT, no tracking.',
  repo: 'https://github.com/MichalAFerber/tomatick',
  releases: 'https://github.com/MichalAFerber/tomatick/releases',
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
export const SUPPORT_EMAIL = 'michal@tomatick.us';
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
    { label: 'GitHub', href: SITE.repo, external: true },
  ],
} as const;
