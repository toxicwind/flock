#!/usr/bin/env node
import { main } from "./emit.mjs";

await main(["--type", "project", ...process.argv.slice(2)]);
