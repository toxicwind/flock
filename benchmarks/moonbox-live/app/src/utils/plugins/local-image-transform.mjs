import eleventyImageModule from '@11ty/eleventy-img'

function resolveImageTransformPlugin() {
  const plugin = eleventyImageModule?.eleventyImageTransformPlugin

  if (typeof plugin === 'function') {
    return plugin
  }

  const availableKeys = Object.keys(eleventyImageModule ?? {})
  throw new Error(
    `@11ty/eleventy-img did not expose eleventyImageTransformPlugin (available: ${
      availableKeys.join(', ')
    })`,
  )
}

export function localImageTransformPlugin(eleventyConfig, options = {}) {
  return resolveImageTransformPlugin()(eleventyConfig, options)
}

export default localImageTransformPlugin
