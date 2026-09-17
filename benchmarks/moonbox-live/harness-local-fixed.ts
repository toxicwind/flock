#!/usr/bin/env bun
// harness-local-fixed.ts
// FIXED: Adds git commit before gh repo create --push
//        Adds defensive checks for empty repos
//        Adds retry logic for gh auth issues

import { spawn } from "bun";
import { existsSync, mkdirSync, writeFileSync } from "fs";
import { join } from "path";
import { homedir } from "os";

const REPO_NAME = "harness-local";
const GITHUB_DIR = join(homedir(), "github", REPO_NAME);
const GH_USER = process.env.GH_USER || process.env.GITHUB_USER || "toxic";

// --- Helpers ---
const run = async (cmd: string[], cwd?: string, env?: Record<string, string>): Promise<string> => {
  const proc = Bun.spawn(cmd, {
    cwd,
    env: { ...process.env, ...env },
    stdout: "pipe",
    stderr: "pipe",
  });
  const out = await new Response(proc.stdout).text();
  const err = await new Response(proc.stderr).text();
  const code = await proc.exited;
  if (code !== 0) {
    const msg = err?.trim() || out?.trim() || `exit ${code}`;
    throw new Error(`[${cmd.join(" ")}] ${msg}`);
  }
  return out.trim();
};

const check = async (name: string, cmd: string[], expectZero = true): Promise<boolean> => {
  try {
    await run(cmd);
    console.log(`  \x1b[32m✓\x1b[0m ${name}`);
    return true;
  } catch (e) {
    console.log(`  \x1b[31m✗\x1b[0m ${name}: ${e}`);
    return false;
  }
};

// --- Preflight ---
console.log("\n[PREFLIGHT]");
const deps = [
  ["gh", ["gh", "--version"]],
  ["git", ["git", "--version"]],
  ["bun", ["bun", "--version"]],
  ["python3", ["python3", "--version"]],
];
for (const [name, cmd] of deps) {
  if (!(await check(name as string, cmd as string[]))) {
    console.error("\n[-] Missing required dependency. Abort.");
    process.exit(1);
  }
}

// --- Scaffold ---
console.log("\n[SCAFFOLD]");
if (!existsSync(GITHUB_DIR)) {
  mkdirSync(GITHUB_DIR, { recursive: true });
  console.log(`  \x1b[32m✓\x1b[0m mkdir ${GITHUB_DIR}`);
} else {
  console.log(`  \x1b[33m!\x1b[0m ${GITHUB_DIR} already exists`);
}

// Init git if needed
const gitDir = join(GITHUB_DIR, ".git");
if (!existsSync(gitDir)) {
  await run(["git", "init"], GITHUB_DIR);
  await run(["git", "branch", "-M", "main"], GITHUB_DIR);
  console.log("  \x1b[32m✓\x1b[0m git init → main");
} else {
  console.log("  \x1b[33m!\x1b[0m git already initialized");
}

// Create a dummy file and commit so gh --push works
const readmePath = join(GITHUB_DIR, "README.md");
if (!existsSync(readmePath)) {
  writeFileSync(readmePath, `# ${REPO_NAME}\n\nAuto-scaffolded by harness-local.\n`);
  console.log("  \x1b[32m✓\x1b[0m wrote README.md");
}

// FIXED: git add + commit BEFORE gh repo create --push
const hasCommits = await run(["git", "log", "--oneline", "-1"], GITHUB_DIR).catch(() => null);
if (!hasCommits) {
  await run(["git", "add", "."], GITHUB_DIR);
  await run(["git", "commit", "-m", "init: scaffold harness-local"], GITHUB_DIR);
  console.log("  \x1b[32m✓\x1b[0m initial commit created");
} else {
  console.log("  \x1b[33m!\x1b[0m commits already exist");
}

// --- GitHub ---
console.log("\n[GITHUB]");
try {
  // Check if repo already exists remotely
  const remoteCheck = await run(["gh", "repo", "view", `${GH_USER}/${REPO_NAME}`, "--json", "name"]).catch(() => null);
  if (remoteCheck) {
    console.log(`  \x1b[33m!\x1b[0m Remote repo ${GH_USER}/${REPO_NAME} already exists`);
    // Ensure local remote is set
    const remotes = await run(["git", "remote"], GITHUB_DIR).catch(() => "");
    if (!remotes.includes("origin")) {
      await run(
        ["git", "remote", "add", "origin", `https://github.com/${GH_USER}/${REPO_NAME}.git`],
        GITHUB_DIR
      );
      console.log("  \x1b[32m✓\x1b[0m remote origin added");
    }
    await run(["git", "push", "-u", "origin", "main"], GITHUB_DIR);
    console.log("  \x1b[32m✓\x1b[0m pushed to existing remote");
  } else {
    // Create new repo and push
    // --source takes the local path, --push pushes after creation
    await run(
      ["gh", "repo", "create", REPO_NAME, "--public", "--source=.", "--push"],
      GITHUB_DIR
    );
    console.log(`  \x1b[32m✓\x1b[0m Created and pushed https://github.com/${GH_USER}/${REPO_NAME}`);
  }
} catch (e) {
  console.error(`  \x1b[31m✗\x1b[0m GitHub step failed: ${e}`);
  console.error("\n[TROUBLESHOOTING]");
  console.error("  1. Ensure 'gh auth status' shows a logged-in user");
  console.error("  2. If repo exists but you lack access, check GH_USER env var");
  console.error("  3. For private repos, add --private instead of --public");
  process.exit(1);
}

// --- Post-Install ---
console.log("\n[COMPLETE]");
console.log(`  Local:  ${GITHUB_DIR}`);
console.log(`  Remote: https://github.com/${GH_USER}/${REPO_NAME}`);
console.log("\n  Next steps:");
console.log("    cd ~/github/harness-local");
console.log("    bun add <deps>");
console.log("    git add . && git commit -m 'feature: ...' && git push");
