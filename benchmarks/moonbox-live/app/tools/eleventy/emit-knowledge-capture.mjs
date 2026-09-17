#!/usr/bin/env node
import { main } from "./emit.mjs";

await main(["--type", "knowledge-capture", ...process.argv.slice(2)]);
