import { expect, test } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import fs from 'fs';
import path from 'path';

import {
  API_BASE,
  DEMO_EMAIL,
  FIXTURES_DIR,
  SCREENSHOT_DIR,
  apiHealthy,
  loginDemo,
  registerAndLogin,
  saveScreenshot,
  uploadPdfAndWaitReady,
} from './helpers';

const leasePdf = path.join(FIXTURES_DIR, 'lease_contract.pdf');
const salePdf = path.join(FIXTURES_DIR, 'sale_contract.pdf');

test.describe('Prompt 8 — UI без API', () => {
  test('1. Landing 1440×1000: hero, две карточки, CTA, без пустого верхнего поля', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 1000 });
    await page.goto('/');
    const heroTitle = page.locator('#hero-title');
    await expect(heroTitle).toBeVisible();
    const box = await heroTitle.boundingBox();
    expect(box?.y ?? 999).toBeLessThan(220);
    await expect(page.getByRole('link', { name: /Проанализировать документ/i })).toBeVisible();
    await expect(page.getByRole('link', { name: /Создать документ/i })).toBeVisible();
    await expect(page.getByRole('link', { name: /Создать аккаунт/i }).first()).toBeVisible();
    await expect(page.getByRole('link', { name: /Зарегистрироваться/i })).toBeVisible();
    await saveScreenshot(page, '01-landing-1440');
  });

  test('2. Desktop navigation: только «Анализатор» и «Генерация», без sidebar', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 1000 });
    await page.goto('/app/analyzer');
    const nav = page.locator('nav.dar-main-nav');
    await expect(nav.getByRole('link', { name: 'Анализатор' })).toBeVisible();
    await expect(nav.getByRole('link', { name: 'Генерация' })).toBeVisible();
    await expect(nav.getByRole('link')).toHaveCount(2);
    await expect(page.locator('.dar-sidebar, aside.dar-sidebar')).toHaveCount(0);
  });

  test('3. Mobile navigation: два пункта, без horizontal overflow', async ({ page }) => {
    await page.setViewportSize({ width: 360, height: 800 });
    await page.goto('/app/analyzer');
    const mobileNav = page.locator('nav.dar-mobile-nav');
    await expect(mobileNav.getByRole('link', { name: 'Анализатор' })).toBeVisible();
    await expect(mobileNav.getByRole('link', { name: 'Генерация' })).toBeVisible();
    await expect(mobileNav.getByRole('link')).toHaveCount(2);
    const hasOverflow = await page.evaluate(
      () => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
    );
    expect(hasOverflow).toBeFalsy();
    await saveScreenshot(page, '08-mobile-analyzer-360');
    await page.goto('/app/generator');
    await saveScreenshot(page, '09-mobile-generator-360');
  });

  test('4. API выключен: понятная ошибка и retry', async ({ page }) => {
    await page.route('**/localhost:8000/**', (route) => route.abort('connectionfailed'));
    await page.route('**/127.0.0.1:8000/**', (route) => route.abort('connectionfailed'));
    await page.goto('/app/analyzer?tab=documents');
    await expect(page.getByRole('heading', { name: /Сервис анализа не запущен/i })).toBeVisible({
      timeout: 20_000,
    });
    await expect(page.getByRole('button', { name: /Повторить/i })).toBeVisible();
    await expect(page.locator('ul[role="list"]')).toHaveCount(0);
  });

  test('5. Регистрация: отдельные необязательные согласия', async ({ page }) => {
    await page.goto('/auth/register');
    for (const id of ['#reg-terms', '#reg-offer', '#reg-pd', '#reg-marketing']) {
      await expect(page.locator(id)).not.toBeChecked();
    }
    await expect(page.getByText('Отдельно даю согласие')).toBeVisible();
    await expect(page.getByText('необязательно')).toBeVisible();
  });

  test('axe: landing и analyzer без critical/serious', async ({ page }) => {
    for (const route of ['/', '/app/analyzer']) {
      await page.goto(route);
      const results = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa']).analyze();
      const serious = results.violations.filter((v) => ['serious', 'critical'].includes(v.impact || ''));
      expect(serious, JSON.stringify(serious, null, 2)).toEqual([]);
    }
  });

  test('visual regression: landing 1440×1000', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 1000 });
    await page.goto('/');
    await expect(page).toHaveScreenshot('landing-1440x1000.png', { fullPage: true, maxDiffPixelRatio: 0.03 });
  });
});

test.describe('Prompt 8 — полный стек (API)', () => {
  test.beforeAll(async ({ request }) => {
    if (!fs.existsSync(leasePdf) || !fs.existsSync(salePdf)) {
      throw new Error(`Запустите: python tests/fixtures/upload/build_fixtures.py (${FIXTURES_DIR})`);
    }
    if (!(await apiHealthy(request))) {
      test.skip(true, 'API на :8000 недоступен — запустите scripts/windows/start-dar.ps1');
    }
  });

  test.beforeEach(async ({ request }) => {
    if (!(await apiHealthy(request))) {
      test.skip(true, 'API недоступен');
    }
  });

  test('5b. Регистрация и вход через API + UI', async ({ page, request }) => {
    await registerAndLogin(page, request);
    await expect(page.getByRole('heading', { name: 'Анализатор' })).toBeVisible();
  });

  test('6–8. Upload synthetic PDF, анализ, citation, без demoReport', async ({ page, request }) => {
    await loginDemo(page);
    await page.goto('/app/analyzer?tab=new');
    await saveScreenshot(page, '02-analyzer-new');

    const input = page.locator('input[type="file"]');
    await input.setInputFiles(leasePdf);
    await page.getByRole('button', { name: /^Проанализировать$/i }).click();
    await expect(page.getByText(/Файл загружен|обработк/i).first()).toBeVisible({ timeout: 60_000 });
    await saveScreenshot(page, '03-analyzer-progress');

    await expect
      .poll(
        async () => {
          const body = await page.locator('body').innerText();
          return /7707083893|аренд|100\s*000/i.test(body);
        },
        { timeout: 180_000, intervals: [3_000, 6_000] },
      )
      .toBeTruthy();

    const html = await page.content();
    expect(html).not.toMatch(/demoReport/i);

    const finding = page.locator('.dar-finding-card, [class*="FindingCard"]').first();
    if (await finding.isVisible().catch(() => false)) {
      await finding.click();
      await expect(page.locator('.dar-doc-canvas, .dar-doc-line').first()).toBeVisible();
    }

    await saveScreenshot(page, '04-analyzer-result');
  });

  test('9. Restart: документ сохраняется после перезагрузки', async ({ page }) => {
    await loginDemo(page);
    const { documentId } = await uploadPdfAndWaitReady(page, leasePdf, 'lease_contract.pdf');
    await page.reload();
    await page.goto(`/app/analyzer?tab=documents&document=${documentId}`);
    await expect(page.getByText(/7707083893|аренд|lease/i).first()).toBeVisible({ timeout: 60_000 });
  });

  test('9b. Compare двух synthetic документов', async ({ page }) => {
    await loginDemo(page);
    await uploadPdfAndWaitReady(page, leasePdf, 'lease_contract.pdf');
    await uploadPdfAndWaitReady(page, salePdf, 'sale_contract.pdf');
    await page.goto('/app/analyzer?tab=compare');
    const checkboxes = page.locator('input[type="checkbox"]');
    const count = await checkboxes.count();
    expect(count).toBeGreaterThanOrEqual(2);
    await checkboxes.nth(0).check();
    await checkboxes.nth(1).check();
    await page.getByRole('button', { name: /Сравнить/i }).click();
    await expect(page.getByText(/различ|изменен|added|removed|Было|Стало/i).first()).toBeVisible({
      timeout: 60_000,
    });
    await saveScreenshot(page, '05-analyzer-compare');
  });

  test('10. Feedback вызывает API', async ({ page, request }) => {
    await loginDemo(page);
    await uploadPdfAndWaitReady(page, leasePdf, 'lease_contract.pdf');
    const feedbackPromise = page.waitForRequest(
      (req) => req.url().includes('/reports/feedback') && req.method() === 'POST',
    );
    await page.getByRole('button', { name: /^Полезно$/i }).first().click();
    const req = await feedbackPromise;
    expect(req.url()).toContain('/reports/feedback');
    const res = await request.post(req.url(), {
      headers: req.headers(),
      data: req.postDataJSON(),
    });
    expect([401, 403]).not.toContain(res.status());
  });

  test('11. Generator: 8 карточек и честные статусы', async ({ page, request }) => {
    await loginDemo(page);
    await page.goto('/app/generator?tab=templates');
    await expect
      .poll(async () => page.locator('ul li.dar-panel').count(), { timeout: 30_000 })
      .toBe(8);
    const cards = page.locator('ul li.dar-panel');
    await expect(cards.filter({ hasText: /Требует проверки|Опубликован/i })).toHaveCount(8);
    const formsRes = await request.get(`${API_BASE}/forms`);
    expect(formsRes.ok()).toBeTruthy();
    const forms = (await formsRes.json()) as Array<{
      status: string;
      form_kind: string;
      has_raw: boolean;
      content_sha256: string | null;
    }>;
    expect(forms).toHaveLength(8);
    const publishedGov = forms.filter((f) => f.status === 'published' && f.form_kind === 'government_form');
    for (const f of publishedGov) {
      expect(f.has_raw && f.content_sha256, `published gov form missing official raw/hash`).toBeTruthy();
    }
    await saveScreenshot(page, '06-generator-catalog');
  });

  test('12. Fill памятки сервиса: preview, validation, PDF', async ({ page, request }) => {
    await loginDemo(page);
    const formsRes = await request.get(`${API_BASE}/forms`);
    const forms = (await formsRes.json()) as Array<{ id: string; slug: string; fill_ready: boolean }>;
    const arrival = forms.find((f) => f.slug === 'mvd.arrival_notice.app4');
    expect(arrival?.fill_ready).toBeFalsy();
    const medical = forms.find((f) => f.slug === 'medical.visit.memo');
    expect(medical?.fill_ready).toBeTruthy();
    await page.goto(`/app/forms/${medical!.id}`);
    await page.locator('#visit_date').fill('2026-01-15');
    await page.locator('#questions').fill('Какие анализы нужны');
    await page.getByRole('button', { name: /Далее/i }).click();
    await page.getByRole('button', { name: /Далее/i }).click();
    await page.getByRole('button', { name: /Проверить поля/i }).click();
    await expect(page.getByText(/Поля прошли проверку/i)).toBeVisible({ timeout: 30_000 });
    await page.getByRole('button', { name: /Сгенерировать PDF/i }).click();
    await page.getByRole('button', { name: /Подтвердить и сгенерировать/i }).click();
    await saveScreenshot(page, '07-generator-fill');
  });

  test('13. Медицинский consent gate', async ({ page }) => {
    await loginDemo(page);
    await page.goto('/app/analyzer?tab=new');
    await page.locator('#upload-medical').check();
    const input = page.locator('input[type="file"]');
    await input.setInputFiles(leasePdf);
    await page.getByRole('button', { name: /^Проанализировать$/i }).click();
    await expect(page.getByText(/медицинск|согласие/i).first()).toBeVisible({ timeout: 15_000 });
    await expect(page.getByRole('dialog')).toBeVisible();
  });

  test('14. Запрет медсправки через direct API', async ({ request }) => {
    const login = await request.post(`${API_BASE}/auth/login`, {
      data: { email: DEMO_EMAIL, password: DEMO_PASSWORD },
    });
    expect(login.ok()).toBeTruthy();
    const cookie = login.headers()['set-cookie'] ?? '';
    const res = await request.post(`${API_BASE}/forms/medical/pdf`, {
      headers: { cookie },
      data: { kind: 'medical_certificate', title: 'X', body_lines: ['y'] },
    });
    expect(res.status()).toBeGreaterThanOrEqual(400);
    const body = await res.json();
    expect(body.detail?.code).toBe('forbidden_medical_artifact');
  });

  test('15. Удаление документа', async ({ page, request }) => {
    await loginDemo(page);
    const { documentId } = await uploadPdfAndWaitReady(page, leasePdf, 'lease_contract.pdf');
    await page.goto(`/app/analyzer?tab=documents&document=${documentId}`);
    await page.getByRole('button', { name: /^Удалить$/i }).click();
    await page.getByRole('button', { name: /Удалить навсегда/i }).click();
    await expect(page.getByText(/удалён|удален/i).first()).toBeVisible({ timeout: 30_000 });
    const docRes = await request.get(`${API_BASE}/documents/${documentId}`, {
      headers: { cookie: (await page.context().cookies()).map((c) => `${c.name}=${c.value}`).join('; ') },
    });
    expect([404, 403]).toContain(docRes.status());
  });
});

test.afterAll(async () => {
  fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
});
