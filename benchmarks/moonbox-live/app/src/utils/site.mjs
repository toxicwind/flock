// src/utils/site.mjs
// Central site and directory configuration used by Eleventy and helpers.
import path from 'node:path'

export const dirs = {
  input: 'src',
  output: process.env.ELEVENTY_TEST_OUTPUT || '_site',
  includes: '_includes',
  data: '_data',
}

export const baseContentPath = 'src/content'
export const CONCEPTS_DIR = path.join(baseContentPath, 'concepts')
export const CONTENT_AREAS = [
  'sparks',
  'concepts',
  'projects',
  'archives',
  'meta',
]

export default { dirs, baseContentPath, CONCEPTS_DIR, CONTENT_AREAS }
