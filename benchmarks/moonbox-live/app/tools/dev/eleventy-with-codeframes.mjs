// moved from utils/dev/eleventy-with-codeframes.mjs
import { codeFrameColumns } from '@babel/code-frame'
import { spawn } from 'node:child_process'
import fs from 'node:fs'
import path from 'node:path'
import pc from 'picocolors'

function extractNjkLocation(stderr) {
  const re = /\(([^)]+\.njk)\)\s*\[Line\s+(\d+),\s*Column\s+(\d+)]/g
  let match,
    last = null
  while ((match = re.exec(stderr))) last = match
  if (!last) return null
  const [, fileRaw, lineStr, colStr] = last
  const file = path.resolve(fileRaw)
  const line = parseInt(lineStr, 10) || 1
  const column = parseInt(colStr, 10) || 1
  return { file, line, column }
}
function printCodeframe({ file, line, column }) {
  if (!fs.existsSync(file)) return
  const src = fs.readFileSync(file, 'utf8')
  const frame = codeFrameColumns(
    src,
    { start: { line, column } },
    { linesAbove: 3, linesBelow: 3, highlightCode: true },
  )
  const rel = path.relative(process.cwd(), file)
  console.error('\n' + pc.bold(pc.red('Nunjucks parse error')))
  console.error(pc.dim(`${rel}:${line}:${column}`) + '\n')
  console.error(frame + '\n')
}
function runEleventy(argv = []) {
  const cp = spawn(
    process.platform === 'win32' ? 'npx.cmd' : 'npx',
    ['@11ty/eleventy', ...argv],
    { stdio: ['inherit', 'pipe', 'pipe'] },
  )
  let errBuf = ''
  cp.stdout.on('data', d => process.stdout.write(d))
  cp.stderr.on('data', d => {
    const s = d.toString()
    errBuf += s
    process.stderr.write(s)
  })
  cp.on('close', code => {
    if (code !== 0) {
      const loc = extractNjkLocation(errBuf)
      if (loc) printCodeframe(loc)
      process.exit(code)
    }
  })
}
runEleventy(process.argv.slice(2))
