#!/usr/bin/env node
/*
 * HYPEBRUT stream guard filter
 * - Soft wrap at width (default 3500)
 * - Allowed control bytes: TAB(0x09), LF(0x0A), CR(0x0D), ESC(0x1B), BS(0x08), VT(0x0B), FF(0x0C)
 * - Backspace sanitation applied before windowing
 * - Unsafe control bytes debounced into one summary per window/time-slice
 * - Raw bytes mirrored to sidecar (per-process, per-channel)
 */

const fs = require('fs');
const path = require('path');

const args = (() => {
  const out = {
    chan: 'stdout',
    pid: process.env.HB_FILTER_PID || process.pid.toString(),
    logdir: process.env.HB_FILTER_LOGDIR || '.',
    width: process.env.HB_FILTER_W || '3500',
    flush: process.env.HB_FILTER_FLUSH || '',
  };
  for (let i = 2; i < process.argv.length; i++) {
    const a = process.argv[i];
    if (a === '--chan') out.chan = process.argv[++i];
    else if (a === '--pid') out.pid = process.argv[++i];
    else if (a === '--logdir') out.logdir = process.argv[++i];
    else if (a === '--width') out.width = process.argv[++i];
    else if (a === '--flush') out.flush = process.argv[++i];
  }
  out.w = Math.max(1, parseInt(out.width, 10) || 3500);
  out.flushThreshold = parseInt(out.flush, 10);
  if (!Number.isFinite(out.flushThreshold) || out.flushThreshold <= 0) {
    out.flushThreshold = out.w * 4; // ≈ 4•W
  }
  return out;
})();

const allow = new Set([0x09, 0x0a, 0x0d, 0x1b, 0x08, 0x0b, 0x0c]);
const BS = 0x08;
const NUL = 0x00,
  DEL = 0x7f;

const sidecarDir = path.resolve(args.logdir);
fs.mkdirSync(sidecarDir, { recursive: true });
const sidecarPath = path.join(sidecarDir, `${args.pid}.${args.chan}.log`);
const sidecar = fs.createWriteStream(sidecarPath, { flags: 'a' });

// Ensure we operate on raw buffers
process.stdin.on('error', () => {});
process.stdin.resume();
process.stdin.setEncoding(null);

const out = process.stdout;
out.on('error', () => {});

let lineBuf = []; // holds sanitized bytes for current logical line/window
let chunkIndex = 0;
let totalChunks = 0; // unknown in streaming; used for cosmetic format only
let suppressed = 0; // debounced counter
let emittedSinceFlush = 0;

function emitSuppressionIfAny() {
  if (suppressed > 0) {
    const msg = `[HBBIN suppressed ${suppressed} bytes]`;
    out.write(msg);
    emittedSinceFlush += msg.length;
    suppressed = 0;
  }
}

function flushWindow(force = false) {
  if (lineBuf.length === 0 && suppressed === 0) return;

  // Window output at configured width
  let i = 0;
  let start = 1; // 1-based positions for human readability
  while (i < lineBuf.length) {
    const end = Math.min(i + args.w, lineBuf.length);
    const piece = Buffer.from(lineBuf.slice(i, end));
    chunkIndex += 1;
    totalChunks += 1;
    const header = `[HBWRAP ${chunkIndex}/? ${start}..${end}] `;
    out.write(header);
    out.write(piece);
    emittedSinceFlush += header.length + piece.length;
    i = end;
    start = i + 1;
  }
  lineBuf = [];
  emitSuppressionIfAny();
  if (force) {
    chunkIndex = 0;
    totalChunks = 0;
    emittedSinceFlush = 0;
  }
}

function handleBytes(buf) {
  // Mirror raw to sidecar immediately
  sidecar.write(buf);

  for (let i = 0; i < buf.length; i++) {
    const b = buf[i];
    if (b === BS) {
      // sanitize backspace by removing previous printable if present; otherwise drop
      if (lineBuf.length > 0) {
        lineBuf.pop();
      }
      continue;
    }
    if (b <= 0x1f || b === DEL) {
      if (allow.has(b)) {
        if (b === 0x0a) {
          // LF ends logical line window
          flushWindow(true);
          out.write('\n');
          emittedSinceFlush += 1;
          continue;
        }
        // pass-through allowed control bytes into buffer as-is, except LF handled above
        lineBuf.push(b);
      } else {
        suppressed++;
      }
    } else {
      lineBuf.push(b);
    }

    // Debounce by flush threshold
    if (emittedSinceFlush >= args.flushThreshold) {
      flushWindow(true);
    }
  }
}

process.stdin.on('data', (buf) => handleBytes(buf));
process.stdin.on('end', () => {
  // Final flush
  flushWindow(true);
  sidecar.end();
});
