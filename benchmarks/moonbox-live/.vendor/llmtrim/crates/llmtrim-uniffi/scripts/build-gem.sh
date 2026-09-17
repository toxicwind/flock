#!/usr/bin/env bash
# Build a platform-specific (precompiled) Ruby gem for llmtrim.
#
# It bundles the compiled llmtrim-core engine so installers need no Rust toolchain:
#   1. generate the UniFFI Ruby glue from an UNSTRIPPED build (bindgen needs the symbols);
#   2. build an optimized cdylib to ship;
#   3. patch the glue's `ffi_lib 'llmtrim_ffi'` to load the bundled library by absolute
#      path with the host's extension (.so/.dylib/.dll);
#   4. drop both into lib/llmtrim/ and `gem build` for the current platform.
#
# Usage: crates/llmtrim-uniffi/scripts/build-gem.sh
# Env:   LLMTRIM_VERSION (gem version, default 0.1.7.dev)
set -euo pipefail

pkg_dir="$(cd "$(dirname "$0")/../packaging/ruby" && pwd)"
workspace_root="$(cd "$(dirname "$0")/../../.." && pwd)"
lib_dir="$pkg_dir/lib/llmtrim"
cd "$workspace_root"

# Linux/macOS produce lib<name>.{so,dylib}; Windows produces <name>.dll (no `lib` prefix).
find_cdylib() {
    for cand in "$1/libllmtrim_ffi.so" "$1/libllmtrim_ffi.dylib" "$1/llmtrim_ffi.dll"; do
        [ -f "$cand" ] && { echo "$cand"; return; }
    done
}

# The gem's platform must describe the TARGET, not the build host. When cross-compiling
# (x86_64-apple-darwin on an arm64 macOS runner) `Gem::Platform.local` returns the host
# (arm64-darwin) and the gem collides with the native arm64 gem, so the Intel-mac gem never
# ships. Derive it from LLMTRIM_TARGET; the version-agnostic darwin form installs on any
# macOS version. Windows/linux host == target, so fall back to the local platform there.
gem_platform() {
    case "${LLMTRIM_TARGET:-}" in
        x86_64-*-linux-gnu)   echo "x86_64-linux" ;;
        aarch64-*-linux-gnu)  echo "aarch64-linux" ;;
        x86_64-apple-darwin)  echo "x86_64-darwin" ;;
        aarch64-apple-darwin) echo "arm64-darwin" ;;
        *)                    ruby -e 'puts Gem::Platform.local' ;;
    esac
}

echo "==> generating UniFFI Ruby glue (from the unstripped debug build)"
cargo build -p llmtrim-uniffi
dbg="$(find_cdylib target/debug)"
[ -n "$dbg" ] || { echo "error: no unstripped cdylib in target/debug/" >&2; exit 1; }
cargo run -q --bin uniffi-bindgen -p llmtrim-uniffi -- generate --library "$dbg" --language ruby --out-dir "$lib_dir"

echo "==> building the optimized cdylib to bundle"
cargo build --release -p llmtrim-uniffi ${LLMTRIM_TARGET:+--target "$LLMTRIM_TARGET"}
rel="$(find_cdylib "target/${LLMTRIM_TARGET:+$LLMTRIM_TARGET/}release")"
[ -n "$rel" ] || { echo "error: no release cdylib in target/release/" >&2; exit 1; }
base="$(basename "$rel")"
cp "$rel" "$lib_dir/$base"

echo "==> patching ffi_lib to load the bundled library ($base)"
# Point ffi_lib at the bundled file by its exact name (platform-specific: libllmtrim_ffi.so
# / .dylib on Unix, llmtrim_ffi.dll on Windows).
perl -i -pe "s{ffi_lib 'llmtrim_ffi'}{ffi_lib File.expand_path('$base', __dir__)}" \
    "$lib_dir/llmtrim_ffi.rb"

plat="$(gem_platform)"
echo "==> gem build (platform: $plat)"
cd "$pkg_dir"
LLMTRIM_GEM_PLATFORM="$plat" gem build llmtrim.gemspec
echo "==> built: $(ls -t "$pkg_dir"/*.gem | head -1)"
