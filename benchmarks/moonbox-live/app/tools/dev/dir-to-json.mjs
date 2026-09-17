#!/usr/bin/env node
// tools/dev/dir-to-json.mjs
// Usage:
//   node tools/dev/dir-to-json.mjs [folder_from_repo_root] [out_file]
// Examples:
//   node tools/dev/dir-to-json.mjs
//   node tools/dev/dir-to-json.mjs src/data out.json
//
// Behavior:
// - Walks the provided folder recursively (relative to repo root / CWD).
// - Emits a JSON array to out_file (default: lib_content.json).
// - Each entry: { path: "<relative path from repo root>", content: "<file content>" }.
// - Tries UTF-8 first; if content isn’t valid UTF-8, falls back to Base64 with an "encoding" field.

import { createWriteStream } from 'node:fs'
import { promises as fs } from 'node:fs'
import { join, relative, resolve } from 'node:path'
import process from 'node:process'

const [, , folderArg = '.', outArg = 'lib_content.json'] = process.argv
const repoRoot = resolve(process.cwd())
const baseDir = resolve(repoRoot, folderArg)
const outFile = resolve(repoRoot, outArg)

// Async recursive walker (follows directories; skips sockets/devices)
async function* walk(dir) {
  let entries
  try {
    entries = await fs.readdir(dir, { withFileTypes: true })
  } catch (e) {
    throw new Error(`Cannot read directory: ${dir} (${e.message})`)
  }
  for (const d of entries) {
    const full = join(dir, d.name)
    if (d.isDirectory()) {
      yield* walk(full)
    } else if (d.isFile()) {
      yield full
    } // silently ignore symlinks/specials
  }
}

// Robust UTF-8 reader: if decode looks lossy, emit base64 with encoding tag
async function readFileSmart(absPath) {
  const buf = await fs.readFile(absPath)
  // Heuristic: try to round-trip to detect likely binary
  const utf8 = buf.toString('utf8')
  const roundtrip = Buffer.from(utf8, 'utf8')
  const looksUtf8 = roundtrip.equals(buf)
  if (looksUtf8) {
    return { content: utf8, encoding: 'utf8' }
  }
  return { content: buf.toString('base64'), encoding: 'base64' }
}

async function main() {
  // Validate baseDir
  let stat
  try {
    stat = await fs.stat(baseDir)
  } catch (e) {
    throw new Error(`Folder not found: ${relative(repoRoot, baseDir)} (${e.message})`)
  }
  if (!stat.isDirectory()) {
    throw new Error(`Not a directory: ${relative(repoRoot, baseDir)}`)
  }

  const out = createWriteStream(outFile, { encoding: 'utf8' })
  let first = true

  await new Promise(async (resolveDone, reject) => {
    out.on('error', reject)
    out.write('[', 'utf8')

    try {
      for await (const abs of walk(baseDir)) {
        const { content, encoding } = await readFileSmart(abs)
        const relFromRoot = relative(repoRoot, abs).split('\\').join('/') // normalize
        const obj = encoding === 'utf8'
          ? { path: relFromRoot, content }
          : { path: relFromRoot, content, encoding } // include encoding only when base64
        const chunk = (first ? '' : ',') + JSON.stringify(obj)
        first = false
        if (!out.write(chunk, 'utf8')) {
          await new Promise((r) => out.once('drain', r))
        }
      }
      out.write(']\n', 'utf8', () => {
        out.end()
        resolveDone()
      })
    } catch (e) {
      reject(e)
    }
  })

  process.stdout.write(`Wrote ${relative(repoRoot, outFile)}\n`)
}

main().catch((err) => {
  process.stderr.write(`dir-to-json: ${err?.message || err}\n`)
  process.exit(1)
})
