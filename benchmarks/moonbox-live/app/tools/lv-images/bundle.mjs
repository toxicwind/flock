#!/usr/bin/env node
import process from 'node:process'

import {
  bundleDataset,
  datasetStats,
  hydrateDataset,
  normalizeUrlmetaPaths,
  paths,
  verifyBundle,
} from './bundle-lib.mjs'

function formatBytes(bytes) {
  if (bytes == null) return '-'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`
}

function usage() {
  console.log(
    `LV images bundle helper\n\nCommands:\n  pack|bundle       Create lv.bundle.tgz and lv.bundle.json\n  hydrate           Restore generated/lv from the bundle\n  verify            Check bundle size/hash against manifest\n  stats             Print dataset stats\n  normalize         Normalize cache paths inside urlmeta.json\n\nFlags:\n  hydrate --keep    Keep existing generated/lv files (no clean)\n`,
  )
}

async function run() {
  const [, , commandRaw, ...rest] = process.argv
  const command = (commandRaw || 'help').toLowerCase()
  const flags = new Set(rest)

  switch (command) {
    case 'pack':
    case 'bundle': {
      const manifest = await bundleDataset()
      if (!manifest) {
        console.warn('[lv-images] Nothing to bundle (dataset missing).')
        return
      }
      const { fileCount, totalBytes } = manifest.dataset
      console.log(
        `[lv-images] Bundled ${fileCount} files (${
          formatBytes(totalBytes)
        }) → ${manifest.archive.path} (${formatBytes(manifest.archive.size)})`,
      )
      console.log(`[lv-images] sha256 ${manifest.archive.sha256}`)
      break
    }
    case 'hydrate': {
      const keepExisting = flags.has('--keep')
      const result = await hydrateDataset({ force: !keepExisting, quiet: false })
      if (result.hydrated) {
        console.log(`[lv-images] Hydrated dataset into ${paths.lvDir}`)
      } else {
        console.warn(`[lv-images] Hydrate skipped: ${result.reason}`)
        process.exitCode = 1
      }
      break
    }
    case 'verify': {
      const result = await verifyBundle()
      if (!result.ok) {
        const reason = result.reason || result.mismatches?.join(', ') || 'unknown'
        console.error(`[lv-images] Bundle verification failed: ${reason}`)
        if (result.actual) {
          const { archive, dataset } = result.actual
          console.error(
            `  archive: size=${archive.size} sha256=${archive.sha256}\n  dataset: files=${dataset.fileCount} bytes=${dataset.totalBytes}`,
          )
        }
        process.exitCode = 1
      } else {
        console.log('[lv-images] Bundle verification passed.')
      }
      break
    }
    case 'stats': {
      const stats = await datasetStats()
      console.log(`[lv-images] Dataset root: ${paths.lvDir}`)
      console.log(`[lv-images] Files: ${stats.entries.length}`)
      console.log(`[lv-images] Size: ${formatBytes(stats.totalBytes)}`)
      break
    }
    case 'normalize': {
      const { changed, count } = await normalizeUrlmetaPaths()
      const state = changed ? 'updated' : 'clean'
      console.log(`[lv-images] Normalized ${count} urlmeta entries (${state}).`)
      break
    }
    case 'help':
    case '--help':
    case '-h':
    default:
      usage()
      if (!commandRaw || command === 'help') {
        return
      }
      process.exitCode = 1
  }
}

run().catch((error) => {
  console.error('[lv-images] Fatal:', error)
  process.exitCode = 1
})
