#!/usr/bin/env node
import { main } from "./emit.mjs";

await main(["--type", "spec-to-implementation", ...process.argv.slice(2)]);
