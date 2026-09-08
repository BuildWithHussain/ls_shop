#!/usr/bin/env node
// The browser serves the last `yarn build`, never dashboard/src. Every e2e lane runs
// this first so a green suite can never be a green run against a stale bundle.
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const DASHBOARD = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..')
const SOURCE = path.join(DASHBOARD, 'src')
// vite writes the entry document to ls_shop/www (Frappe serves it as a www page) and
// the hashed assets to ls_shop/public/commera — see buildConfig in vite.config.js.
const BUILT_ENTRY = path.resolve(DASHBOARD, '..', 'ls_shop', 'www', 'commera.html')
const BUILT_ASSETS = path.resolve(DASHBOARD, '..', 'ls_shop', 'public', 'commera', 'assets')

function newestMtime(directory) {
  let newest = 0
  for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
    const full = path.join(directory, entry.name)
    const stamp = entry.isDirectory() ? newestMtime(full) : fs.statSync(full).mtimeMs
    if (stamp > newest) newest = stamp
  }
  return newest
}

function fail(message) {
  console.error('\nStale dashboard build: ' + message)
  console.error('Run `yarn build` in dashboard/ and re-run the suite.\n')
  process.exit(1)
}

if (!fs.existsSync(BUILT_ENTRY)) fail(BUILT_ENTRY + ' does not exist.')
if (!fs.existsSync(BUILT_ASSETS)) fail(BUILT_ASSETS + ' does not exist.')

const builtAt = Math.min(fs.statSync(BUILT_ENTRY).mtimeMs, newestMtime(BUILT_ASSETS))
const sourceAt = newestMtime(SOURCE)

if (sourceAt > builtAt) {
  const stale = new Date(builtAt).toISOString()
  const edited = new Date(sourceAt).toISOString()
  fail(`dashboard/src changed at ${edited} but the bundle was built at ${stale}.`)
}

console.log('build is fresh (bundle built ' + new Date(builtAt).toISOString() + ')')
