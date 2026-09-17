#!/usr/bin/env node
import { main } from "./emit.mjs";

await main(["--type", "concept", ...process.argv.slice(2)]);
