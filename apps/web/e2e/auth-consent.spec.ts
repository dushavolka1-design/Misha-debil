import { expect, test } from '@playwright/test';

test('registration checkboxes are unchecked and PD is separate', async ({ page }) => {
  await page.goto('/auth/register');
  for (const id of ['#reg-terms', '#reg-offer', '#reg-pd', '#reg-marketing']) {
    await expect(page.locator(id)).not.toBeChecked();
  }
  await expect(page.getByText('Отдельно даю согласие')).toBeVisible();
  await expect(page.getByText('необязательно')).toBeVisible();
  // No single bundled checkbox for all legal docs
  await expect(page.getByText('пользовательское соглашение')).toBeVisible();
  await expect(page.getByRole('link', { name: /оферт/i })).toBeVisible();
});

test('billing cancel is visible without support contact requirement', async ({ page }) => {
  await page.goto('/app/billing');
  await expect(page.getByRole('button', { name: /Отменить автопродление/i })).toBeVisible();
  await expect(page.getByText(/не маскируются|один поток|Отмена/i).first()).toBeVisible();
  await expect(page.getByLabel(/рекуррентные списания/i)).not.toBeChecked();
});

test('analyzer result shows disclaimer that does not waive mandatory rights', async ({ page }) => {
  await page.goto('/app/analyzer');
  await expect(page.getByText(/информационный помощник|не оказывает юридическую/i).first()).toBeVisible();
});
