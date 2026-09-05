import { expect, test } from '@playwright/test';

test('billing cancel and account-delete paths are visible', async ({ page }) => {
  await page.goto('/app/billing');
  await expect(page.getByRole('button', { name: /Отменить автопродление/i })).toBeVisible();
  await expect(page.getByRole('button', { name: /Удалить способ оплаты/i })).toBeVisible();
  await expect(page.getByRole('link', { name: /Удаление аккаунта/i })).toBeVisible();
  await expect(page.getByLabel(/рекуррентные списания/i)).not.toBeChecked();
});

test('profile exposes billing cancel and account deletion without masking', async ({ page }) => {
  await page.goto('/app/profile');
  await expect(page.getByRole('tab', { name: /Подписка/i })).toBeVisible();
  await page.getByRole('tab', { name: /Подписка/i }).click();
  await expect(page.getByRole('link', { name: /Открыть подписку/i })).toBeVisible();
  await page.getByRole('tab', { name: /Экспорт \/ удаление/i }).click();
  await expect(page.getByRole('button', { name: /Запросить удаление/i })).toBeVisible();
});

test('entry wizard page loads with uncertainty honesty', async ({ page }) => {
  await page.goto('/app/entry-wizard');
  await expect(page.getByText(/въезд|мастер|не заменяет|помощник/i).first()).toBeVisible();
});
