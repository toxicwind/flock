
# EFFUSION-LABS BUG AUDIT — Actual Code Issues Found

## Bug 1: Missing Lockfile (CI-Breaking)
- **package-lock.json**: MISSING
- **bun.lock**: EXISTS (but bun not installed in CI)
- **CI uses**: `npm ci` which REQUIRES package-lock.json
- **Result**: `npm ci` fails → CI burns minutes retrying
- **Fix**: Run `npm install --package-lock-only` to generate package-lock.json
  OR change CI to use `bun install` (but bun must be installed first)

## Bug 2: Missing Config Files
- **eleventy.config.js**: MISSING (referenced in package.json scripts)
- **vite.config.ts**: MISSING (referenced in package.json scripts)
- **Result**: Build scripts fail because configs don't exist
- **Fix**: Create minimal config files or remove from scripts

## Bug 3: Permission Issues (FUSE Limitation)
- **package.json**: -rw------- (restrictive)
- **Can't fix in sandbox**: FUSE drive9 doesn't allow chmod
- **Fix on user machine**: `chmod 644 package.json`

## Bug 4: Bun Not Installed
- **bun**: NOT in PATH
- **bun.lock**: Exists but can't be used
- **Fix**: Install bun: `curl -fsSL https://bun.sh/install | bash`

## Root Cause
The project was initialized with bun but:
1. CI environment doesn't have bun
2. No package-lock.json for npm fallback
3. Config files referenced but not created
4. This causes CI to fail repeatedly → burns GitHub Actions minutes

## Fixes (Apply on User's Machine)
```bash
cd /path/to/effusion-labs

# 1. Install bun
curl -fsSL https://bun.sh/install | bash

# 2. Fix permissions
chmod 644 package.json

# 3. Generate lockfiles
bun install                    # creates bun.lock (if not exists)
npm install --package-lock-only # creates package-lock.json for CI

# 4. Create missing configs
cat > eleventy.config.js << 'EOF'
module.exports = function(eleventyConfig) {
  eleventyConfig.addPassthroughCopy("src/assets");
  return {
    dir: { input: "src", output: "_site" }
  };
};
EOF

cat > vite.config.ts << 'EOF'
import { defineConfig } from 'vite';
export default defineConfig({
  root: 'src',
  build: { outDir: '../dist' }
});
EOF

# 5. Commit and push
git add -A
git commit -m "fix: add lockfiles, configs, permissions"
git push

# 6. Re-enable CI workflows (after fixing code)
# Go to GitHub → repo → Actions → enable workflows
```
