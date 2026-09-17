#!/usr/bin/env node
import { main } from "./emit.mjs";

await main(["--type", "meeting-intelligence", ...process.argv.slice(2)]);
