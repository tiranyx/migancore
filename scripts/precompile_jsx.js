#!/usr/bin/env node
/**
 * Day 71d Phase 1.4: Pre-compile JSX in chat.html.
 *
 * Reads chat.html, finds <script type="text/babel"> blocks,
 * transforms JSX to JS via @babel/core, replaces them with type="application/javascript".
 * Removes the @babel/standalone CDN script (~600KB saved per page load).
 *
 * Usage:
 *   cd /opt/ado && npm install @babel/core @babel/preset-react @babel/preset-env --save-dev
 *   node scripts/precompile_jsx.js frontend/chat.html frontend/chat.html
 *
 * Output: in-place rewrite of chat.html (or copy to second arg).
 */

const fs = require('fs');
const path = require('path');
const babel = require('@babel/core');

if (process.argv.length < 4) {
  console.error('Usage: node precompile_jsx.js <input.html> <output.html>');
  process.exit(1);
}

const [, , inputPath, outputPath] = process.argv;
const html = fs.readFileSync(inputPath, 'utf-8');

// Match <script type="text/babel">...</script> blocks (greedy across newlines)
const SCRIPT_RE = /<script\s+type=["']text\/babel["']\s*>([\s\S]*?)<\/script>/g;

let totalIn = 0;
let totalOut = 0;
let count = 0;
let result = html.replace(SCRIPT_RE, (match, jsxContent) => {
  count += 1;
  totalIn += jsxContent.length;
  try {
    const compiled = babel.transformSync(jsxContent, {
      presets: [
        ['@babel/preset-env', { targets: '> 0.5%, last 2 versions, not dead, not IE 11' }],
        ['@babel/preset-react', { runtime: 'classic' }],
      ],
      compact: false, // keep readable line numbers for debugging
    });
    if (!compiled || !compiled.code) {
      console.error(`  [block ${count}] babel returned empty — keeping original`);
      return match;
    }
    totalOut += compiled.code.length;
    return `<script type="application/javascript">\n${compiled.code}\n</script>`;
  } catch (err) {
    console.error(`  [block ${count}] BABEL ERROR:`, err.message.split('\n')[0]);
    return match; // fail-safe: leave original block
  }
});

// Remove the babel CDN script tag (~600KB no longer needed)
const BABEL_CDN_RE = /\s*<script\s+src=["']https?:\/\/[^"']*babel\/standalone[^"']*["'][^>]*><\/script>/g;
let removedCdn = 0;
result = result.replace(BABEL_CDN_RE, () => {
  removedCdn += 1;
  return '';
});

fs.writeFileSync(outputPath, result, 'utf-8');

console.log('=== JSX Pre-compile complete ===');
console.log(`  blocks transformed:  ${count}`);
console.log(`  Babel CDN refs removed: ${removedCdn}`);
console.log(`  JSX size in:    ${totalIn} chars`);
console.log(`  JS  size out:   ${totalOut} chars`);
console.log(`  Delta:          ${totalOut - totalIn >= 0 ? '+' : ''}${totalOut - totalIn} chars`);
console.log(`  Output:         ${outputPath} (${fs.statSync(outputPath).size} bytes)`);
console.log();
console.log('  Browser saves ~600KB per page load (no @babel/standalone fetch).');
