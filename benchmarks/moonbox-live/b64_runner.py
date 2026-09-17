#!/usr/bin/env python3 -uS
"""b64_runner — Execute base64-encoded Python without plaintext on disk."""
import base64, sys, os, ast, subprocess
from pathlib import Path

def run_b64(b64_path, script_args=None, validate=True, keep_temp=False):
    b64_path = Path(b64_path)
    if not b64_path.exists():
        print(f"[B64_RUNNER] FATAL: {b64_path} not found", file=sys.stderr)
        sys.exit(1)
    with open(b64_path) as f:
        b64_data = f.read().strip()
    decoded = base64.b64decode(b64_data)
    code = decoded.decode('utf-8')
    if validate:
        try:
            ast.parse(code)
        except SyntaxError as e:
            print(f"[B64_RUNNER] SYNTAX_ERR: {e}", file=sys.stderr)
            sys.exit(1)
    tmp_dir = os.environ.get('B64_TMP', '/dev/shm')
    tmp_path = Path(tmp_dir) / f"b64_{os.getpid()}_{b64_path.stem}.py"
    with open(tmp_path, 'w') as f:
        f.write(code)
    os.chmod(tmp_path, 0o700)
    cmd = [sys.executable, str(tmp_path)] + (script_args or [])
    rc = subprocess.call(cmd)
    if not keep_temp:
        tmp_path.unlink(missing_ok=True)
    sys.exit(rc)

def b64_encode_file(src_path, dst_path):
    with open(src_path, 'rb') as f:
        data = f.read()
    b64 = base64.b64encode(data).decode()
    with open(dst_path, 'w') as f:
        f.write(b64)
    print(f"[B64_RUNNER] Encoded {src_path} -> {dst_path}")

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='b64_runner')
    parser.add_argument('--encode', help='Encode plaintext file to base64')
    parser.add_argument('--output', '-o', help='Output path for --encode')
    parser.add_argument('--keep-temp', action='store_true')
    parser.add_argument('b64_file', nargs='?', help='Base64 file to execute')
    args, script_args = parser.parse_known_args()
    
    if args.encode:
        if not args.output:
            print("[B64_RUNNER] --encode requires --output", file=sys.stderr)
            sys.exit(1)
        b64_encode_file(args.encode, args.output)
        sys.exit(0)
    
    if not args.b64_file:
        parser.print_help()
        sys.exit(1)
    
    run_b64(args.b64_file, script_args, keep_temp=args.keep_temp)
