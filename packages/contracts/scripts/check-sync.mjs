import { createHash } from 'node:crypto';
import { mkdtempSync, readFileSync, existsSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const openapiPath = join(root, 'openapi', 'openapi.json');
const generatedPath = join(root, 'src', 'generated', 'openapi.ts');
const bin = join(
  root,
  'node_modules',
  '.bin',
  process.platform === 'win32' ? 'openapi-typescript.cmd' : 'openapi-typescript',
);

if (!existsSync(openapiPath) || !existsSync(generatedPath)) {
  console.error('Missing openapi.json or generated openapi.ts');
  process.exit(1);
}

const tmpDir = mkdtempSync(join(tmpdir(), 'dar-contracts-'));
const tmpOut = join(tmpDir, 'openapi.ts');

try {
  const gen = spawnSync(bin, [openapiPath, '-o', tmpOut], {
    cwd: root,
    encoding: 'utf8',
    shell: process.platform === 'win32',
  });
  if (gen.status !== 0) {
    console.error(gen.stdout);
    console.error(gen.stderr);
    console.error('failed to run', bin);
    process.exit(gen.status ?? 1);
  }

  const normalize = (s) => s.replace(/\r\n/g, '\n').trim();
  const expected = normalize(readFileSync(tmpOut, 'utf8'));
  const actual = normalize(readFileSync(generatedPath, 'utf8'));
  if (expected !== actual) {
    console.error('OpenAPI TypeScript contracts are out of sync. Run: pnpm contracts:generate');
    process.exit(1);
  }
  console.log('contracts sync ok', createHash('sha256').update(actual).digest('hex').slice(0, 12));
} finally {
  rmSync(tmpDir, { recursive: true, force: true });
}
