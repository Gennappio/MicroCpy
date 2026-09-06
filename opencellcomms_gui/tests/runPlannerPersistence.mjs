import { build } from 'esbuild';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';

const directory = mkdtempSync(join(tmpdir(), 'occ-planner-test-'));
try {
  const outfile = join(directory, 'test.mjs');
  await build({ entryPoints: [fileURLToPath(new URL('./plannerPersistence.js', import.meta.url))],
    bundle: true, platform: 'node', format: 'esm', define: { 'import.meta.env': '{}' }, outfile });
  const result = spawnSync(process.execPath, [outfile], { stdio: 'inherit' });
  process.exitCode = result.status ?? 1;
} finally {
  rmSync(directory, { recursive: true, force: true });
}
