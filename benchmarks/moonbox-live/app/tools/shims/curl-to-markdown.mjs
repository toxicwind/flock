#!/usr/bin/env node
import { spawn } from 'node:child_process'
import path from 'node:path'
import process from 'node:process'
import { fileURLToPath } from 'node:url'

const realCurl = process.env.CURL_SHIM_REAL
const safePath = process.env.CURL_SHIM_SAFE_PATH || process.env.PATH || ''
const args = process.argv.slice(2)
const here = path.dirname(fileURLToPath(import.meta.url))
const repoRoot = path.resolve(here, '../..')
const modulePath = path.join(repoRoot, 'src/utils/net/webpageToMarkdown.mjs')

const MARKERS = {
  contentType: '__curl_shim_content_type__',
  effectiveUrl: '__curl_shim_effective_url__',
}

if (!realCurl) {
  console.error('curl shim: missing real curl path; install curl to use this shim.')
  process.exit(127)
}

function debugLog(...parts) {
  if (process.env.CURL_SHIM_DEBUG === '1') {
    console.error('[curl-shim]', ...parts)
  }
}

function runRealCurl() {
  debugLog('delegating to system curl')
  return new Promise((resolve, reject) => {
    const child = spawn(realCurl, args, {
      stdio: 'inherit',
      env: { ...process.env, PATH: safePath },
    })
    child.on('error', reject)
    child.on('exit', code => resolve(code ?? 0))
  })
}

function parseArgs() {
  let silent = false
  let showError = false
  let follow = false
  let url = null
  let supported = true

  for (let i = 0; i < args.length && supported; i += 1) {
    const arg = args[i]
    if (arg === '--') {
      supported = false
      break
    }
    if (arg.startsWith('--')) {
      switch (arg) {
        case '--silent':
          silent = true
          break
        case '--show-error':
          showError = true
          break
        case '--location':
          follow = true
          break
        default:
          supported = false
          break
      }
      continue
    }
    if (arg.startsWith('-') && arg !== '-') {
      const flags = arg.slice(1)
      for (const flag of flags) {
        switch (flag) {
          case 's':
            silent = true
            break
          case 'S':
            showError = true
            break
          case 'L':
            follow = true
            break
          default:
            supported = false
            break
        }
        if (!supported) break
      }
      continue
    }
    if (url === null) {
      url = arg
    } else {
      supported = false
      break
    }
  }

  return { silent, showError, follow, url, supported }
}

function execCurl(cmdArgs) {
  return new Promise((resolve, reject) => {
    const outChunks = []
    const errChunks = []
    const child = spawn(realCurl, cmdArgs, {
      env: { ...process.env, PATH: safePath },
    })
    child.stdout.on('data', chunk => outChunks.push(chunk))
    child.stderr.on('data', chunk => errChunks.push(chunk))
    child.on('error', reject)
    child.on('close', code => {
      resolve({
        code: code ?? 0,
        stdout: Buffer.concat(outChunks),
        stderr: Buffer.concat(errChunks),
      })
    })
  })
}

function decodeBody(buffer, contentType) {
  if (!buffer || buffer.length === 0) return ''
  const charsetMatch = /charset=([^;]+)/i.exec(contentType || '')
  const charset = charsetMatch ? charsetMatch[1].trim().toLowerCase() : 'utf-8'
  try {
    const decoder = new TextDecoder(charset)
    return decoder.decode(buffer)
  } catch {
    return buffer.toString('utf8')
  }
}

function decodeEntities(text = '') {
  return text
    .replace(/&#(\d+);/g, (_, num) => String.fromCharCode(Number.parseInt(num, 10)))
    .replace(/&#x([\da-f]+);/gi, (_, hex) => String.fromCharCode(Number.parseInt(hex, 16)))
    .replace(/&nbsp;/gi, ' ')
    .replace(/&amp;/gi, '&')
    .replace(/&lt;/gi, '<')
    .replace(/&gt;/gi, '>')
    .replace(/&quot;/gi, '"')
    .replace(/&apos;/gi, "'")
    .replace(/&ldquo;|&rdquo;/gi, '"')
    .replace(/&lsquo;|&rsquo;/gi, "'")
}

function stripTags(value = '') {
  return decodeEntities(value.replace(/<[^>]+>/g, ' '))
}

function basicHtmlToMarkdown(html = '', effectiveUrl = '') {
  if (!html) return ''
  let working = String(html)
  const titleMatch = /<title[^>]*>([\S\s]*?)<\/title>/i.exec(working)
  const title = titleMatch ? stripTags(titleMatch[1]).trim() : ''

  working = working
    .replace(/<head[\S\s]*?<\/head>/gi, ' ')
    .replace(/<script[\S\s]*?<\/script>/gi, ' ')
    .replace(/<style[\S\s]*?<\/style>/gi, ' ')
    .replace(/<!--([\S\s]*?)-->/g, ' ')

  working = working.replace(
    /<(h[1-6])[^>]*>([\S\s]*?)<\/\1>/gi,
    (match, tag, inner) => {
      const level = Number.parseInt(String(tag).slice(1), 10) || 1
      const prefix = '#'.repeat(Math.max(1, Math.min(level, 6)))
      const content = stripTags(inner).trim()
      return content ? `${prefix} ${content}\n\n` : ''
    },
  )

  working = working.replace(/<br\s*\/?>(?!\n)/gi, '\n')
  working = working.replace(/<br\s*\/?>(?=\s*<)/gi, '\n')

  working = working.replace(
    /<p[^>]*>([\S\s]*?)<\/p>/gi,
    (match, inner) => {
      const content = stripTags(inner).trim()
      return content ? `${content}\n\n` : ''
    },
  )

  working = working.replace(
    /<li[^>]*>([\S\s]*?)<\/li>/gi,
    (match, inner) => {
      const content = stripTags(inner).trim()
      return content ? `- ${content}\n` : ''
    },
  )

  working = working.replace(
    /<blockquote[^>]*>([\S\s]*?)<\/blockquote>/gi,
    (match, inner) => {
      const block = basicHtmlToMarkdown(inner)
      const lines = block.split(/\n+/).filter(Boolean)
      return lines.length ? `${lines.map(line => `> ${line}`).join('\n')}\n\n` : ''
    },
  )

  working = working.replace(
    /<pre[^>]*>([\S\s]*?)<\/pre>/gi,
    (match, inner) => {
      const cleaned = decodeEntities(inner.replace(/<\/?[^>]*>/g, '')).trim()
      return cleaned ? `\n\n\`\`\`\n${cleaned}\n\`\`\`\n\n` : ''
    },
  )

  working = working.replace(
    /<a[^>]*href=("|')([^"']+?)\1[^>]*>([\S\s]*?)<\/a>/gi,
    (match, _q, href, inner) => {
      const label = stripTags(inner).trim() || href
      return `[${label}](${href})`
    },
  )

  working = working.replace(
    /<(strong|b)[^>]*>([\S\s]*?)<\/(strong|b)>/gi,
    (match, _tag, inner) => {
      const content = stripTags(inner).trim()
      return content ? `**${content}**` : ''
    },
  )

  working = working.replace(
    /<(em|i)[^>]*>([\S\s]*?)<\/(em|i)>/gi,
    (match, _tag, inner) => {
      const content = stripTags(inner).trim()
      return content ? `_${content}_` : ''
    },
  )

  working = working.replace(/<[^>]+>/g, ' ')
  let text = decodeEntities(working)
  text = text.replace(/\r/g, '')
  text = text.replace(/[\t ]+\n/g, '\n')
  text = text.replace(/\n{3,}/g, '\n\n')
  text = text.replace(/[\t ]{2,}/g, ' ')
  const lines = text.split('\n').map(line => line.trim())
  let final = lines.join('\n').trim()
  if (title && !final.startsWith('# ')) {
    final = `# ${title}\n\n${final}`
  }
  if (effectiveUrl && final) {
    final += `\n\n---\nSource: ${effectiveUrl}`
  }
  return final
}

async function main() {
  if (process.env.CURL_SHIM_DISABLE === '1') {
    return runRealCurl()
  }

  const { silent, showError, follow, url, supported } = parseArgs()

  if (!supported || !url) {
    debugLog('unsupported arguments detected')
    return runRealCurl()
  }

  if (!/^https?:\/\//i.test(url)) {
    debugLog('non-http scheme', url)
    return runRealCurl()
  }

  if (!silent) {
    debugLog('requires -s/--silent to enable markdown conversion')
    return runRealCurl()
  }

  const curlArgs = ['-s']
  if (showError) curlArgs.push('-S')
  if (follow) curlArgs.push('-L')
  curlArgs.push(
    '-w',
    `\n${MARKERS.contentType}:%{content_type}\n${MARKERS.effectiveUrl}:%{url_effective}\n`,
  )
  curlArgs.push(url)

  let result
  try {
    result = await execCurl(curlArgs)
  } catch (error) {
    debugLog('curl invocation failed', error)
    if (!silent || showError) {
      const message = error && error.message ? error.message : String(error)
      console.error(`curl shim: ${message}`)
    }
    return 7
  }

  if (result.code !== 0) {
    debugLog('curl exited with code', result.code)
    if (!silent || showError) {
      if (result.stderr.length > 0) {
        process.stderr.write(result.stderr)
      } else {
        console.error(`curl: (${result.code}) request failed`)
      }
    }
    return result.code
  }

  const urlMarker = Buffer.from(`\n${MARKERS.effectiveUrl}:`)
  const typeMarker = Buffer.from(`\n${MARKERS.contentType}:`)

  const urlIndex = result.stdout.lastIndexOf(urlMarker)
  if (urlIndex === -1) {
    debugLog('unable to locate url marker; falling back')
    return runRealCurl()
  }
  const effectiveUrlBuf = result.stdout.slice(urlIndex + urlMarker.length)
  const beforeUrl = result.stdout.slice(0, urlIndex)
  const typeIndex = beforeUrl.lastIndexOf(typeMarker)
  if (typeIndex === -1) {
    debugLog('unable to locate content-type marker; falling back')
    return runRealCurl()
  }
  const typeBuf = beforeUrl.slice(typeIndex + typeMarker.length)
  const bodyBuf = beforeUrl.slice(0, typeIndex)

  const contentType = typeBuf.toString('utf8').trim()
  const effectiveUrl = effectiveUrlBuf.toString('utf8').trim() || url

  const isHtml = !contentType || /text\/html|application\/xhtml\+xml/i.test(contentType)
  if (!isHtml) {
    debugLog('content-type not html; streaming raw response', contentType)
    process.stdout.write(bodyBuf)
    return 0
  }

  const html = decodeBody(bodyBuf, contentType)

  let htmlToMarkdown
  try {
    ;({ htmlToMarkdown } = await import(modulePath))
  } catch (error) {
    debugLog('markdown module load failed', error)
  }

  let markdown = ''
  if (htmlToMarkdown) {
    try {
      markdown = await htmlToMarkdown(html, effectiveUrl)
    } catch (error) {
      debugLog('markdown conversion failed', error)
      if (!silent || showError) {
        const message = error && error.message ? error.message : String(error)
        console.error(`curl shim: markdown conversion failed: ${message}`)
      }
      markdown = ''
    }
  }

  if (!markdown || !markdown.trim()) {
    markdown = basicHtmlToMarkdown(html, effectiveUrl)
  }

  if (!markdown || !markdown.trim()) {
    debugLog('conversion empty; streaming raw html fallback')
    process.stdout.write(bodyBuf)
    return 0
  }

  if (!markdown.endsWith('\n')) {
    markdown += '\n'
  }
  process.stdout.write(markdown)
  return 0
}

try {
  const code = await main()
  process.exit(typeof code === 'number' ? code : 0)
} catch (error) {
  debugLog('unexpected error', error)
  try {
    const code = await runRealCurl()
    process.exit(code)
  } catch (fallbackError) {
    debugLog('fallback execution failed', fallbackError)
    process.exit(127)
  }
}
