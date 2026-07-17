// Site-wide constants — single source of truth for identity & SEO.
export const SITE = {
  name: 'Tomatick',
  domain: 'tomatick.us',
  url: 'https://tomatick.us',
  tagline: 'A macOS menu bar timer, stopwatch, alarm & pomodoro.',
  description:
    'Tomatick is a macOS menu bar timer, stopwatch, alarm and pomodoro — all in one icon, ' +
    'with a timestamped history of everything you run. Open source, MIT, no tracking that leaves your Mac.',
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

// Product footer nav (§1 product-site footer variant).
export const NAV = {
  product: [
    { label: 'Quick Start', href: '/docs/' },
    { label: 'Download', href: SITE.releases, external: true },
    { label: 'Source', href: SITE.repo, external: true },
  ],
  about: [
    { label: 'Privacy', href: '/privacy/' },
    { label: 'Terms', href: '/terms/' },
    { label: 'GitHub', href: SITE.repo, external: true },
  ],
} as const;
