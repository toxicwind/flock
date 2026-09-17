import { fetch } from 'undici'
// Prefer the local gateway implementation to keep container builds self-contained.
import { resolveChromium } from '../../tools/resolve-chromium.mjs'
import { resolveSidecar } from '../sidecars/resolver.mjs'
import { assertAllowed } from './lib/host-allowlist.mjs'
import { htmlToMarkdown } from './lib/webToMd.js'

function normUrl(u) {
  try {
    const url = new URL(u)
    return url.toString()
  } catch {
    const url = new URL(`https://${u}`)
    return url.toString()
  }
}

function isCloudflare(headers, body, status) {
  const h = Object.fromEntries(
    Object.entries(headers || {}).map(([k, v]) => [
      String(k).toLowerCase(),
      String(v),
    ]),
  )
  if (h['server']?.toLowerCase() === 'cloudflare') return true
  const txt = typeof body === 'string' ? body : ''
  if (
    /__cf_bm|just a moment|cf-mitigated:\s*challenge|\/cdn-cgi\/challenge-platform\//i.test(
      txt,
    )
  ) {
    return true
  }
  if (status && [401, 403, 429].includes(Number(status))) return true
  return false
}

async function directFetch(url, { headers }) {
  const res = await fetch(url, {
    method: 'GET',
    headers: {
      'user-agent': UA,
      'accept-language': 'en-US,en;q=0.9',
      ...(headers || {}),
    },
    redirect: 'follow',
    signal: AbortSignal.timeout(60_000),
  })
  const buf = Buffer.from(await res.arrayBuffer())
  const text = buf.toString('utf8')
  return {
    ok: res.ok,
    status: res.status,
    url: res.url,
    headers: Object.fromEntries(res.headers.entries()),
    body: text,
    bytes: buf.length,
  }
}

async function flareFetch(url, { headers, base }) {
  const baseUrl = base || process.env.FLARESOLVERR_URL
  if (!baseUrl) throw new Error('flaresolverr_not_configured')
  const res = await fetch(new URL('/v1', baseUrl).toString(), {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({
      cmd: 'request.get',
      url,
      maxTimeout: 60_000,
      headers: { 'user-agent': UA, ...(headers || {}) },
    }),
    signal: AbortSignal.timeout(75_000),
  })
  if (!res.ok) throw new Error(`flaresolverr_bad_status:${res.status}`)
  const json = await res.json()
  const sol = json.solution || {}
  return {
    ok: true,
    status: Number(sol.status || 200),
    url: sol.url || url,
    headers: sol.headers || {},
    body: sol.response || '',
    bytes: Buffer.byteLength(sol.response || ''),
  }
}

const UA =
  'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

export async function readWeb(inputUrl, opts = {}) {
  const url = normUrl(inputUrl)
  assertAllowed(url)
  let last
  // Try direct first
  last = await directFetch(url, opts).catch(e => ({
    ok: false,
    error: String(e),
  }))
  if (last.ok && !isCloudflare(last.headers, last.body, last.status)) {
    const md = htmlToMarkdown(last.body, last.url)
    return {
      ok: true,
      url: last.url,
      status: last.status,
      contentType: last.headers?.['content-type'],
      md,
      bytes: last.bytes,
      mode: 'direct',
    }
  }
  // If CF hinted, auto-discover FlareSolverr (env or DNS) and try it
  const flareSidecar = resolveSidecar('flaresolverr')
  const flareBase = await discoverFlareBase(flareSidecar?.url).catch(() => null)
  if (flareBase || process.env.FLARESOLVERR_URL) {
    const via = await flareFetch(url, {
      ...opts,
      base: flareBase || process.env.FLARESOLVERR_URL,
    }).catch(e => ({ ok: false, error: String(e) }))
    if (via.ok) {
      const md = htmlToMarkdown(via.body, via.url)
      return {
        ok: true,
        url: via.url,
        status: via.status,
        contentType: via.headers?.['content-type'],
        md,
        bytes: via.bytes,
        mode: 'flaresolverr',
      }
    }
    return {
      ok: false,
      url,
      error: via.error || 'flaresolverr_failed',
      mode: 'flaresolverr',
    }
  }
  return {
    ok: false,
    url,
    error: last.error || 'cloudflare_challenge',
    mode: 'degraded',
  }
}

export async function screenshotUrl(inputUrl, _opts = {}) {
  const url = normUrl(inputUrl)
  assertAllowed(url)
  let chromium
  try {
    // Prefer full playwright if available
    ;({ chromium } = await import('playwright'))
  } catch {
    try {
      ;({ chromium } = await import('@playwright/test'))
    } catch {}
  }
  if (!chromium) return { ok: false, url, error: 'playwright_not_available' }
  const browser = await chromium.launch({ headless: true, executablePath: resolveChromium() })
  try {
    const ctx = await browser.newContext({
      userAgent: UA,
      viewport: { width: 1280, height: 800 },
    })
    const page = await ctx.newPage()
    await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60_000 })
    const buf = await page.screenshot({ fullPage: true, type: 'png' })
    return {
      ok: true,
      url: page.url(),
      bytes: buf.length,
      mime: 'image/png',
      base64: buf.toString('base64'),
      mode: 'playwright',
    }
  } finally {
    await browser.close()
  }
}

async function discoverFlareBase(candidate) {
  const base = candidate || process.env.FLARESOLVERR_URL || 'http://flaresolverr:8191'
  // Try a very quick probe to see if something is listening; many containers respond 404 on '/'
  const url = new URL('/', base).toString()
  try {
    const res = await fetch(url, {
      method: 'GET',
      signal: AbortSignal.timeout(1500),
    })
    if (res.status >= 200 && res.status < 500) return base // something is there
  } catch {}
  // Try POST /v1 with a harmless command expecting 200/4xx
  try {
    const res = await fetch(new URL('/v1', base).toString(), {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ cmd: 'sessions.list' }),
      signal: AbortSignal.timeout(1500),
    })
    if (res.status >= 200 && res.status < 500) return base
  } catch {}
  throw new Error('flaresolverr_unreachable')
}
