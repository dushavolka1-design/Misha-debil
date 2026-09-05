import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import test from 'node:test';

const srcRoot = join(dirname(fileURLToPath(import.meta.url)));

function read(rel: string): string {
  return readFileSync(join(srcRoot, rel), 'utf8');
}

test('Registration collects name, password confirm and optional photo', () => {
  const page = read('app/auth/register/page.tsx');
  assert.match(page, /display_name/);
  assert.match(page, /reg-name/);
  assert.match(page, /reg-password-confirm/);
  assert.match(page, /reg-avatar/);
  assert.match(page, /буква и цифра/);
});

test('Login uses username, not email', () => {
  const login = read('app/auth/login/LoginClient.tsx');
  assert.match(login, /login-username/);
  assert.match(login, /Имя пользователя/);
  assert.match(login, /username:/);
  assert.doesNotMatch(login, /login-email/);
  assert.doesNotMatch(login, /Укажите корректный email/);
});

test('Profile can update name and photo through existing cabinet', () => {
  const profile = read('app/app/profile/ProfileClient.tsx');
  assert.match(profile, /\/auth\/profile/);
  assert.match(profile, /display_name/);
  assert.match(profile, /avatar_data_url/);
  const shell = read('components/Shell.tsx');
  assert.match(shell, /\/auth\/me/);
  assert.match(shell, /has_avatar/);
});
