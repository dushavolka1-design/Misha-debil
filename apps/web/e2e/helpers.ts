import { APIRequestContext, Page, expect } from '@playwright/test';
import fs from 'fs';
import path from 'path';

export const API_BASE = process.env.E2E_API_BASE_URL ?? 'http://127.0.0.1:8000';
export const FIXTURES_DIR = path.resolve(__dirname, '../../../tests/fixtures/upload');
export const SCREENSHOT_DIR = path.resolve(__dirname, '../../../artifacts/screenshots/prompt8');

export const DEMO_EMAIL = 'demo@document-analyzer-rf.local';
export const DEMO_PASSWORD = 'Demo-Password-12';
export const DEMO_USERNAME = 'Демо';

export async function apiHealthy(request: APIRequestContext): Promise<boolean> {
  try {
    const res = await request.get(`${API_BASE}/health`, { timeout: 5_000 });
    return res.ok();
  } catch {
    return false;
  }
}

export async function loginDemo(page: Page): Promise<void> {
  await page.goto('/auth/login');
  await page.locator('#login-username').fill(DEMO_USERNAME);
  await page.locator('#login-password').fill(DEMO_PASSWORD);
  await page.getByRole('button', { name: /^Войти$/i }).click();
  await page.waitForURL('**/app/analyzer**', { timeout: 30_000 });
}

export async function registerAndLogin(page: Page, request: APIRequestContext): Promise<string> {
  const email = `e2e-${Date.now()}@prompt8.test`;
  const password = 'Correct-Horse-12';

  const legalRes = await request.get(`${API_BASE}/legal/documents/active`);
  expect(legalRes.ok()).toBeTruthy();
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

  await page.goto('/auth/register');
  for (const id of ['#reg-terms', '#reg-offer', '#reg-pd', '#reg-marketing']) {
    await expect(page.locator(id)).not.toBeChecked();
  }

  const reg = await request.post(`${API_BASE}/auth/register`, {
    data: { email, password, display_name: 'Тест Пользователь', locale: 'ru-RU', accepts },
  });
  expect(reg.ok()).toBeTruthy();
  const regBody = (await reg.json()) as { verification_token_dev?: string };
  if (regBody.verification_token_dev) {
    await request.post(`${API_BASE}/auth/verify-email`, {
      data: { token: regBody.verification_token_dev },
    });
  }

  await page.goto('/auth/login');
  await page.locator('#login-username').fill('Тест Пользователь');
  await page.locator('#login-password').fill(password);
  await page.getByRole('button', { name: /^Войти$/i }).click();
  await page.waitForURL('**/app/analyzer**', { timeout: 30_000 });
  return email;
}

export async function uploadPdfAndWaitReady(
  page: Page,
  filePath: string,
  displayName: string,
): Promise<{ documentId: string; runId: string }> {
  await page.goto('/app/analyzer?tab=new');
  const input = page.locator('input[type="file"]');
  await input.setInputFiles(filePath);
  await page.getByRole('button', { name: /^Проанализировать$/i }).click();

  await expect(page.getByText(/Файл загружен|обработк/i).first()).toBeVisible({ timeout: 60_000 });

  await expect(page.getByRole('button', { name: /Открыть результат/i })).toBeVisible({ timeout: 180_000 });
  await page.getByRole('button', { name: /Открыть результат/i }).click();

  const url = page.url();
  const docMatch = url.match(/document=([^&]+)/);
  const runMatch = url.match(/run=([^&]+)/);
  if (docMatch?.[1] && runMatch?.[1]) {
    return { documentId: docMatch[1], runId: runMatch[1] };
  }

  await page.goto('/app/analyzer?tab=documents');
  await expect(page.getByText(displayName).first()).toBeVisible({ timeout: 30_000 });
  await page.getByText(displayName).first().click();
  const finalUrl = page.url();
  const d = finalUrl.match(/document=([^&]+)/);
  const r = finalUrl.match(/run=([^&]+)/);
  expect(d?.[1]).toBeTruthy();
  expect(r?.[1]).toBeTruthy();
  return { documentId: d![1], runId: r![1] };
}

export async function saveScreenshot(page: Page, name: string): Promise<void> {
  fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
  await page.screenshot({ path: path.join(SCREENSHOT_DIR, `${name}.png`), fullPage: true });
}
