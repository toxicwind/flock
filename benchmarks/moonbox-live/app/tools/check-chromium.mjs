#!/usr/bin/env node
import { execFileSync } from 'node:child_process'
import process from 'node:process'

import { resolveChromium } from './resolve-chromium.mjs'

let chromiumPath
try {
  chromiumPath = resolveChromium()
} catch (error) {
  const message = error instanceof Error ? error.message : String(error)
  console.error(`❌ ${message}`)
  console.error(
    '💡 Run ./bin/install-chromium.sh or `npx playwright install chromium` to provision a browser.',
  )
  process.exit(1)
}

let version = ''
try {
  version = execFileSync(chromiumPath, ['--version'], { encoding: 'utf8' }).trim()
} catch (error) {
  if (process.env.CI) {
    console.warn(`⚠️ Unable to read Chromium version from ${chromiumPath}:`, error)
  }
}

const versionText = version ? ` (${version})` : ''
console.log(`Chromium available at ${chromiumPath}${versionText}`)
