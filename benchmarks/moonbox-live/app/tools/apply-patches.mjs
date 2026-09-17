#!/usr/bin/env node
import { spawn } from 'node:child_process'
import { readdir } from 'node:fs/promises'
import path from 'node:path'
import process from 'node:process'
import { fileURLToPath } from 'node:url'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const patchesDir = path.join(root, 'patches')

const args = new Set(process.argv.slice(2))
const checkOnly = args.has('--check')
const force = args.has('--force')
const verbose = args.has('--verbose')

if (args.has('--help')) {
  console.log(
    `Usage: node tools/apply-patches.mjs [--check] [--force] [--verbose]\n\n`
      + `Applies unified diff patches located in the \\"patches\\" directory.\n`
      + `--check   Validate patches without applying them (succeeds if already applied).\n`
      + `--force   Apply patches even when PATCH_PACKAGE_RUN=0.\n`
      + `--verbose Show git output while applying patches.`,
  )
  process.exit(0)
}

if (!checkOnly && process.env.PATCH_PACKAGE_RUN === '0' && !force) {
  if (verbose) {
    console.log('Skipping patch application because PATCH_PACKAGE_RUN=0')
  }
  process.exit(0)
}

async function runGit(args, { allowFailure = false, stream = false } = {}) {
  return await new Promise((resolve, reject) => {
    const child = spawn('git', args, {
      cwd: root,
      stdio: stream ? ['ignore', 'inherit', 'inherit'] : ['ignore', 'pipe', 'pipe'],
    })

    if (stream) {
      child.on('exit', (code) => {
        if (code === 0 || allowFailure) {
          resolve({ code })
        } else {
          reject(new Error(`git ${args.join(' ')} exited with code ${code}`))
        }
      })
      return
    }

    let stdout = ''
    let stderr = ''
    child.stdout.on('data', (data) => {
      stdout += data
    })
    child.stderr.on('data', (data) => {
      stderr += data
    })

    child.on('error', (error) => {
      reject(error)
    })

    child.on('exit', (code) => {
      if (code === 0 || allowFailure) {
        resolve({ code, stdout, stderr })
      } else {
        const error = new Error(`git ${args.join(' ')} exited with code ${code}`)
        error.stdout = stdout
        error.stderr = stderr
        reject(error)
      }
    })
  })
}

async function listPatchFiles() {
  try {
    const entries = await readdir(patchesDir, { withFileTypes: true })
    return entries
      .filter((entry) => entry.isFile() && entry.name.endsWith('.patch'))
      .map((entry) => entry.name)
      .sort((a, b) => a.localeCompare(b))
  } catch (error) {
    if (error.code === 'ENOENT') {
      return []
    }
    throw error
  }
}

async function main() {
  const patchFiles = await listPatchFiles()
  if (patchFiles.length === 0) {
    if (verbose) {
      console.log('No patch files found.')
    }
    return
  }

  for (const patchName of patchFiles) {
    const patchPath = path.join(patchesDir, patchName)
    const relPath = path.relative(root, patchPath)

    const checkResult = await runGit(['apply', '--check', relPath], { allowFailure: true })
    if (checkResult.code === 0) {
      if (checkOnly) {
        if (verbose) {
          console.log(`✔ ${patchName} applies cleanly.`)
        }
        continue
      }
      await runGit(['apply', '--ignore-space-change', '--whitespace=nowarn', relPath], {
        stream: verbose,
      })
      if (!verbose) {
        console.log(`Applied ${patchName}`)
      }
      continue
    }

    const reverseCheck = await runGit(['apply', '--reverse', '--check', relPath], {
      allowFailure: true,
    })
    if (reverseCheck.code === 0) {
      if (checkOnly) {
        if (verbose) {
          console.log(`✔ ${patchName} already applied.`)
        }
      } else if (verbose) {
        console.log(`Skipping ${patchName}; already applied.`)
      }
      continue
    }

    const details = [
      checkResult.stderr?.trim(),
      reverseCheck.stderr?.trim(),
    ].filter(Boolean).join('\n')
    throw new Error(`Failed to apply ${patchName}.\n${details}`)
  }
}

main().catch((error) => {
  console.error(error instanceof Error ? error.message : error)
  if (error?.stderr && verbose) {
    console.error(error.stderr)
  }
  process.exit(1)
})
