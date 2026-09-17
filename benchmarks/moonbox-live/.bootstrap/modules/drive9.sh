#!/bin/bash
# drive9.sh — Drive9 filesystem operations

DRIVE9="http://10.213.5.144"
DRIVE9_TOKEN="${DRIVE9_TOKEN:-}"

d9_api() {
    local path="$1"
    curl -s -m 10 -H "Authorization: Bearer $DRIVE9_TOKEN" \
      "$DRIVE9$path" 2>/dev/null
}

d9_list() {
    d9_api "/v1/fs/list?path=$1" | python3 -m json.tool 2>/dev/null | head -40
}

d9_projects() {
    d9_api "/v1/fs/projects" | python3 -m json.tool 2>/dev/null | head -40
}

d9_token_issue() {
    local ttl="${1:-99999h}"
    local scope="${2:-fs:read,write}"
    # Use envd-alt to issue token
    curl -s -m 10 -X POST http://127.0.0.1:18888/ \
      -H "Content-Type: application/json" \
      -d "{\"cmd\":\"/usr/local/bin/drive9 token issue --ttl $ttl --allow $scope 2>&1\"}" 2>/dev/null
}
