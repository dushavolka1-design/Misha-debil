import { readdirSync } from 'node:fs';
import { createRequire } from 'node:module';
import { resolve } from 'node:path';
import { spawnSync } from 'node:child_process';
import { pathToFileURL } from 'node:url';

// Enumerate explicitly: sh, cmd and Node 20 disagree about ** expansion.
function collect(directory) {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const path = resolve(directory, entry.name);
    if (entry.isSymbolicLink()) throw new Error(`Refusing test-tree symlink: ${path}`);
    if (entry.isDirectory()) return collect(path);
    return /\.test\.(?:[cm]?[jt]s|[jt]sx)$/.test(entry.name) ? [path] : [];
  });
}

try {
  const files = collect(resolve('src')).sort();
  if (files.length === 0) throw new Error('No test files found under src');
  const args = [];
  if (files.some((file) => /\.(?:[cm]?ts|tsx)$/.test(file))) {
    const require = createRequire(resolve('package.json'));
    args.push('--import', pathToFileURL(require.resolve('tsx')).href);
  }
  console.log(`Running ${files.length} test files (recursive, including src root)`);
  const result = spawnSync(process.execPath, [...args, '--test', ...files], {
    cwd: process.cwd(),
    stdio: 'inherit',
    shell: false,
  });
  if (result.error) throw result.error;
  if (result.signal) console.error(`Test process terminated by ${result.signal}`);
  process.exitCode = result.status ?? 1;
} catch (error) {
  console.error(error);
  process.exitCode = 1;
}
