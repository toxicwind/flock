// src/utils/markdown/parts/inlineMacros.js
const toStr = v => (v == null ? '' : String(v))

function parseArgs(src) {
  let s = src.trim()
  const out = []
  let cur = ''
  let inStr = false
  let chStr = ''
  let depth = 0
  for (let i = 0; i < s.length; i++) {
    const ch = s[i]
    if (inStr) {
      if (ch === chStr && s[i - 1] !== '\\') inStr = false
      cur += ch
      continue
    }
    if (ch === '"' || ch === "'") {
      inStr = true
      chStr = ch
      cur += ch
      continue
    }
    if (ch === '(') {
      depth++
      cur += ch
      continue
    }
    if (ch === ')') {
      depth = Math.max(0, depth - 1)
      cur += ch
      continue
    }
    if (ch === ',' && depth === 0) {
      out.push(cur.trim().replace(/^["']|["']$/g, ''))
      cur = ''
      continue
    }
    cur += ch
  }
  if (cur) out.push(cur.trim().replace(/^["']|["']$/g, ''))
  return out
}

function inlineMacro(name, after, render) {
  const re = new RegExp(`^@${name}\\(([^)]*)\\)`)
  return md => {
    md.inline.ruler.after(after, name, (state, silent) => {
      if (!state) return false
      const src = state.src.slice(state.pos)
      const m = src.match(re)
      if (!m) return false
      if (!silent) {
        const args = parseArgs(m[1])
        const html = render(...args.map(toStr))
        state.push({ type: 'html_inline', content: html })
      }
      state.pos += m[0].length
      return true
    })
  }
}

export const audioEmbed = inlineMacro('audio', 'emphasis', (url, label) => {
  const u = toStr(url)
  const lab = toStr(label || '')
  const cap = lab
    ? `<figcaption class="text-xs opacity-70 mt-1">${lab}</figcaption>`
    : ''
  return `<figure class="audio-embed not-prose"><audio controls class="w-full" src="${u}"></audio>${cap}</figure>`
})

export const qrEmbed = inlineMacro('qr', 'audio', text => {
  const v = encodeURIComponent(toStr(text))
  return `<img class="qr-code border-2 shadow-[4px_4px_0_rgba(0,0,0,.85)]" src="https://api.qrserver.com/v1/create-qr-code/?size=150x150&data=${v}" alt="QR code">`
})

export default { audioEmbed, qrEmbed }
