#!/usr/bin/env python3
"""autofix_linter.py — Auto-fix Python syntax errors before execution.
Usage: python3 /mnt/agents/output/autofix_linter.py <file.py> [--in-place]
"""
import ast, re, sys, argparse, shutil

class AutoFixLinter:
    def __init__(self, src):
        self.src = src
        self.lines = src.split("\n")
        self.fixes = []

    def fix_escape_sequences(self):
        new_lines = []
        for i, line in enumerate(self.lines):
            old = line
            # Fix backslash-dollar in strings (shell var refs)
            line = line.replace(r"\$", "$")
            # Fix double-backslash-n -> single backslash-n in strings
            line = line.replace(r"\\n", r"\n")
            line = line.replace(r"\\t", r"\t")
            line = line.replace(r"\\r", r"\r")
            # Fix triple-backslash in JSON strings
            line = line.replace(r"\\\"", r"\"")
            if old != line:
                self.fixes.append(f"Line {i+1}: fixed escapes")
            new_lines.append(line)
        self.lines = new_lines

    def lint(self):
        self.fix_escape_sequences()
        fixed_src = "\n".join(self.lines)
        try:
            ast.parse(fixed_src)
            valid = True
        except SyntaxError as e:
            valid = False
            self.fixes.append(f"STILL BROKEN: {e}")
        return fixed_src, valid

def main():
    p = argparse.ArgumentParser()
    p.add_argument("file")
    p.add_argument("--in-place", "-i", action="store_true")
    args = p.parse_args()

    with open(args.file) as f:
        src = f.read()

    linter = AutoFixLinter(src)
    fixed, valid = linter.lint()

    for fix in linter.fixes:
        print(f"[FIX] {fix}")

    if valid:
        print(f"[OK] {args.file} is valid ({len(linter.fixes)} fixes)")
        if args.in_place:
            shutil.copy(args.file, args.file + ".bak")
            with open(args.file, "w") as f:
                f.write(fixed)
            print(f"[SAVED] {args.file}")
        return 0
    else:
        print(f"[FAIL] {args.file} still broken")
        return 1

if __name__ == "__main__":
    sys.exit(main())
