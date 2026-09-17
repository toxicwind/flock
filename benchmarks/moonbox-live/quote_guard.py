#!/usr/bin/env python3
"""quote_guard.py — Prevent nested quote SyntaxErrors forever."""
import sys, os, re

def fix_line(line):
    """Fix nested quotes in a single line."""
    if 'f"' in line or '"' in line:
        count = 0
        i = 0
        while i < len(line):
            if line[i] == '"' and (i == 0 or line[i-1] != '\\'):
                count += 1
            i += 1

        if count > 2:
            idx = line.find('f"')
            if idx != -1:
                last = line.rfind('"')
                if last > idx + 1:
                    return line[:idx] + "f'" + line[idx+2:last] + "'" + line[last+1:]
            else:
                idx = line.find('"')
                if idx != -1:
                    last = line.rfind('"')
                    if last > idx:
                        return line[:idx] + "'" + line[idx+1:last] + "'" + line[last+1:]
    return line

def sanitize_file(filepath):
    """Auto-fix all nested quote issues in a Python file."""
    with open(filepath, 'r') as f:
        lines = f.readlines()

    fixed = []
    changed = False
    for line in lines:
        new_line = fix_line(line)
        if new_line != line:
            changed = True
        fixed.append(new_line)

    if changed:
        with open(filepath, 'w') as f:
            f.writelines(fixed)
        print(f"[SANITIZED] {filepath}")

    # Verify compilation
    try:
        compile(''.join(fixed), filepath, 'exec')
        return True
    except SyntaxError as e:
        print(f"[ERR] {filepath}: {e}")
        return False

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 quote_guard.py <file.py> [file2.py ...]")
        sys.exit(1)

    for filepath in sys.argv[1:]:
        if os.path.exists(filepath):
            sanitize_file(filepath)
        else:
            print(f"[SKIP] {filepath}: not found")

if __name__ == "__main__":
    main()
