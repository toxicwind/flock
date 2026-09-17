// src/utils/markdown/index.mjs
import markdownItFootnote from 'markdown-it-footnote'
import { footnotePopoverRefs, hybridFootnotes } from './parts/footnotes.js'
import { audioEmbed, qrEmbed } from './parts/inlineMacros.js'
import { externalLinks } from './parts/links.js'

export function applyMarkdownExtensions(md) {
  md.use(markdownItFootnote)
  try {
    hybridFootnotes(md)
  } catch (e) {
    console.error('[md-it] hybridFootnotes:', e?.message || e)
  }
  try {
    footnotePopoverRefs(md)
  } catch (e) {
    console.error('[md-it] footnotePopoverRefs:', e?.message || e)
  }
  try {
    audioEmbed(md)
  } catch (e) {
    console.error('[md-it] audioEmbed:', e?.message || e)
  }
  try {
    qrEmbed(md)
  } catch (e) {
    console.error('[md-it] qrEmbed:', e?.message || e)
  }
  try {
    externalLinks(md)
  } catch (e) {
    console.error('[md-it] externalLinks:', e?.message || e)
  }
  return md
}

export default { applyMarkdownExtensions }
