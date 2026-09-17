// src/utils/filters/index.mjs
import { icons } from 'lucide'
import defaultAttributes from 'lucide/dist/esm/defaultAttributes.js'
import { DateTime } from 'luxon'
import fs from 'node:fs'
import path from 'node:path'
import generateConceptMapJSONLD from '../build/concept-map.js'
const iconRegistry = icons

const fileCache = new Map()
const toStr = v => String(v ?? '')
const escapeHtml = str =>
  String(str ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;')

function readFileCached(p) {
  try {
    const { mtimeMs } = fs.statSync(p)
    const cached = fileCache.get(p)
    if (cached?.mtimeMs === mtimeMs) return cached.data
    const data = fs.readFileSync(p, 'utf8')
    fileCache.set(p, { mtimeMs, data })
    return data
  } catch {
    return null
  }
}

function ordinalSuffix(n) {
  const abs = Math.abs(n)
  if (abs % 100 >= 11 && abs % 100 <= 13) return 'th'
  return ['th', 'st', 'nd', 'rd'][abs % 10] || 'th'
}

const defaultFilters = {
  readableDate: (d, zone = 'utc') => {
    if (!(d instanceof Date)) return ''
    const dt = DateTime.fromJSDate(d, { zone })
    return `${dt.toFormat('MMMM d')}${ordinalSuffix(dt.day)}, ${dt.toFormat('yyyy')}`
  },
  htmlDateString: d =>
    d instanceof Date
      ? DateTime.fromJSDate(d, { zone: 'utc' }).toFormat('yyyy-MM-dd')
      : '',
  readingTime: (text = '', wordsPerMinute = 200) => {
    const count = toStr(text).trim().split(/\s+/).filter(Boolean).length
    const minutes = Math.max(1, Math.ceil(count / wordsPerMinute))
    return `${minutes} min read`
  },
  truncate: (str = '', n = 140) => {
    if (typeof str !== 'string' || n <= 0) return ''
    return str.length > n ? `${str.slice(0, n)}…` : str
  },
  slugify: (str = '') =>
    String(str)
      .toLowerCase()
      .trim()
      .replace(/[^\da-z]+/g, '-')
      .replace(/(^-|-$)+/g, ''),
  limit: (arr = [], n = 5) => (Array.isArray(arr) ? arr.slice(0, n) : []),
  isNew: (d, days = 14) => {
    if (!(d instanceof Date)) return false
    const now = DateTime.now().toUTC()
    const then = DateTime.fromJSDate(d, { zone: 'utc' })
    return now.diff(then, 'days').days <= days
  },
  shout: (str = '') => toStr(str).toUpperCase(),
  money: (value = 0, code = '') => {
    const num = Number(value)
    const cur = toStr(code).toUpperCase()
    if (Number.isNaN(num)) return ''
    return cur ? `${cur} ${num.toFixed(2)}` : `${num.toFixed(2)}`
  },
  yesNo: v => (v ? 'Yes' : 'No'),
  humanDate: (iso = '') => {
    if (typeof iso !== 'string' || !iso) return ''
    const d = DateTime.fromISO(iso, { zone: 'utc' })
    if (!d.isValid) return ''
    const fmt = d.toFormat('yyyy-LL-dd')
    return `<time datetime="${escapeHtml(iso)}">${fmt}</time>`
  },
  titleizeSlug: (str = '') =>
    toStr(str)
      .split('-')
      .filter(Boolean)
      .map(s => s.charAt(0).toUpperCase() + s.slice(1))
      .join(' '),
  hostname: (url = '') => {
    try {
      return new URL(url).hostname
    } catch {
      return ''
    }
  },
  absoluteUrl: (p = '', base = process.env.SITE_URL || '') => {
    try {
      return new URL(p, base).toString()
    } catch {
      return p
    }
  },
  conceptMapJSONLD: (pages = []) => JSON.stringify(generateConceptMapJSONLD(pages)),
  jsonify: v => JSON.stringify(v),
  date: (value, fmt = 'yyyy-LL-dd') => {
    try {
      let dt
      if (value instanceof Date) {
        dt = DateTime.fromJSDate(value, { zone: 'utc' })
      } else if (typeof value === 'number') {
        dt = DateTime.fromMillis(value, { zone: 'utc' })
      } else if (typeof value === 'string') {
        dt = DateTime.fromISO(value, { zone: 'utc' })
      } else return ''
      return dt.isValid ? dt.toFormat(fmt) : ''
    } catch {
      return ''
    }
  },
  provenanceSources: (ref = '') => {
    if (typeof ref !== 'string' || ref.trim() === '') return []
    const rel = ref.startsWith('/') ? ref.slice(1) : ref
    const full = path.join(process.cwd(), 'src', rel)
    const raw = readFileCached(full)
    if (raw === null) return []
    return raw
      .trim()
      .split('\n')
      .filter(Boolean)
      .map(line => {
        try {
          return JSON.parse(line)
        } catch {
          return null
        }
      })
      .filter(Boolean)
  },
  provenanceViewerUrl: (ref = '') => {
    if (typeof ref !== 'string' || !ref.includes('/provenance/')) return ref
    const clean = ref.replace(/^\/*content\//, '')
    const parts = clean.split('/')
    const idx = parts.lastIndexOf('provenance')
    if (idx < 0 || !parts[idx + 1]) return ref
    const file = parts[idx + 1].replace(/\.jsonl$/, '')
    const slug = file.replace(/--+/g, '-')
    const prefix = parts.slice(1, idx).join('/')
    return `/archives/${prefix}/provenance/${slug}/`
  },
  provenanceDownloadUrl: (ref = '') => {
    if (typeof ref !== 'string' || !ref.includes('/provenance/')) return ref
    const clean = ref.replace(/^\/*content\//, '')
    const parts = clean.split('/')
    const idx = parts.lastIndexOf('provenance')
    if (idx < 0 || !parts[idx + 1]) return ref
    const file = parts[idx + 1].replace(/\.jsonl$/, '')
    const slug = file.replace(/--+/g, '-')
    const prefix = parts.slice(1, idx).join('/')
    return `/archives/${prefix}/provenance/${slug}.jsonl`
  },
}

function fieldCounts(obj = {}, excludeKeys = []) {
  try {
    const o = obj && typeof obj === 'object' ? obj : {}
    const sys = new Set(
      [
        'industry',
        'industrySlug',
        'category',
        'categorySlug',
        'company',
        'companySlug',
        'line',
        'lineSlug',
        'section',
        'locale',
        '__source',
        '__rel',
        'url',
        'title',
        'lineTitle',
        'companyTitle',
        'categoryTitle',
        'industryTitle',
        'productSlug',
        'product_id',
        'charSlug',
        'name',
        'seriesSlug',
        'page',
        'collections',
      ].concat(Array.isArray(excludeKeys) ? excludeKeys : []),
    )
    const keys = Object.keys(o).filter(k => !sys.has(k))
    const total = keys.length
    let present = 0
    for (const k of keys) {
      if (
        (v =>
          v == null
            ? false
            : Array.isArray(v)
            ? v.length > 0
            : typeof v === 'string'
            ? v.trim().length > 0
            : typeof v === 'object'
            ? Object.keys(v).length > 0
            : true)(o[k])
      ) {
        present += 1
      }
    }
    return { total, present }
  } catch {
    return { total: 0, present: 0 }
  }
}

const len = v => (Array.isArray(v) ? v.length : 0)

export function registerFilters(eleventyConfig) {
  Object.entries(defaultFilters).forEach(([name, fn]) => eleventyConfig.addFilter(name, fn))

  const toJson = (value, spaces = 0) => {
    const json = JSON.stringify(value ?? null, null, spaces)
    return String(json)
      .replace(/</g, '\\u003C')
      .replace(/--!?>/g, '\\u002D\\u002D>')
  }
  eleventyConfig.addFilter('json', toJson)
  eleventyConfig.addNunjucksFilter('json', toJson)
  eleventyConfig.addFilter('dump', toJson)
  eleventyConfig.addNunjucksFilter('dump', toJson)

  eleventyConfig.addFilter('fieldCounts', fieldCounts)
  eleventyConfig.addFilter('fieldRatio', (obj = {}, exclude = []) => {
    const { total, present } = fieldCounts(obj, exclude)
    return `${present}/${total}`
  })
  eleventyConfig.addFilter('len', len)

  // Extra helpers used across templates
  eleventyConfig.addFilter('compactUnique', arr => Array.from(new Set((arr || []).filter(Boolean))))
  eleventyConfig.addFilter(
    'safe_upper',
    (value, fallback = '', coerce = false) => {
      if (typeof value === 'string') return value.toUpperCase()
      if (value == null) return fallback
      return coerce ? String(value).toUpperCase() : fallback
    },
  )

  // Mutation helpers for Nunjucks use (safe, defensive)
  const setAttribute = (obj, key, value) => {
    try {
      if (!obj || typeof obj !== 'object') return obj
      obj[key] = value
      return obj
    } catch {
      return obj
    }
  }
  const push = (arr, value) => {
    try {
      if (Array.isArray(arr)) {
        arr.push(value)
        return arr
      }
      return arr
    } catch {
      return arr
    }
  }
  eleventyConfig.addFilter('setAttribute', setAttribute)
  eleventyConfig.addNunjucksFilter('setAttribute', setAttribute)
  eleventyConfig.addFilter('push', push)
  eleventyConfig.addNunjucksFilter('push', push)

  // Lucide helper
  eleventyConfig.addFilter('lucide', (name, attrs = {}) => {
    try {
      if (!name || typeof name !== 'string') return ''
      const toPascal = s =>
        s
          .split(/[\s.:_-]+/)
          .filter(Boolean)
          .map(p => p.charAt(0).toUpperCase() + p.slice(1))
          .join('')
      const key = toPascal(name)
      const node = iconRegistry[key] || iconRegistry[name]
      if (!node) return ''

      const toAttrString = obj =>
        Object.entries(obj)
          .filter(([, value]) => value !== undefined && value !== null && value !== false)
          .map(([k, v]) => `${k}="${escapeHtml(v)}"`)
          .join(' ')

      const renderChildren = childNodes =>
        (Array.isArray(childNodes) ? childNodes : [])
          .map(entry => {
            if (!Array.isArray(entry) || entry.length === 0) return ''
            const [tag, attr = {}, nested] = entry
            const rendered = renderChildren(nested)
            const attrsHtml = toAttrString(attr)
            const openTag = attrsHtml ? `<${tag} ${attrsHtml}` : `<${tag}`
            if (rendered) {
              return `${openTag}>${rendered}</${tag}>`
            }
            return `${openTag} />`
          })
          .join('')

      let svgAttrs = { ...defaultAttributes, ...attrs }
      let childEntries = []

      if (Array.isArray(node) && node[0] === 'svg') {
        // Legacy lucide signature: ['svg', attrs, children]
        const [, iconAttrs, children] = node
        svgAttrs = { ...defaultAttributes, ...(iconAttrs || {}), ...attrs }
        childEntries = Array.isArray(children) ? children : []
      } else if (Array.isArray(node)) {
        // Modern lucide signature: array of child tuples
        childEntries = node
      } else if (Array.isArray(node?.iconNode)) {
        // Catch-all for other shapes ({ iconNode: [...] })
        childEntries = node.iconNode
        if (node.attrs && typeof node.attrs === 'object') {
          svgAttrs = { ...defaultAttributes, ...node.attrs, ...attrs }
        }
      }

      return `<svg ${toAttrString(svgAttrs)}>${renderChildren(childEntries)}</svg>`
    } catch {
      return ''
    }
  })
}

export default { registerFilters }
