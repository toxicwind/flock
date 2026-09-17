#!/usr/bin/env node
import libnpmsearch from 'libnpmsearch'
import { execSync } from 'node:child_process'
import npmFetch from 'npm-registry-fetch'

async function search(keyword) {
  const results = await libnpmsearch(keyword, { size: 20 })
  for (const r of results) {
    console.log(`${r.name}@${r.version} - ${r.description}`)
  }
}

async function view(pkg) {
  const info = await npmFetch.json(pkg)
  console.log(JSON.stringify(info, null, 2))
}

async function analyze(keyword) {
  const results = await libnpmsearch(keyword, { size: 10, detailed: true })
  const enriched = []
  for (const r of results) {
    const pkg = r.package || r
    try {
      const info = await npmFetch.json(pkg.name)
      const lastPublish = info.time?.modified || info.time?.[pkg.version] || 'unknown'
      enriched.push({
        name: pkg.name,
        version: pkg.version,
        description: pkg.description,
        lastPublish,
        score: r.score?.final ?? 0,
      })
    } catch {
      // ignore packages we cannot fetch
    }
  }
  enriched.sort((a, b) => b.score - a.score)
  console.log(JSON.stringify(enriched, null, 2))
}

async function install(pkg) {
  const info = await npmFetch.json(pkg)
  const version = info['dist-tags']?.latest || info.version
  execSync(`npm install ${pkg}@${version} --save-exact`, { stdio: 'inherit' })
}

async function main() {
  const [, , cmd, arg] = process.argv
  if (!cmd || !arg || !['search', 'view', 'analyze', 'install'].includes(cmd)) {
    console.error('Usage: npm-utils <search|view|analyze|install> <arg>')
    process.exit(1)
  }
  try {
    if (cmd === 'search') await search(arg)
    else if (cmd === 'view') await view(arg)
    else if (cmd === 'analyze') await analyze(arg)
    else if (cmd === 'install') await install(arg)
  } catch (err) {
    console.error(err.message)
    process.exit(1)
  }
}

main()
