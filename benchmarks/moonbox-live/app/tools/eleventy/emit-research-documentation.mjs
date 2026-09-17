#!/usr/bin/env node
import { main } from "./emit.mjs";

await main(["--type", "research-documentation", ...process.argv.slice(2)]);
