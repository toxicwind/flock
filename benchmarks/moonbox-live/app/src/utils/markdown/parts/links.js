// src/utils/markdown/parts/links.js
export function externalLinks(md) {
  const base = md.renderer.rules.link_open || ((t, i, o, e, s) => s.renderToken(t, i, o))
  md.renderer.rules.link_open = (tokens, idx, options, env, self) => {
    const href = tokens[idx].attrGet('href') || ''
    const isHttp = /^https?:\/\//i.test(href)
    const siteUrl = env?.site?.url || ''
    const isOwnAbsolute = siteUrl && href.startsWith(siteUrl)
    if (isHttp && !isOwnAbsolute) {
      tokens[idx].attrSet('target', '_blank')
      tokens[idx].attrSet('rel', 'noopener noreferrer ugc')
      tokens[idx].attrJoin('class', 'external-link')
      const nxt = tokens[idx + 1]
      if (nxt?.type === 'text' && !/^↗/.test(nxt.content.trim())) {
        nxt.content = `↗ ${nxt.content}`
      }
    }
    return base(tokens, idx, options, env, self)
  }
}

export default { externalLinks }
