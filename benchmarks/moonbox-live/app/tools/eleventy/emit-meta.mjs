#!/usr/bin/env node
import { main } from "./emit.mjs";

await main(["--type", "meta", ...process.argv.slice(2)]);
