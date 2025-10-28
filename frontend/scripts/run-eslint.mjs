#!/usr/bin/env node
// Programmatic ESLint runner to avoid PowerShell argument parsing quirks on Windows.
// Uses Flat config by default if eslint.config.js is present at project root (frontend/).

import { ESLint } from 'eslint';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import fs from 'node:fs';

async function main() {
  const __dirname = path.dirname(fileURLToPath(import.meta.url));
  const root = path.resolve(__dirname, '..');

  // Determine patterns: lint src with common extensions
  const patterns = [
    'src/**/*.{ts,tsx,js,vue}',
  ];

  // Ensure we execute from frontend root so ESLint discovers eslint.config.js (flat config)
  process.chdir(root);

  // Let ESLint auto-discover flat config by default
  const eslint = new ESLint({
    // Enable caching for speed on repeated runs
    cache: true,
    cacheLocation: path.join('.eslintcache'),
    // Respect ignore files and flat ignores
    errorOnUnmatchedPattern: false,
  });

  const results = await eslint.lintFiles(patterns);
  // Apply fixes if any rule is configured with --fix in config (we don't auto-fix here)
  // await ESLint.outputFixes(results);

  const formatter = await eslint.loadFormatter('stylish');
  const resultText = formatter.format(results);

  if (resultText && resultText.trim().length > 0) {
    console.log(resultText);
  }

  // Compute counts
  let errorCount = 0;
  let warningCount = 0;
  for (const r of results) {
    errorCount += (r.errorCount || 0) + (r.fatalErrorCount || 0);
    warningCount += r.warningCount || 0;
  }

  // Exit with 0 on no errors; warnings allowed (verify step treats non-zero as WARN)
  if (errorCount > 0) {
    process.exit(2);
  } else {
    process.exit(0);
  }
}

main().catch((err) => {
  // Print a concise error without stack spam in verify output
  const msg = (err && err.message) ? err.message : String(err);
  console.error(`[run-eslint] Failed: ${msg}`);
  // Non-zero so verify can mark WARN
  process.exit(1);
});
