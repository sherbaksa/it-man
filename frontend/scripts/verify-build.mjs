/**
 * Author: Dev2
 * Date: 2026-07-16
 * Purpose: Smoke-check the production artifact without external test libraries.
 */
import { access, readFile, readdir } from 'node:fs/promises'
import { constants } from 'node:fs'
import { join } from 'node:path'

const distDir = new URL('../dist/', import.meta.url)
const indexPath = new URL('index.html', distDir)

await access(indexPath, constants.R_OK)
const html = await readFile(indexPath, 'utf8')
if (!html.includes('<div id="root"></div>')) {
  throw new Error('Smoke test failed: React root is missing from dist/index.html')
}

const assets = await readdir(new URL('assets/', distDir))
if (!assets.some((name) => name.endsWith('.js')) || !assets.some((name) => name.endsWith('.css'))) {
  throw new Error('Smoke test failed: compiled JS/CSS assets are missing')
}

console.log(`Smoke test passed: ${join('dist', 'index.html')} and ${assets.length} assets are ready.`)
