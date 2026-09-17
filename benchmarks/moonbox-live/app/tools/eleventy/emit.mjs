#!/usr/bin/env node
import fs from "node:fs/promises";
import path from "node:path";
import matter from "gray-matter";
import {
  ELEVENTY_CONTENT_ROOT,
  ELEVENTY_PROJECT_NAME,
  ELEVENTY_TAG_ROOT,
} from "./config.mjs";

export async function main(argv = process.argv.slice(2)) {
  const args = parseArgs(argv);
  const type = normalizeType(args.type || "general");
  const title = args.title || "Eleventy Capture";
  const description = args.description || "";
  const date = args.date || new Date().toISOString();
  const tags = normalizeTags(args.tags);
  const body = await readBody(args);
  const slug = args.slug || slugify(title) || defaultSlug(type);

  const data = {
    title,
    description,
    date,
    tags: uniqueTags([
      ELEVENTY_TAG_ROOT,
      `${ELEVENTY_TAG_ROOT}/${type}`,
      ...tags,
    ]),
    eleventy_type: type,
    eleventy_project: ELEVENTY_PROJECT_NAME,
  };

  const outputDir = path.join(ELEVENTY_CONTENT_ROOT, type);
  const outputPath = path.join(outputDir, `${slug}.md`);
  await fs.mkdir(outputDir, { recursive: true });
  const payload = matter.stringify(body, data);
  await fs.writeFile(outputPath, payload);
  console.log(outputPath);
}

if (import.meta.url === `file://${process.argv[1]}`) {
  main().catch((err) => {
    console.error(err?.message || err);
    process.exit(1);
  });
}

function parseArgs(argv) {
  const out = {};
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === "--type") out.type = argv[++i];
    else if (arg === "--title") out.title = argv[++i];
    else if (arg === "--description") out.description = argv[++i];
    else if (arg === "--tags") out.tags = argv[++i];
    else if (arg === "--slug") out.slug = argv[++i];
    else if (arg === "--date") out.date = argv[++i];
  }
  return out;
}

async function readBody(args) {
  let body = "";
  if (process.stdin.isTTY) {
    body = "";
  } else {
    process.stdin.setEncoding("utf8");
    for await (const chunk of process.stdin) {
      body += chunk;
    }
  }
  if (!body.trim()) {
    return "## Summary\n\n## Details\n\n## Next steps\n";
  }
  return body.trimEnd() + "\n";
}

function normalizeType(value) {
  return slugify(value || "general");
}

function normalizeTags(tags) {
  if (!tags) return [];
  if (Array.isArray(tags)) return tags.map(String);
  if (typeof tags === "string") {
    return tags
      .split(",")
      .map((tag) => tag.trim())
      .filter(Boolean);
  }
  return [];
}

function uniqueTags(tags) {
  const seen = new Set();
  return tags.filter((tag) => {
    const key = String(tag || "").trim();
    if (!key || seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function slugify(value) {
  return String(value || "")
    .normalize("NFKD")
    .toLowerCase()
    .replace(/[^\w\s-]/g, "")
    .trim()
    .replace(/\s+/g, "-")
    .replace(/-+/g, "-");
}

function defaultSlug(type) {
  const stamp = new Date().toISOString().replace(/[:.]/g, "");
  return `${type}-${stamp}`;
}
