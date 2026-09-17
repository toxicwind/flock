#!/usr/bin/env node

import fs from 'node:fs'
import fsp from 'node:fs/promises'
import http from 'node:http'
import path from 'node:path'
import { pathToFileURL } from 'node:url'

const args = process.argv.slice(2)
const options = {
  port: 4173,
  host: '127.0.0.1',
  dir: '_site',
}

for (let i = 0; i < args.length; i += 1) {
  const arg = args[i]
  if (arg === '--port' || arg === '-p') {
    const value = args[i + 1]
    if (!value) throw new Error('Missing value for --port')
    options.port = Number(value)
    i += 1
  } else if (arg === '--host' || arg === '-H') {
    const value = args[i + 1]
    if (!value) throw new Error('Missing value for --host')
    options.host = value
    i += 1
  } else if (arg === '--dir' || arg === '-d') {
    const value = args[i + 1]
    if (!value) throw new Error('Missing value for --dir')
    options.dir = value
    i += 1
  }
}

const rootDir = path.resolve(process.cwd(), options.dir)

if (!fs.existsSync(rootDir)) {
  console.error(`Static directory "${rootDir}" not found. Run \`npm run build:site\` first.`)
  process.exit(1)
}

const MIME_TYPES = new Map([
  ['.html', 'text/html; charset=utf-8'],
  ['.htm', 'text/html; charset=utf-8'],
  ['.css', 'text/css; charset=utf-8'],
  ['.js', 'application/javascript; charset=utf-8'],
  ['.mjs', 'application/javascript; charset=utf-8'],
  ['.json', 'application/json; charset=utf-8'],
  ['.svg', 'image/svg+xml'],
  ['.png', 'image/png'],
  ['.jpg', 'image/jpeg'],
  ['.jpeg', 'image/jpeg'],
  ['.gif', 'image/gif'],
  ['.webp', 'image/webp'],
  ['.ico', 'image/x-icon'],
  ['.woff2', 'font/woff2'],
  ['.woff', 'font/woff'],
  ['.ttf', 'font/ttf'],
])

function getContentType(filePath) {
  const ext = path.extname(filePath).toLowerCase()
  return MIME_TYPES.get(ext) || 'application/octet-stream'
}

function cleanPath(requestUrl) {
  const decoded = decodeURIComponent(requestUrl.split('?')[0])
  const normalized = path.normalize(decoded).replace(/^\.\//, '')
  const resolved = path.join(rootDir, normalized)
  if (!resolved.startsWith(rootDir)) {
    return rootDir
  }
  return resolved
}

async function resolveFilePath(requestPath) {
  try {
    const stats = await fsp.stat(requestPath)
    if (stats.isDirectory()) {
      const indexFile = path.join(requestPath, 'index.html')
      try {
        await fsp.access(indexFile)
        return { path: indexFile, stats: await fsp.stat(indexFile) }
      } catch {
        return null
      }
    }
    return { path: requestPath, stats }
  } catch {
    const fallback = `${requestPath}.html`
    try {
      const stats = await fsp.stat(fallback)
      return { path: fallback, stats }
    } catch {
      return null
    }
  }
}

const server = http.createServer(async (req, res) => {
  if (!req.url) {
    res.writeHead(400)
    res.end('Bad Request')
    return
  }

  const targetPath = cleanPath(req.url)
  const resolved = await resolveFilePath(targetPath)
  if (!resolved) {
    res.writeHead(404, { 'content-type': 'text/plain; charset=utf-8' })
    res.end('Not found')
    return
  }

  const { path: filePath, stats } = resolved
  res.writeHead(200, {
    'content-type': getContentType(filePath),
    'content-length': stats.size,
    'cache-control': 'no-store',
  })

  const stream = fs.createReadStream(filePath)
  stream.pipe(res)
})

server.keepAliveTimeout = 0

server.listen(options.port, options.host, () => {
  const origin = new URL(`http://${options.host}:${options.port}/`)
  console.log(`[static] Serving ${pathToFileURL(rootDir).href} → ${origin.href}`)
})

for (const signal of ['SIGINT', 'SIGTERM']) {
  process.on(signal, () => {
    server.close(() => process.exit(0))
  })
}
