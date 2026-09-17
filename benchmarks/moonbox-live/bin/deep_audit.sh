#!/bin/bash
# Deep audit script - runs in background, detached
set -e
OUT="/mnt/agents/output/_audit_inventory.csv"
echo "path,repo,filename,size_bytes,mtime,ftype,is_contaminated,is_ipynb,is_lfs,is_kimi" > "$OUT"

cd /mnt/agents/output
find . -type f -not -path './.git/*' -not -path '*/node_modules/*' -not -path '*/.next/*' -not -path '*/__pycache__/*' -not -path '*/.venv/*' 2>/dev/null | while read f; do
    f="${f#./}"
    repo="$(echo "$f" | cut -d'/' -f1)"
    filename="$(basename "$f")"
    size="$(stat -c%s "$f" 2>/dev/null || echo 0)"
    mtime="$(stat -c%Y "$f" 2>/dev/null || echo 0)"
    ext="${filename##*.}"
    ext_lower="$(echo "$ext" | tr '[:upper:]' '[:lower:]')"
    
    ftype="other"
    case "$ext_lower" in
        py) ftype="python";;
        js) ftype="javascript";;
        ts) ftype="typescript";;
        json) ftype="json";;
        md) ftype="markdown";;
        html) ftype="html";;
        css) ftype="css";;
        ipynb) ftype="jupyter";;
        sh) ftype="shell";;
        txt) ftype="text";;
        yml|yaml) ftype="yaml";;
        toml) ftype="toml";;
        lock) ftype="lock";;
        tgz|gz|zip) ftype="archive";;
        parquet) ftype="parquet";;
        git) ftype="git";;
    esac
    
    is_contaminated=0
    case "$f" in
        *cannabis*|*emergent_api*|*lv-*|*/lv/*|*dayz*|*vector_ops*) is_contaminated=1;;
    esac
    
    is_ipynb=0
    [ "$ext_lower" = "ipynb" ] && is_ipynb=1
    
    is_lfs=0
    case "$f" in
        *.bundle.tgz|*lfs*) is_lfs=1;;
    esac
    
    is_kimi=0
    case "$f" in
        *kimi*|*Kimi*) is_kimi=1;;
    esac
    
    echo "\"$f\",\"$repo\",\"$filename\",$size,$mtime,\"$ftype\",$is_contaminated,$is_ipynb,$is_lfs,$is_kimi" >> "$OUT"
done
echo "AUDIT_COMPLETE" >> "$OUT"
