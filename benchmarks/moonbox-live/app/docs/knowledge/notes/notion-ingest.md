# Eleventy capture tooling

Use the Eleventy capture scripts to generate new Effusion Labs pages with consistent frontmatter.

Entry points:
- `bun run eleventy:spark -- --title "<title>" --description "<desc>"`
- `bun run eleventy:concept -- --title "<title>" --description "<desc>"`
- `bun run eleventy:project -- --title "<title>" --description "<desc>"`
- `bun run eleventy:meta -- --title "<title>" --description "<desc>"`

Outputs land in `src/content/docs/eleventy/<type>/` with tags `eleventy/<type>`. The project name
defaults to `effusion_labs_final` via `tools/eleventy/config.mjs`.
