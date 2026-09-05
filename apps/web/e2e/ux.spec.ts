import { expect, test } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

const routes = [
  '/',
  '/auth/login',
  '/auth/register',
  '/app/analyzer',
  '/app/generator',
  '/app/billing',
  '/app/profile',
];

for (const route of routes) {
  test(`no horizontal overflow @360 ${route}`, async ({ page }) => {
    await page.setViewportSize({ width: 360, height: 800 });
    await page.goto(route);
    const hasOverflow = await page.evaluate(() => {
      return document.documentElement.scrollWidth > document.documentElement.clientWidth + 1;
    });
    expect(hasOverflow).toBeFalsy();
  });
}

test('keyboard can reach primary CTA on landing', async ({ page }) => {
  await page.goto('/');
  await page.keyboard.press('Tab');
  // skip link or first focusable
  for (let i = 0; i < 8; i += 1) {
    const focused = page.locator(':focus');
    const text = await focused.textContent();
    if (text && /Начать|Создать аккаунт|Войти/i.test(text)) {
      expect(text.length).toBeGreaterThan(0);
      return;
    }
    await page.keyboard.press('Tab');
  }
  throw new Error('Primary CTA not reachable by keyboard');
});

test('axe critical/serious on landing and analyzer', async ({ page }) => {
  for (const route of ['/', '/app/analyzer']) {
    await page.goto(route);
    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa'])
      .analyze();
    const serious = results.violations.filter((v) =>
      ['serious', 'critical'].includes(v.impact || ''),
    );
    expect(serious, JSON.stringify(serious, null, 2)).toEqual([]);
  }
});

test('visual snapshots key screens', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto('/');
  await expect(page).toHaveScreenshot('landing-1440.png', { fullPage: true, maxDiffPixelRatio: 0.03 });
  await page.setViewportSize({ width: 768, height: 900 });
  await page.goto('/app/analyzer');
  await expect(page).toHaveScreenshot('analyzer-768.png', {
    fullPage: true,
    maxDiffPixelRatio: 0.04,
  });
});
