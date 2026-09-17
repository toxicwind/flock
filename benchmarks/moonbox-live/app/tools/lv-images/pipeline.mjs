#!/usr/bin/env node
import { execFileSync, spawn } from 'node:child_process'
import fs from 'node:fs/promises'
import path from 'node:path'
import process from 'node:process'
import { fileURLToPath, pathToFileURL } from 'node:url'

import { resolveChromium } from '../resolve-chromium.mjs'
import { hydrateDataset, verifyBundle } from './bundle-lib.mjs'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const projectRoot = path.resolve(__dirname, '..', '..')
const updateScript = path.join(projectRoot, 'src/content/projects/lv-images/update-dataset.mjs')
const doctorScript = path.join(projectRoot, 'tools/doctor.mjs')
const offlineShim = path.join(projectRoot, 'tools/offline-network-shim.cjs')
const eleventyCmd = path.join(projectRoot, 'node_modules', '@11ty', 'eleventy', 'cmd.cjs')
const isTestMode = process.env.LV_PIPELINE_TEST_MODE === '1'
const testLog = []
if (isTestMode) {
  globalThis.__LV_PIPELINE_TEST_LOG__ = testLog
}

const BAKED_OUTPUT_DIR = path.resolve(projectRoot, 'public', 'lvreport')
const BAKED_REPORT_PATH = path.join(BAKED_OUTPUT_DIR, 'report.json')

async function pathExists(p) {
  try {
    await fs.access(p)
    return true
  } catch {
    return false
  }
}

const LEGACY_COMMANDS = new Map([
  ['crawl-pages', { command: 'crawl', preset: { mode: 'pages' } }],
  ['crawl-pages-images', { command: 'crawl', preset: { mode: 'pages-images' } }],
  ['cycle-pages', { command: 'cycle', preset: { mode: 'pages' } }],
  ['cycle-pages-images', { command: 'cycle', preset: { mode: 'pages-images' } }],
  ['hydrate-build', { command: 'build', preset: {} }],
  ['cycle', { command: 'cycle', preset: {} }],
])

export function resolveCommandDescriptor(rawCommand) {
  const normalized = String(rawCommand || '').toLowerCase()
  const legacy = LEGACY_COMMANDS.get(normalized)
  return {
    normalized,
    baseCommand: legacy ? legacy.command : normalized,
    preset: legacy?.preset ?? {},
    isLegacy: Boolean(legacy),
  }
}

function logStep(message) {
  console.log(`\x1b[95m[lv-images]\x1b[0m ${message}`)
}

let chromiumPathCache = ''

function ensureChromiumReady() {
  if (isTestMode) {
    chromiumPathCache = chromiumPathCache || '/tmp/chromium-test'
    return chromiumPathCache
  }
  if (chromiumPathCache) return chromiumPathCache
  const resolved = resolveChromium()
  let version = ''
  try {
    version = execFileSync(resolved, ['--version'], { encoding: 'utf8' }).trim()
  } catch (error) {
    console.warn(`[lv-images] Unable to read Chromium version from ${resolved}:`, error)
  }
  const versionLabel = version ? ` (${version})` : ''
  logStep(`Chromium @ ${resolved}${versionLabel}`)
  chromiumPathCache = resolved
  return chromiumPathCache
}

function spawnProcess(command, args = [], options = {}) {
  if (isTestMode) {
    testLog.push({ type: 'spawn', command, args, options })
    return Promise.resolve()
  }
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, {
      cwd: projectRoot,
      stdio: 'inherit',
      ...options,
    })
    child.on('exit', (code) => {
      if (code === 0) {
        resolve()
      } else {
        reject(new Error(`${command} exited with code ${code}`))
      }
    })
  })
}

function spawnNodeScript(scriptPath, args = [], env = {}) {
  if (isTestMode) {
    testLog.push({ type: 'node', scriptPath, args, env })
    return Promise.resolve()
  }
  return spawnProcess(process.execPath, [scriptPath, ...args], {
    env: { ...process.env, ...env },
  })
}

function splitCliArgs(argv) {
  const pivot = argv.indexOf('--')
  if (pivot === -1) return { flags: argv, passthrough: [] }
  return { flags: argv.slice(0, pivot), passthrough: argv.slice(pivot + 1) }
}

function parseFlagMap(args = []) {
  return new Map(
    args.map((token) => {
      if (!token.startsWith('--')) return [token, true]
      const eq = token.indexOf('=')
      if (eq === -1) return [token, true]
      const key = token.slice(0, eq)
      const value = token.slice(eq + 1)
      return [key, value]
    }),
  )
}

async function runUpdate(
  { mode = 'pages', label = '', skipBundle = false, keepWorkdir = false } = {},
) {
  ensureChromiumReady()
  const args = []
  if (mode) args.push(`--mode=${mode}`)
  if (label) args.push(`--bundle-label=${label}`)
  if (skipBundle) args.push('--skip-bundle')
  if (keepWorkdir) args.push('--keep-workdir')
  const labelMsg = label ? ` label=${label}` : ''
  logStep(
    `Refreshing dataset via Playwright (mode=${mode}${labelMsg}${skipBundle ? ' skip-bundle' : ''}${keepWorkdir ? ' keep-workdir' : ''
    })`,
  )
  await spawnNodeScript(updateScript, args)
}

async function runHydrate({ force = true } = {}) {
  if (isTestMode) {
    testLog.push({ type: 'hydrate', force })
    return { hydrated: true }
  }
  logStep(`Hydrating dataset from bundle${force ? ' (force clean)' : ''}`)
  const result = await hydrateDataset({ force, quiet: false })
  if (!result.hydrated) {
    if (await pathExists(BAKED_REPORT_PATH) || await pathExists(`${BAKED_REPORT_PATH}.gz`)) {
      logStep(
        `Warning: Hydrate failed (${result.reason}), but baked report exists. Continuing using baked artifact.`,
      )
      return { hydrated: true, reason: 'fallback-to-baked' }
    }
    throw new Error(`Hydrate failed (${result.reason || 'unknown'})`)
  }
  return result
}

async function runVerify({ strict = true } = {}) {
  if (isTestMode) {
    testLog.push({ type: 'verify', strict })
    return { ok: true }
  }
  logStep('Verifying bundle against manifest')
  const result = await verifyBundle()
  if (!result.ok) {
    const reason = result.reason || result.mismatches?.join(', ') || 'unknown'
    const toleratedReasons = new Set([
      'manifest-lfs-pointer',
      'invalid-manifest-json',
      'missing-manifest',
      'missing-bundle',
    ])
    if (strict && !toleratedReasons.has(reason)) {
      if ((await pathExists(BAKED_REPORT_PATH)) || (await pathExists(`${BAKED_REPORT_PATH}.gz`))) {
        logStep(
          `Warning: Bundle verification failed (${reason}), but baked report exists. Continuing using baked artifact.`,
        )
        return { ok: true, reason: 'fallback-to-baked' }
      }
      throw new Error(`Bundle verification failed: ${reason}`)
    }
    console.warn(`[lv-images] Bundle verification failed: ${reason}`)
  } else {
    logStep('Bundle verification passed')
  }
  return result
}

async function runEleventy({ offline = false, eleventyArgs = [] } = {}) {
  if (isTestMode) {
    testLog.push({ type: 'eleventy', offline, eleventyArgs })
    return
  }
  const nodeArgs = []
  if (offline) {
    nodeArgs.push('--require', offlineShim)
  }
  nodeArgs.push(eleventyCmd, ...eleventyArgs)
  const env = { ...process.env }
  if (offline) env.BUILD_OFFLINE = '1'
  else delete env.BUILD_OFFLINE
  const heapFlag = '--max-old-space-size=8192'
  env.NODE_OPTIONS = env.NODE_OPTIONS ? `${env.NODE_OPTIONS} ${heapFlag}`.trim() : heapFlag
  await spawnProcess(process.execPath, nodeArgs, { env })
}

async function runReportBuild({ reason = 'manual' } = {}) {
  if (isTestMode) {
    testLog.push({ type: 'report-build', reason })
    return
  }
  try {
    const modulePath = path.join(projectRoot, 'src', '_data', 'lvreport.js')
    const moduleUrl = pathToFileURL(modulePath).href
    const { buildAndPersistReport, DATASET_REPORT_FILE } = await import(moduleUrl)
    if (typeof buildAndPersistReport !== 'function') {
      throw new Error('lvreport module missing buildAndPersistReport export')
    }
    logStep(`Rebuilding lvreport dataset cache (${reason})`)
    const { payload } = await buildAndPersistReport({ log: logStep })
    const totals = payload?.totals || {}
    const relPath = DATASET_REPORT_FILE
      ? path.relative(projectRoot, DATASET_REPORT_FILE)
      : 'src/content/projects/lv-images/generated/lv/lvreport.dataset.json'
    logStep(
      `lvreport cached → ${relPath} (images=${totals.images ?? '?'}, pages=${totals.pages ?? '?'})`,
    )
  } catch (error) {
    if ((await pathExists(BAKED_REPORT_PATH)) || (await pathExists(`${BAKED_REPORT_PATH}.gz`))) {
      logStep(
        `Warning: Report rebuild failed (${error.message}), but baked report exists. Continuing using baked artifact.`,
      )
      return
    }
    console.error(`[lv-images] lvreport build failed (${reason}):`, error?.message || error)
    throw error
  }
}

function sanitizeMode(requested) {
  const normalized = String(requested || '').toLowerCase()
  if (['pages', 'pages-images', 'metadata', 'metadata-only'].includes(normalized)) {
    if (normalized === 'metadata') return 'metadata-only'
    return normalized
  }
  return 'pages'
}

export async function crawl(
  { mode = 'pages', label = '', skipBundle = false, keepWorkdir = false } = {},
) {
  const safeMode = sanitizeMode(mode)
  await runUpdate({ mode: safeMode, label, skipBundle, keepWorkdir })
}

export async function build({ keep = false, eleventyArgs = [] } = {}) {
  await runHydrate({ force: !keep })
  await runVerify({ strict: true })
  await runReportBuild({ reason: keep ? 'build-keep' : 'build' })
  await runEleventy({ offline: true, eleventyArgs })
}

export async function cycle(
  { mode = 'pages', label = '', eleventyArgs = [], keepWorkdir = false } = {},
) {
  const safeMode = sanitizeMode(mode)
  await crawl({ mode: safeMode, label, skipBundle: false, keepWorkdir })
  await build({ keep: false, eleventyArgs })
}

export async function doctor() {
  await spawnNodeScript(doctorScript)
}

function usage() {
  console.log(
    [
      'LV images pipeline',
      '',
      'Usage: node tools/lv-images/pipeline.mjs <command> [options]',
      '',
      'Commands:',
      '  crawl [--mode=pages|pages-images|metadata] [--label=name] [--skip-bundle] [--keep-workdir]',
      '        Crawl live site and refresh dataset (Playwright).',
      '  build [--keep] [-- ... eleventy]',
      '        Hydrate from bundle, verify, rebuild dataset cache, offline Eleventy.',
      '  cycle [--mode=pages|pages-images|metadata] [--label=name] [--keep-workdir] [-- ... eleventy]',
      '        Crawl then hydrate/verify/offline build in one run.',
      '  doctor',
      '        Run environment diagnostics.',
      '',
      'Legacy aliases: crawl-pages, crawl-pages-images, cycle-pages, cycle-pages-images, hydrate-build',
    ].join('\n'),
  )
}

async function main() {
  const [, , rawCommand = 'help', ...argv] = process.argv
  const descriptor = resolveCommandDescriptor(rawCommand)
  const { normalized, baseCommand, preset, isLegacy } = descriptor
  if (isLegacy && !isTestMode) {
    console.warn(
      `[lv-images] Legacy command "${normalized}" invoked; forwarding to ${baseCommand}.`,
    )
  }

  const ciPivot = process.env.CI === 'true' && baseCommand === 'crawl'
  const effectiveCommand = ciPivot ? 'build' : baseCommand
  const appliedPreset = ciPivot ? {} : preset
  if (ciPivot) {
    console.warn('[lv-images] WARN: Live crawl requested in CI; pivoting to offline build.')
  }

  try {
    switch (effectiveCommand) {
      case 'crawl': {
        const { flags } = splitCliArgs(argv)
        const map = parseFlagMap(flags)
        await crawl({
          mode: map.get('--mode') || appliedPreset.mode || 'pages',
          label: map.get('--label') || '',
          skipBundle: map.has('--skip-bundle'),
          keepWorkdir: map.has('--keep-workdir') || appliedPreset.keepWorkdir || false,
        })
        break
      }
      case 'build': {
        const { flags, passthrough } = splitCliArgs(argv)
        const map = parseFlagMap(flags)
        const keep = map.has('--keep') || appliedPreset.keep || false
        await build({ keep, eleventyArgs: passthrough })
        break
      }
      case 'cycle': {
        const { flags, passthrough } = splitCliArgs(argv)
        const map = parseFlagMap(flags)
        await cycle({
          mode: map.get('--mode') || appliedPreset.mode || 'pages',
          label: map.get('--label') || '',
          eleventyArgs: passthrough,
          keepWorkdir: map.has('--keep-workdir') || appliedPreset.keepWorkdir || false,
        })
        break
      }
      case 'doctor': {
        await doctor()
        break
      }
      case 'help':
      case '--help':
      case '-h':
      default:
        usage()
        if (!['help', '--help', '-h'].includes(effectiveCommand)) process.exitCode = 1
    }
  } catch (error) {
    console.error('[lv-images] Fatal:', error?.message || error)
    if (error?.stack) console.error(error.stack)
    process.exitCode = 1
  }
}

if (import.meta.url === pathToFileURL(__filename).href) {
  main()
}
