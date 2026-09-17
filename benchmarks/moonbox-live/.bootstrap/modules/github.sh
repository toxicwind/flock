#!/bin/bash
# github.sh — GitHub API operations

PAT="${GITHUB_PAT:-}"
API="https://api.github.com"

gh_api() {
    local method="$1"
    local path="$2"
    local data="${3:-}"
    local req_data=""
    [ -n "$data" ] && req_data="-d $data"
    curl -s -m 15 -X "$method" \
      -H "Authorization: token $PAT" \
      -H "Accept: application/vnd.github.v3+json" \
      -H "Content-Type: application/json" \
      $req_data \
      "$API$path" 2>/dev/null
}

gh_archive() {
    gh_api "PATCH" "/repos/toxicwind/$1" "{\"archived\":true}" > /dev/null
    echo "Archived $1"
}

gh_privatize() {
    gh_api "PATCH" "/repos/toxicwind/$1" "{\"private\":true}" > /dev/null
    echo "Privatized $1"
}

gh_disable_workflows() {
    local repo="$1"
    local wfs=$(gh_api "GET" "/repos/toxicwind/$repo/actions/workflows" | \
      python3 -c "import sys,json; [print(w[id]) for w in json.load(sys.stdin).get(workflows,[])]")
    for wf_id in $wfs; do
        gh_api "PUT" "/repos/toxicwind/$repo/actions/workflows/$wf_id/disable" > /dev/null
        echo "  Disabled workflow $wf_id"
    done
}

gh_repo_info() {
    gh_api "GET" "/repos/toxicwind/$1" | python3 -m json.tool 2>/dev/null | head -20
}
