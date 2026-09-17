import { strict as assert } from 'node:assert/strict'
import { mkdtempSync } from 'node:fs'
import { mkdir, readdir, readFile, rm, writeFile } from 'node:fs/promises'
import os from 'node:os'
import path from 'node:path'
import process from 'node:process'
import { fileURLToPath } from 'node:url'

process.env.LV_PIPELINE_TEST_MODE = '1'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const tempRoot = mkdtempSync(path.join(os.tmpdir(), 'lv-dataset-'))
process.env.LV_DATASET_ROOT = tempRoot
const datasetRoot = tempRoot
const generatedDir = path.join(datasetRoot, 'generated')
const lvDir = path.join(generatedDir, 'lv')
const archivesDir = path.join(generatedDir, 'archives')
const historyFile = path.join(archivesDir, 'history.json')
const legacyHistoryFile = path.join(generatedDir, 'lv.bundle.history.json')
const legacyBundlesDir = path.join(generatedDir, 'bundles')

async function ensureFixtureDataset(content = 'fixture') {
  await rm(lvDir, { recursive: true, force: true })
  await mkdir(lvDir, { recursive: true })
  await writeFile(path.join(lvDir, 'sample.txt'), content, 'utf8')
}

function resetLog() {
  const log = globalThis.__LV_PIPELINE_TEST_LOG__
  assert.ok(Array.isArray(log), 'pipeline test log should exist')
  log.length = 0
  return log
}

async function testPipelineCli() {
  const pipeline = await import('./pipeline.mjs')
  const { resolveCommandDescriptor } = pipeline
  const log = resetLog()

  await pipeline.crawl({ mode: 'invalid-mode', label: 'demo', skipBundle: true, keepWorkdir: true })
  const updateCall = log.find((entry) =>
    entry.type === 'node' && entry.scriptPath?.endsWith('update-dataset.mjs')
  )
  assert.ok(updateCall, 'crawl should spawn update script')
  assert.ok(updateCall.args.includes('--mode=pages'), 'crawl sanitizes invalid mode to pages')

  resetLog()
  await pipeline.build({ keep: true, eleventyArgs: ['--dry-run'] })
  const hydrateCall = log.find((entry) => entry.type === 'hydrate')
  assert.deepEqual(hydrateCall, { type: 'hydrate', force: false }, 'build respects --keep flag')
  const eleventyCall = log.find((entry) => entry.type === 'eleventy')
  assert.ok(eleventyCall, 'build should invoke eleventy')
  assert.equal(eleventyCall.offline, true, 'eleventy runs offline')
  assert.deepEqual(eleventyCall.eleventyArgs, ['--dry-run'])

  resetLog()
  await pipeline.cycle({ mode: 'pages-images', label: 'combo', eleventyArgs: ['--foo'] })
  const cycleUpdate = log.find((entry) =>
    entry.type === 'node' && entry.args?.includes('--mode=pages-images')
  )
  assert.ok(cycleUpdate, 'cycle forwards requested crawl mode')
  const cycleEleventy = log.find((entry) => entry.type === 'eleventy')
  assert.ok(cycleEleventy, 'cycle should trigger build eleventy stage')
  assert.deepEqual(cycleEleventy.eleventyArgs, ['--foo'])

  const legacyAlias = resolveCommandDescriptor('crawl-pages-images')
  assert.equal(legacyAlias.baseCommand, 'crawl', 'legacy crawl-pages-images maps to crawl command')
  assert.equal(
    legacyAlias.preset.mode,
    'pages-images',
    'legacy crawl-pages-images presets mode pages-images',
  )
  assert.equal(legacyAlias.isLegacy, true, 'legacy alias flagged appropriately')

  const modernCommand = resolveCommandDescriptor('crawl')
  assert.equal(modernCommand.isLegacy, false, 'modern command not treated as legacy')
}

async function testArchiving() {
  const bundle = await import('./bundle-lib.mjs')
  await rm(historyFile, { force: true })
  await rm(legacyHistoryFile, { force: true })
  await rm(archivesDir, { recursive: true, force: true })
  await rm(legacyBundlesDir, { recursive: true, force: true })
  await rm(path.join(generatedDir, 'lv.bundle.tgz'), { force: true })

  await ensureFixtureDataset('one')
  const first = await bundle.bundleDataset({ runLabel: 'test-a', mode: 'pages' })
  assert.ok(first?.history?.latest, 'first bundle produces history entry')
  assert.ok(first.history.latest.name.startsWith('lv-'), 'history entry is timestamped')
  assert.equal(first.history.entries.length, 1, 'history manifest records first run')

  await new Promise((resolve) => setTimeout(resolve, 1100))
  await ensureFixtureDataset('two')
  const second = await bundle.bundleDataset({ runLabel: 'test-b', mode: 'pages' })
  assert.ok(second.history.entries.length >= 2, 'second bundle appends history entry')
  assert.equal(
    second.history.latest.name,
    second.history.entries[0].name,
    'latest entry is first in history',
  )

  const history = JSON.parse(await readFile(historyFile, 'utf8'))
  assert.equal(
    history[0].name,
    second.history.latest.name,
    'history.json newest entry matches manifest latest',
  )
  assert.ok(history.length <= 10, 'history manifest respects retention limit')

  const archiveFiles = await readdir(archivesDir)
  for (const entry of history) {
    assert.ok(archiveFiles.includes(entry.name), `archive file ${entry.name} should exist`)
  }

  const legacyHistory = JSON.parse(await readFile(legacyHistoryFile, 'utf8'))
  assert.equal(legacyHistory[0].name, history[0].name, 'legacy history mirrors latest entry')
  assert.ok(
    legacyHistory.every((entry) => entry.path.startsWith('generated/bundles/')),
    'legacy history uses bundles directory paths',
  )
  const legacyArchives = await readdir(legacyBundlesDir)
  for (const entry of legacyHistory) {
    assert.ok(legacyArchives.includes(entry.name), `legacy archive ${entry.name} should exist`)
  }
}

export async function run() {
  await testPipelineCli()
  await testArchiving()
  console.log('pipeline.spec.mjs ✅')
}
