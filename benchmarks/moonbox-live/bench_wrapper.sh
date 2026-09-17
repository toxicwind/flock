#!/bin/sh
# Benchmark wrapper - prefix any command with timing
: ${GITHUB_PAT:?"GITHUB_PAT must be exported"}
export PYTHONPATH="/mnt/agents/output/.pip:$PYTHONPATH"
t0=$(date +%s%N)
"$@"
rc=$?
t1=$(date +%s%N)
echo "§BENCH§ $(( (t1 - t0) / 1000000 ))ms rc=$rc"
exit $rc
