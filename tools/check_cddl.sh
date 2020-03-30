#!/usr/bin/env bash

TOOL="$(dirname $0)/extract_cddl.py"

for toplevel in ENDIVE SNIP VoteDocument BinaryDiff VoterCert RootDocument; do
    "${TOOL}" --check --toplevel "${TOPLEVEL}" specs/*.md 
done
