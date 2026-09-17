#!/usr/bin/env python3
"""
Bytecode Inspector v1.0 - AST-aware deobfuscator
Analyzes Python bytecode, extracts constants, strings, API endpoints
"""
import dis, marshal, types, sys, os, json, struct
from datetime import datetime, timezone

T = lambda: datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

def analyze_pyc(path):
    """Analyze a .pyc file for strings, constants, API endpoints"""
    with open(path, 'rb') as f:
        magic = f.read(4)
        if magic[:2] != b'\xcb\x0d':  # Python 3.12 magic
            f.seek(0)
        try:
            f.read(8)  # Skip header
            code = marshal.load(f)
        except Exception as e:
            return {'error': str(e)}
    
    results = {'strings': set(), 'urls': set(), 'api_paths': set(), 'constants': []}
    
    def walk_code(co):
        for const in co.co_consts:
            if isinstance(const, str):
                results['strings'].add(const)
                if const.startswith(('http://', 'https://', 'ws://', 'wss://')):
                    results['urls'].add(const)
                if const.startswith('/api/') or const.startswith('/v1/'):
                    results['api_paths'].add(const)
            elif isinstance(const, types.CodeType):
                walk_code(const)
    
    walk_code(code)
    results['strings'] = list(results['strings'])[:500]
    results['urls'] = list(results['urls'])
    results['api_paths'] = list(results['api_paths'])
    return results

def analyze_py(path):
    """Analyze .py source for imports, strings, API calls"""
    with open(path, 'r', errors='replace') as f:
        source = f.read()
    
    import re
    results = {
        'imports': re.findall(r'^(?:import|from)\s+([a-zA-Z0-9_.]+)', source, re.M),
        'urls': re.findall(r'["\'](https?://[^"\']+)["\']', source),
        'api_paths': re.findall(r'["\'](/api/[a-zA-Z0-9_/]+)["\']', source),
        'tokens': re.findall(r'["\'](eyJ[a-zA-Z0-9_-]*\.eyJ[a-zA-Z0-9_-]*\.[a-zA-Z0-9_-]*)["\']', source),
        'keys': re.findall(r'["\'](sk-[a-zA-Z0-9]{20,})["\']', source),
    }
    return results

def scan_directory(base):
    """Recursively scan for .py and .pyc files"""
    findings = {}
    for root, dirs, files in os.walk(base):
        for f in files:
            path = os.path.join(root, f)
            try:
                if f.endswith('.pyc'):
                    findings[path] = analyze_pyc(path)
                elif f.endswith('.py'):
                    findings[path] = analyze_py(path)
            except Exception as e:
                findings[path] = {'error': str(e)}
    return findings

if __name__ == '__main__':
    target = sys.argv[1] if len(sys.argv) > 1 else '/mnt/agents'
    print(f'{T()} SCANNING: {target}')
    results = scan_directory(target)
    
    # Aggregate
    all_urls = set()
    all_tokens = set()
    all_keys = set()
    all_api_paths = set()
    
    for path, data in results.items():
        if 'urls' in data:
            all_urls.update(data['urls'])
        if 'tokens' in data:
            all_tokens.update(data['tokens'])
        if 'keys' in data:
            all_keys.update(data['keys'])
        if 'api_paths' in data:
            all_api_paths.update(data['api_paths'])
    
    report = {
        'timestamp': T(),
        'target': target,
        'files_scanned': len(results),
        'urls': sorted(all_urls),
        'tokens': sorted(all_tokens),
        'api_keys': sorted(all_keys),
        'api_paths': sorted(all_api_paths),
    }
    
    out = f'/mnt/agents/dot/intel/bytecode_audit_{int(datetime.now(timezone.utc).timestamp())}.json'
    with open(out, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f'{T()} REPORT: {out}')
    print(f'URLs: {len(all_urls)}, Tokens: {len(all_tokens)}, Keys: {len(all_keys)}, API Paths: {len(all_api_paths)}')
