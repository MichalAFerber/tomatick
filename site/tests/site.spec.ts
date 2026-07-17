import { test, expect, type Page } from '@playwright/test';

const PAGES = ['/', '/docs/', '/privacy/', '/terms/'];

// Only the self-hosted Plausible instance is allowed to be unreachable in this
// sandbox (§15 analytics noise = pass). Everything else must load. We split
// signals: console errors catch CSP violations ("Refused to…") and JS errors;
// the network watch catches broken *local* assets (a 404 font would fail here).
const PLAUSIBLE = 'plausible.thompsonblack.us';

function watch(page: Page) {
  const consoleErrors: string[] = [];
  const resourceFailures: string[] = [];
  page.on('console', (msg) => {
    if (msg.type() !== 'error') return;
    const text = msg.text();
    const url = msg.location()?.url || '';
    // "Failed to load resource" lines carry no CSP detail — the network watch
    // below judges those. Keep genuine errors (CSP "Refused to…", JS throws).
    if (/failed to load resource/i.test(text)) return;
    if (`${text} ${url}`.includes(PLAUSIBLE)) return;
    consoleErrors.push(text);
  });
  page.on('pageerror', (err) => consoleErrors.push(`pageerror: ${err.message}`));
  page.on('requestfailed', (req) => {
    if (!req.url().includes(PLAUSIBLE)) resourceFailures.push(`FAILED ${req.url()}`);
  });
  page.on('response', (res) => {
    if (res.status() >= 400 && !res.url().includes(PLAUSIBLE)) {
      resourceFailures.push(`${res.status()} ${res.url()}`);
    }
  });
  return { consoleErrors, resourceFailures };
}

for (const path of PAGES) {
  test(`${path} loads clean under production CSP`, async ({ page }) => {
    const { consoleErrors, resourceFailures } = watch(page);
    const resp = await page.goto(path, { waitUntil: 'load' });
    expect(resp?.status(), `HTTP status for ${path}`).toBe(200);

    // Real CSP header is served and strict.
    const csp = resp?.headers()['content-security-policy'] || '';
    expect(csp, `CSP on ${path}`).toContain("default-src 'none'");
    expect(csp).not.toContain("'unsafe-eval'");

    // Exactly one h1, canonical present.
    await expect(page.locator('h1')).toHaveCount(1);
    await expect(page.locator('link[rel="canonical"]')).toHaveCount(1);

    // No Google Fonts anywhere. §1
    const html = await page.content();
    expect(html).not.toContain('fonts.googleapis.com');
    expect(html).not.toContain('fonts.gstatic.com');

    // No CSP violations / unexpected console errors, and every local asset loaded.
    expect(consoleErrors, `console errors on ${path}: ${consoleErrors.join(' | ')}`).toEqual([]);
    expect(resourceFailures, `broken resources on ${path}: ${resourceFailures.join(' | ')}`).toEqual([]);
  });
}

test('footer carries the exact ❤️ credit line and Octocat', async ({ page }) => {
  await page.goto('/');
  const footer = page.locator('footer');
  await expect(footer).toContainText('Created with ❤️ by');
  await expect(footer).toContainText('Michal Ferber');
  await expect(footer).toContainText('TechGuyWithABeard');
  await expect(footer.locator('svg')).not.toHaveCount(0); // logo + github mark
});

test('header links to the repo and offers a download', async ({ page }) => {
  await page.goto('/');
  await expect(page.locator('header a[href*="github.com/MichalAFerber/tomatick"]')).not.toHaveCount(0);
  await expect(page.locator('a[href*="/releases"]')).not.toHaveCount(0);
});

test('theme toggle flips and persists', async ({ page }) => {
  await page.goto('/');
  const html = page.locator('html');
  const toggle = page.locator('#theme-toggle');
  await toggle.click();
  const theme = await html.getAttribute('data-theme');
  expect(['dark', 'light']).toContain(theme);
  expect(await toggle.getAttribute('aria-pressed')).toBe(theme === 'dark' ? 'true' : 'false');
  // Persisted for next load.
  await page.reload();
  expect(await page.locator('html').getAttribute('data-theme')).toBe(theme);
});

test('unknown URL returns branded 404', async ({ page }) => {
  const resp = await page.goto('/definitely-not-a-page/');
  expect(resp?.status()).toBe(404);
  await expect(page.locator('h1')).toContainText('404');
});

test('SEO essentials present on home', async ({ page }) => {
  await page.goto('/');
  await expect(page.locator('meta[property="og:image"]')).toHaveAttribute('content', /og\.png$/);
  await expect(page.locator('meta[name="twitter:card"]')).toHaveAttribute('content', 'summary_large_image');
  await expect(page.locator('meta[name="twitter:creator"]')).toHaveAttribute('content', '@michalaferber');
  await expect(page.locator('script[type="application/ld+json"]')).not.toHaveCount(0);
});
