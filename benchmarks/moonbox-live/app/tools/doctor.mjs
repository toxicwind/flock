#!/usr/bin/env node
// tools/doctor.mjs — hardened environment validation for LV pipeline
import { execFileSync } from 'node:child_process'
import process from 'node:process'

import { resolveChromium } from './resolve-chromium.mjs'

function compareVersions(a = '', b = '') {
  const normalize = (value) =>
    String(value).split('.').map((part) => Number.parseInt(part, 10) || 0)
  const [aMajor, aMinor, aPatch] = normalize(a)
  const [bMajor, bMinor, bPatch] = normalize(b)
  if (aMajor !== bMajor) return aMajor - bMajor
  if (aMinor !== bMinor) return aMinor - bMinor
  return aPatch - bPatch
}

function safeExec(command, args = []) {
  try {
    return execFileSync(command, args, { stdio: ['ignore', 'pipe', 'ignore'], encoding: 'utf8' })
      .trim()
  } catch {
    return null
  }
}

const results = []

const nodeVersion = process.versions.node
const nodeRequired = '22.19.0'
const nodeOk = compareVersions(nodeVersion, nodeRequired) >= 0
results.push({ name: 'node', version: nodeVersion, ok: nodeOk, note: `>= ${nodeRequired}` })

const npmVersion = safeExec('npm', ['--version'])
results.push({ name: 'npm', version: npmVersion, ok: Boolean(npmVersion) })

let chromiumVersion = null
let chromiumPath = null
let chromiumOk = false
let chromiumError = null
try {
  chromiumPath = resolveChromium()
  chromiumVersion = safeExec(chromiumPath, ['--version'])
  chromiumOk = Boolean(chromiumVersion)
} catch (error) {
  chromiumError = error instanceof Error ? error.message : String(error)
}
results.push({
  name: 'chromium',
  version: chromiumVersion || 'missing',
  ok: chromiumOk,
  note: chromiumPath || chromiumError || '',
})

const ciState = process.env.CI == null ? 'unset' : String(process.env.CI)

let allOk = true
for (const { name, version, ok, note } of results) {
  allOk &&= ok
  const mark = ok ? '✓' : '✗'
  const detail = note ? ` — ${note}` : ''
  console.log(`${mark} ${name} ${version || '(missing)'}${detail}`)
}
console.log(`CI environment: ${ciState}`)

if (!chromiumOk) {
  console.error('\nChromium runtime missing; run ./bin/install-chromium.sh or npm run setup.')
  process.exit(1)
}

if (!allOk) {
  console.error('\nEnvironment checks failed.')
  process.exit(1)
}

console.log('\nEnvironment looks good.')
