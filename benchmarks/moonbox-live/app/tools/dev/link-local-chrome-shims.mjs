// tools/dev/link-local-chrome-shims.mjs
// Sudo-less, autonomous: guarantee a Chrome-like binary on PATH using Puppeteer's local browser.
// Works on Linux containers/CI without touching the OS or setting env vars.

import { spawnSync } from 'node:child_process'
import { chmodSync, existsSync, mkdirSync, writeFileSync } from 'node:fs'
import { resolve } from 'node:path'

const PW_VERSION = '23' // keep in sync with your devDependency major

function sh(cmd, args, opts = {}) {
  const r = spawnSync(cmd, args, { stdio: 'pipe', encoding: 'utf8', ...opts })
  if (r.error) throw r.error
  if (r.status !== 0) throw new Error(`[${cmd} ${args.join(' ')}] failed:\n${r.stderr || r.stdout}`)
  return (r.stdout || '').trim()
}

async function resolveExecutablePath() {
  try {
    // Puppeteer is ESM in v23+. dynamic import works in .mjs
    const mod = await import('puppeteer')
    const puppeteer = mod.default || mod
    const p = puppeteer.executablePath?.()
    return p && existsSync(p) ? p : ''
  } catch {
    return ''
  }
}

async function ensureBrowserInstalled() {
  // First try normal install path — Puppeteer’s own postinstall should have run already.
  let exe = await resolveExecutablePath()
  if (exe && existsSync(exe)) return exe

  // If not present (e.g., cache purged or SKIP flag in CI), force-install via Puppeteer CLI
  // v23 uses "browsers install chrome" (Chrome for Testing). Chromium also works, but chrome is the default now.
  try {
    sh('npx', ['--yes', `puppeteer@${PW_VERSION}`, 'browsers', 'install', 'chrome'])
  } catch {
    // As a fallback, try chromium:
    try {
      sh('npx', ['--yes', `puppeteer@${PW_VERSION}`, 'browsers', 'install', 'chromium'])
    } catch {
      throw new Error('Puppeteer could not download a local browser.')
    }
  }

  exe = await resolveExecutablePath()
  if (!exe || !existsSync(exe)) {
    throw new Error('Puppeteer returned an empty or missing executablePath().')
  }
  return exe
}

function writeShims(executablePath) {
  const binDir = resolve('node_modules/.bin')
  mkdirSync(binDir, { recursive: true })

  const names = ['google-chrome-stable', 'google-chrome', 'chromium', 'chromium-browser']
  for (const name of names) {
    const shimPath = resolve(binDir, name)
    const script = `#!/usr/bin/env bash
# Local browser shim (sudo-less). Use Puppeteer's browser; disable sandbox for CI/containers.
exec "${executablePath}" --no-sandbox "$@"
`
    writeFileSync(shimPath, script)
    chmodSync(shimPath, 0o755)
  }
  // Quick sanity: ensure at least one shim exists
  if (!existsSync(resolve(binDir, 'google-chrome-stable'))) {
    throw new Error('Failed to create browser shims in node_modules/.bin')
  }
}

;(async () => {
  // Non-Linux? We still create shims if Puppeteer has a path (harmless on mac/Win).
  const exe = await ensureBrowserInstalled()
  writeShims(exe)
  console.log(`[link-local-chrome-shims] OK -> ${exe}`)
})().catch(err => {
  console.error('[link-local-chrome-shims] ERROR:', err?.message || err)
  process.exit(2)
})
