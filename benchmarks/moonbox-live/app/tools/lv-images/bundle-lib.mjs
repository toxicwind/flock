import { createHash } from 'node:crypto'
import { createReadStream } from 'node:fs'
import { access, copyFile, mkdir, readdir, readFile, rm, stat, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

import * as tar from 'tar'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const projectRoot = path.resolve(__dirname, '..', '..')
const datasetRootOverride = process.env.LV_DATASET_ROOT
const datasetRoot = datasetRootOverride
  ? path.resolve(datasetRootOverride)
  : path.join(projectRoot, 'src/content/projects/lv-images')
const generatedDir = path.join(datasetRoot, 'generated')
const lvDir = path.join(generatedDir, 'lv')
const stableBundlePath = path.join(generatedDir, 'lv.bundle.tgz')
const manifestPath = path.join(generatedDir, 'lv.bundle.json')
const archivesDir = path.join(generatedDir, 'archives')
const historyManifestPath = path.join(archivesDir, 'history.json')
const legacyBundleHistoryDir = path.join(generatedDir, 'bundles')
const legacyHistoryManifestPath = path.join(generatedDir, 'lv.bundle.history.json')
const urlmetaPath = path.join(lvDir, 'cache', 'urlmeta.json')
const summaryPath = path.join(lvDir, 'summary.json')

const HISTORY_LIMIT = 10

const posixify = (value) => value.split(path.sep).join('/')
const rel = (from, to) => posixify(path.relative(from, to))
const timestampSlug = (date = new Date()) =>
  date.toISOString().replace(/[:-]/g, '').replace(/\.\d{3}Z$/, 'Z')

async function hashFile(filePath, algorithm = 'sha256') {
  return new Promise((resolve, reject) => {
    const hash = createHash(algorithm)
    const stream = createReadStream(filePath)
    stream.on('error', reject)
    stream.on('data', (chunk) => hash.update(chunk))
    stream.on('end', () => resolve(hash.digest('hex')))
  })
}

function toRelativeCachePath(p) {
  if (!p) return ''
  const normalized = String(p).trim()
  if (!normalized) return ''
  const unixified = normalized.replace(/\\/g, '/')
  const marker = '/generated/lv/'
  const idx = unixified.indexOf(marker)
  if (idx !== -1) {
    const tail = unixified.slice(idx + marker.length).replace(/^\/+/, '')
    if (tail) return tail
  }
  const abs = path.isAbsolute(normalized) ? normalized : path.resolve(lvDir, normalized)
  const relative = path.relative(lvDir, abs)
  if (!relative || relative.startsWith('..')) {
    return posixify(normalized)
  }
  return posixify(relative)
}

async function walkDatasetDir(dirRel, acc) {
  const target = path.join(lvDir, dirRel)
  let dirents
  try {
    dirents = await readdir(target, { withFileTypes: true })
  } catch (error) {
    if (error.code === 'ENOENT') return
    throw error
  }
  for (const entry of dirents) {
    const childRel = dirRel ? `${dirRel}/${entry.name}` : entry.name
    const abs = path.join(target, entry.name)
    if (entry.isDirectory()) {
      await walkDatasetDir(childRel, acc)
    } else if (entry.isFile()) {
      const s = await stat(abs)
      acc.push({ path: posixify(childRel), size: s.size })
    }
  }
}

export async function collectDatasetEntries() {
  const acc = []
  await walkDatasetDir('', acc)
  return acc.sort((a, b) => a.path.localeCompare(b.path))
}

export async function normalizeUrlmetaPaths() {
  let data
  try {
    const raw = await readFile(urlmetaPath, 'utf8')
    data = raw ? JSON.parse(raw) : {}
  } catch (error) {
    if (error.code === 'ENOENT') {
      return { changed: false, count: 0 }
    }
    throw error
  }

  let changed = false
  let count = 0
  for (const meta of Object.values(data)) {
    if (!meta || !meta.path) continue
    count++
    const relPath = toRelativeCachePath(meta.path)
    if (relPath && meta.path !== relPath) {
      meta.path = relPath
      changed = true
    }
  }

  if (changed) {
    await writeFile(urlmetaPath, JSON.stringify(data, null, 2))
  }

  return { changed, count }
}

async function readHistoryManifest() {
  try {
    const raw = await readFile(historyManifestPath, 'utf8')
    return raw ? JSON.parse(raw) : []
  } catch (error) {
    if (error.code === 'ENOENT') return []
    throw error
  }
}

function sanitizeSlug(value) {
  return value
    ? String(value)
      .toLowerCase()
      .replace(/[^\da-z]+/g, '-')
      .replace(/^-+|-+$/g, '')
    : ''
}

async function writeHistoryManifest(entries) {
  await mkdir(archivesDir, { recursive: true })
  await writeFile(historyManifestPath, JSON.stringify(entries, null, 2))
}

async function pruneArchives(keepNames) {
  let files = []
  try {
    files = await readdir(archivesDir)
  } catch (error) {
    if (error.code === 'ENOENT') return
    throw error
  }
  const keep = new Set(keepNames)
  await Promise.all(
    files
      .filter((name) => name.endsWith('.tgz') && !keep.has(name))
      .map((name) => rm(path.join(archivesDir, name), { force: true })),
  )
}

async function writeLegacyHistory(entries) {
  await mkdir(legacyBundleHistoryDir, { recursive: true })
  const legacyEntries = entries.map((entry) => ({
    name: entry.name,
    path: `generated/bundles/${entry.name}`,
    generatedAt: entry.generatedAt,
    size: entry.size,
    sha256: entry.sha256,
    mode: entry.mode || null,
    label: entry.label || null,
  }))
  await writeFile(legacyHistoryManifestPath, JSON.stringify(legacyEntries, null, 2))
}

async function pruneLegacyArchives(keepNames) {
  let files = []
  try {
    files = await readdir(legacyBundleHistoryDir)
  } catch (error) {
    if (error.code === 'ENOENT') return
    throw error
  }
  const keep = new Set(keepNames)
  await Promise.all(
    files
      .filter((name) => name.endsWith('.tgz') && !keep.has(name))
      .map((name) => rm(path.join(legacyBundleHistoryDir, name), { force: true })),
  )
}

export async function bundleDataset({
  skipIfMissing = false,
  quiet = false,
  runLabel = '',
  mode = '',
} = {}) {
  const entries = await collectDatasetEntries()
  if (entries.length === 0) {
    if (skipIfMissing) {
      if (!quiet) {
        console.warn(`[lv-images] No dataset found at ${lvDir}`)
      }
      return null
    }
    throw new Error(`LV dataset missing at ${lvDir}`)
  }

  await normalizeUrlmetaPaths()
  await mkdir(generatedDir, { recursive: true })
  await mkdir(archivesDir, { recursive: true })
  await mkdir(legacyBundleHistoryDir, { recursive: true })

  const generationTime = new Date()
  const generatedAtIso = generationTime.toISOString()
  const timestamp = timestampSlug(generationTime)
  const modeSlug = sanitizeSlug(mode)
  const labelSlug = sanitizeSlug(runLabel)
  const suffixParts = [modeSlug, labelSlug].filter(Boolean)
  const suffix = suffixParts.length ? `-${suffixParts.join('-')}` : ''
  const archiveName = `lv-${timestamp}${suffix}.tgz`
  const archivePath = path.join(archivesDir, archiveName)

  await tar.create({
    gzip: true,
    cwd: generatedDir,
    file: archivePath,
    portable: true,
    noMtime: true,
  }, ['lv'])

  const archiveStat = await stat(archivePath)
  const sha256 = await hashFile(archivePath)

  let summary = null
  try {
    const raw = await readFile(summaryPath, 'utf8')
    summary = raw ? JSON.parse(raw) : null
  } catch (error) {
    if (error.code !== 'ENOENT') throw error
  }

  const totalBytes = entries.reduce((sum, file) => sum + file.size, 0)

  const legacyArchivePath = path.join(legacyBundleHistoryDir, archiveName)

  const historyEntry = {
    name: archiveName,
    path: rel(datasetRoot, archivePath),
    legacyPath: rel(datasetRoot, legacyArchivePath),
    size: archiveStat.size,
    sha256,
    generatedAt: generatedAtIso,
    mode: mode || null,
    label: runLabel || null,
  }

  let historyManifest = await readHistoryManifest()
  historyManifest.unshift(historyEntry)
  if (historyManifest.length > HISTORY_LIMIT) {
    historyManifest = historyManifest.slice(0, HISTORY_LIMIT)
  }
  await writeHistoryManifest(historyManifest)
  await writeLegacyHistory(historyManifest)
  await pruneArchives(historyManifest.map((entry) => entry.name))
  await pruneLegacyArchives(historyManifest.map((entry) => entry.name))

  await copyFile(archivePath, stableBundlePath)
  await copyFile(archivePath, legacyArchivePath)

  const historySummary = historyManifest.map((entry) => ({
    ...entry,
    path: rel(datasetRoot, path.join(datasetRoot, entry.path)),
    legacyPath: rel(datasetRoot, path.join(datasetRoot, entry.legacyPath || entry.path)),
  }))

  const manifest = {
    generatedAt: generatedAtIso,
    runLabel: runLabel || null,
    mode: mode || null,
    dataset: {
      fileCount: entries.length,
      totalBytes,
    },
    archive: {
      path: rel(datasetRoot, stableBundlePath),
      size: archiveStat.size,
      sha256,
    },
    summary: summary
      ? {
        version: summary.version || null,
        generatedAt: summary.generatedAt || null,
        totals: summary.totals || null,
      }
      : null,
    history: {
      latest: historySummary[0] || null,
      entries: historySummary,
      manifestPath: rel(datasetRoot, historyManifestPath),
      directory: rel(datasetRoot, archivesDir),
    },
  }

  await writeFile(manifestPath, JSON.stringify(manifest, null, 2))
  return manifest
}

export async function hydrateDataset({ force = true, quiet = false } = {}) {
  try {
    await access(stableBundlePath)
  } catch (error) {
    if (error.code === 'ENOENT') {
      if (!quiet) {
        console.warn(`[lv-images] Bundle missing at ${stableBundlePath}`)
      }
      return { hydrated: false, reason: 'missing-bundle' }
    }
    throw error
  }

  if (force) {
    await rm(lvDir, { recursive: true, force: true })
  }

  await mkdir(generatedDir, { recursive: true })
  await tar.extract({ cwd: generatedDir, file: stableBundlePath, strip: 0 })
  await normalizeUrlmetaPaths()

  return { hydrated: true, reason: 'ok' }
}

export async function verifyBundle() {
  let manifest
  try {
    const raw = await readFile(manifestPath, 'utf8')
    if (!raw) {
      manifest = null
    } else {
      try {
        manifest = JSON.parse(raw)
      } catch {
        if (raw.startsWith('version https://git-lfs.github.com/spec/v1')) {
          return { ok: false, reason: 'manifest-lfs-pointer', raw }
        }
        return { ok: false, reason: 'invalid-manifest-json', raw }
      }
    }
  } catch (error) {
    if (error.code === 'ENOENT') {
      return { ok: false, reason: 'missing-manifest' }
    }
    throw error
  }

  if (!manifest) {
    return { ok: false, reason: 'invalid-manifest' }
  }

  let bundleStat
  try {
    bundleStat = await stat(stableBundlePath)
  } catch (error) {
    if (error.code === 'ENOENT') {
      return { ok: false, reason: 'missing-bundle', manifest }
    }
    throw error
  }

  const sha256 = await hashFile(stableBundlePath)
  const entries = await collectDatasetEntries()
  const totalBytes = entries.reduce((sum, file) => sum + file.size, 0)

  const mismatches = []
  if (manifest.archive?.size != null && manifest.archive.size !== bundleStat.size) {
    mismatches.push('size')
  }
  if (manifest.archive?.sha256 && manifest.archive.sha256 !== sha256) {
    mismatches.push('sha256')
  }
  if (manifest.dataset?.fileCount != null && manifest.dataset.fileCount !== entries.length) {
    mismatches.push('fileCount')
  }
  if (manifest.dataset?.totalBytes != null && manifest.dataset.totalBytes !== totalBytes) {
    mismatches.push('totalBytes')
  }

  return {
    ok: mismatches.length === 0,
    manifest,
    actual: {
      archive: { size: bundleStat.size, sha256 },
      dataset: { fileCount: entries.length, totalBytes },
    },
    mismatches,
  }
}

export async function datasetStats() {
  const entries = await collectDatasetEntries()
  const totalBytes = entries.reduce((sum, file) => sum + file.size, 0)
  return {
    entries,
    totalBytes,
  }
}

export const paths = {
  projectRoot,
  datasetRoot,
  generatedDir,
  lvDir,
  bundlePath: stableBundlePath,
  manifestPath,
  archivesDir,
  historyManifestPath,
  legacyBundleHistoryDir,
  legacyHistoryManifestPath,
  urlmetaPath,
  summaryPath,
}

export default {
  bundleDataset,
  hydrateDataset,
  verifyBundle,
  datasetStats,
  normalizeUrlmetaPaths,
  collectDatasetEntries,
  paths,
}
