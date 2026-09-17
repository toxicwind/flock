#!/usr/bin/env node
import { spawn } from 'node:child_process'
import process from 'node:process'

const args = process.argv.slice(2)

if (args.length === 0) {
  console.error('Usage: node tools/run-if-network.mjs <command> [args...]')
  process.exit(1)
}

const shouldSkip = process.env.CI && process.env.CI_NETWORK_OK !== '1'

if (shouldSkip) {
  console.log('CI network access disallowed; skipping command:', args.join(' '))
  process.exit(0)
}

const child = spawn(args[0], args.slice(1), { stdio: 'inherit' })
child.on('exit', (code) => {
  process.exit(code ?? 0)
})
child.on('error', (error) => {
  console.error(error)
  process.exit(1)
})
