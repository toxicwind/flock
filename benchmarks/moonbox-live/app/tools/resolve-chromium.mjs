import { execFileSync } from 'node:child_process'
import { accessSync, constants, readdirSync } from 'node:fs'
import path from 'node:path'
import process from 'node:process'
import { fileURLToPath } from 'node:url'

const ENV_CANDIDATES = [
  process.env.PUPPETEER_EXECUTABLE_PATH,
  process.env.PLAYWRIGHT_CHROMIUM_PATH,
  process.env.CHROMIUM_BIN,
  process.env.CHROMIUM_PATH,
]

const SYSTEM_CANDIDATES = [
  '/usr/local/bin/chromium',
  '/usr/local/bin/chromium-browser',
  '/usr/bin/chromium',
  '/usr/bin/chromium-browser',
  '/usr/bin/google-chrome-stable',
  '/snap/bin/chromium',
]

function fromPlaywrightCaches() {
  const bases = new Set()
  if (process.env.PLAYWRIGHT_BROWSERS_PATH) {
    bases.add(process.env.PLAYWRIGHT_BROWSERS_PATH)
  }
  if (process.env.HOME) {
    bases.add(path.join(process.env.HOME, '.cache', 'ms-playwright'))
  }
  bases.add(path.join(process.cwd(), 'node_modules', '.cache', 'ms-playwright'))

  const results = []
  for (const base of bases) {
    if (!base) continue
    let entries
    try {
      entries = readdirSync(base, { withFileTypes: true })
    } catch {
      continue
    }
    for (const entry of entries) {
      if (!entry.isDirectory() || !entry.name.startsWith('chromium-')) continue
      const candidate = path.join(base, entry.name, 'chrome-linux', 'chrome')
      results.push(candidate)
    }
  }
  return results
}

function dedupeCandidates(candidates) {
  const seen = new Set()
  const ordered = []
  for (const candidate of candidates) {
    if (!candidate) continue
    const key = path.resolve(candidate)
    if (seen.has(key)) continue
    seen.add(key)
    ordered.push(candidate)
  }
  return ordered
}

function isFunctionalChromium(candidate) {
  try {
    execFileSync(candidate, ['--version'], { stdio: 'ignore' })
    return true
  } catch {
    return false
  }
}

export function resolveChromium() {
  const candidates = dedupeCandidates([
    ...ENV_CANDIDATES,
    ...fromPlaywrightCaches(),
    ...SYSTEM_CANDIDATES,
  ])
  for (const candidate of candidates) {
    try {
      accessSync(candidate, constants.X_OK)
      if (isFunctionalChromium(candidate)) {
        return candidate
      }
    } catch {
      // continue searching
    }
  }
  throw new Error(
    'Chromium not found after automated provisioning attempts (bin/install-chromium.sh).',
  )
}

const modulePath = fileURLToPath(import.meta.url)

if (process.argv[1] && path.resolve(process.argv[1]) === modulePath) {
  try {
    const resolved = resolveChromium()
    process.stdout.write(`${resolved}\n`)
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error)
    console.error(message)
    process.exit(1)
  }
}
