#!/usr/bin/env node
import { main } from "./emit.mjs";

await main(["--type", "spark", ...process.argv.slice(2)]);
