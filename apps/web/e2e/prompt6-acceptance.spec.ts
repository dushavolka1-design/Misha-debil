import { expect, test, type APIRequestContext, type Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import fs from 'fs';
import path from 'path';

const SHOT_DIR = path.resolve(__dirname, '../../../artifacts/prompt6/screenshots');
const EMOJI_RE = /\p{Extended_Pictographic}/u;
const API = process.env.E2E_API_BASE_URL || 'http://127.0.0.1:8000';
const WEB = process.env.PLAYWRIGHT_BASE_URL || process.env.E2E_WEB_BASE_URL || 'http://127.0.0.1:3000';

function parseWeight(value: string): number {
  const n = Number.parseInt(value, 10);
  if (Number.isFinite(n)) return n;
  if (value === 'bold') return 700;
  if (value === 'medium') return 500;
  if (value === 'normal') return 400;
  return 0;
}

async function saveShot(page: Page, name: string): Promise<string> {
  fs.mkdirSync(SHOT_DIR, { recursive: true });
  const dest = path.join(SHOT_DIR, `${name}.png`);
  await page.screenshot({ path: dest, fullPage: true });
  return dest;
}

async function sessionLogin(page: Page, request: APIRequestContext): Promise<void> {
  const email = `p6-${Date.now()}@example.com`;
  const password = 'Correct-Horse-12';
  const legalRes = await request.get(`${API}/legal/documents/active`);
  expect(legalRes.ok(), `legal ${legalRes.status()} ${await legalRes.text()}`).toBeTruthy();
  const legal = (await legalRes.json()) as Array<{
    consent_id: string;
    consent_version: string;
    content_hash: string;
  }>;
  const byId = Object.fromEntries(legal.map((l) => [l.consent_id, l]));
  const accepts = ['terms_of_use', 'offer', 'personal_data_processing'].map((key) => ({
    consent_id: byId[key].consent_id,
    consent_version: byId[key].consent_version,
    content_hash: byId[key].content_hash,
  }));
  const reg = await request.post(`${API}/auth/register`, {
    data: { email, password, display_name: 'Тест Пользователь', locale: 'ru-RU', accepts },
  });
  expect(reg.ok(), `register ${reg.status()} ${await reg.text()}`).toBeTruthy();
  const regBody = (await reg.json()) as { verification_token_dev?: string };
  if (regBody.verification_token_dev) {
    const verify = await request.post(`${API}/auth/verify-email`, {
      data: { token: regBody.verification_token_dev },
    });
    expect(verify.ok(), await verify.text()).toBeTruthy();
  }
  const login = await request.post(`${API}/auth/login`, { data: { email, password } });
  expect(login.ok(), `login ${login.status()} ${await login.text()}`).toBeTruthy();
  const setCookie = login.headers()['set-cookie'] ?? '';
  const match = /dar_session=([^;]+)/.exec(setCookie);
  expect(match, `set-cookie: ${setCookie}`).toBeTruthy();
  const value = decodeURIComponent(match![1]);
  await page.context().addCookies([
    { name: 'dar_session', value, url: API },
    { name: 'dar_session', value, url: WEB },
  ]);
}

test.describe.configure({ mode: 'serial' });
test.setTimeout(120_000);

test.describe('Prompt 6 — visual acceptance', () => {
  test.beforeEach(async ({ page, request }) => {
    await sessionLogin(page, request);
  });

  test('p6_27_body_font_size', async ({ page }) => {
    await page.goto('/app/analyzer');
    const size = await page.evaluate(() => parseFloat(getComputedStyle(document.body).fontSize));
    expect(size).toBeGreaterThanOrEqual(16);
    fs.mkdirSync(SHOT_DIR, { recursive: true });
    fs.writeFileSync(path.join(SHOT_DIR, 't27-body-font.json'), JSON.stringify({ fontSize: size }));
  });

  test('p6_28_body_font_weight', async ({ page }) => {
    await page.goto('/app/analyzer');
    const weight = await page.evaluate(() => getComputedStyle(document.body).fontWeight);
    expect(parseWeight(weight)).toBeGreaterThanOrEqual(500);
    fs.writeFileSync(path.join(SHOT_DIR, 't28-body-weight.json'), JSON.stringify({ fontWeight: weight }));
  });

  test('p6_29_secondary_important_text', async ({ page }) => {
    await page.goto('/app/analyzer');
    const samples = await page.evaluate(() => {
      const nodes = [
        ...Array.from(document.querySelectorAll('nav.dar-main-nav a, nav.dar-mobile-nav a')),
        ...Array.from(document.querySelectorAll('.dar-btn, .dar-muted, h1, h2, .dar-h1, .dar-h2')),
      ];
      return nodes.slice(0, 40).map((el) => {
        const cs = getComputedStyle(el);
        return {
          tag: el.tagName,
          text: (el.textContent || '').trim().slice(0, 80),
          fontSize: parseFloat(cs.fontSize),
          fontWeight: cs.fontWeight,
        };
      });
    });
    const important = samples.filter((s) => s.text.length > 0);
    expect(important.length).toBeGreaterThan(0);
    for (const sample of important) {
      expect(sample.fontSize, JSON.stringify(sample)).toBeGreaterThanOrEqual(14);
      expect(parseWeight(sample.fontWeight), JSON.stringify(sample)).toBeGreaterThanOrEqual(500);
    }
    fs.writeFileSync(path.join(SHOT_DIR, 't29-secondary.json'), JSON.stringify(important, null, 2));
  });

  test('p6_30_two_primary_tabs', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto('/app/analyzer');
    const nav = page.locator('nav.dar-main-nav');
    await expect(nav.getByRole('link', { name: 'Анализатор' })).toBeVisible();
    await expect(nav.getByRole('link', { name: 'Генерация' })).toBeVisible();
    await expect(nav.getByRole('link')).toHaveCount(2);
    await nav.getByRole('link', { name: 'Генерация' }).click();
    await expect(page).toHaveURL(/\/app\/generator/);
    await nav.getByRole('link', { name: 'Анализатор' }).click();
    await expect(page).toHaveURL(/\/app\/analyzer/);
  });

  test('p6_31_no_sidebar', async ({ page }) => {
    await page.goto('/app/analyzer');
    await expect(page.locator('.dar-sidebar, aside.dar-sidebar, [data-sidebar]')).toHaveCount(0);
    await page.goto('/app/generator');
    await expect(page.locator('.dar-sidebar, aside.dar-sidebar, [data-sidebar]')).toHaveCount(0);
  });

  test('p6_32_no_emoji', async ({ page }) => {
    await page.goto('/app/analyzer');
    const analyzerText = await page.locator('body').innerText();
    expect(EMOJI_RE.test(analyzerText)).toBeFalsy();
    await page.goto('/app/generator');
    const generatorText = await page.locator('body').innerText();
    expect(EMOJI_RE.test(generatorText)).toBeFalsy();
    const visible = `${analyzerText}\n${generatorText}`;
    expect(visible).not.toMatch(/\b(raw|fixture|fill version|needs_review|approved)\b/);
  });

  test('p6_33_no_horizontal_overflow', async ({ page }) => {
    for (const width of [360, 768, 1440, 1920]) {
      await page.setViewportSize({ width, height: 900 });
      await page.goto('/app/analyzer');
      const overflow = await page.evaluate(
        () => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
      );
      expect(overflow, `overflow at ${width}`).toBeFalsy();
      await page.goto('/app/generator');
      const overflowGen = await page.evaluate(
        () => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
      );
      expect(overflowGen, `generator overflow at ${width}`).toBeFalsy();
    }
  });

  test('p6_34_axe_no_serious_critical', async ({ page }) => {
    for (const route of ['/', '/app/analyzer', '/app/generator']) {
      await page.goto(route);
      const results = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa']).analyze();
      const serious = results.violations.filter((v) => ['serious', 'critical'].includes(v.impact || ''));
      expect(serious, `${route}: ${JSON.stringify(serious, null, 2)}`).toEqual([]);
    }
  });

  test('p6_35_visual_screenshots', async ({ page }) => {
    const widths = [360, 768, 1440, 1920];
    for (const width of widths) {
      await page.setViewportSize({ width, height: width >= 1440 ? 1000 : 800 });
      await page.goto('/app/analyzer');
      await saveShot(page, `analyzer-${width}`);
      await page.goto('/app/generator?tab=templates');
      await saveShot(page, `generator-${width}`);
    }
    await page.setViewportSize({ width: 1440, height: 1000 });
    await page.goto('/');
    await saveShot(page, 'landing-1440');
    const files = widths.flatMap((w) => [`analyzer-${w}.png`, `generator-${w}.png`]);
    for (const name of files) {
      expect(fs.existsSync(path.join(SHOT_DIR, name)), name).toBeTruthy();
    }
  });
});
