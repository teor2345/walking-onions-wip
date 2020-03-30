#!/usr/bin/env bash

TOOL="$(dirname $0)/extract_cddl.py"
SPECDIR="$(dirname $0)/../specs"

set -e

for toplevel in ENDIVE SNIP BinaryDiff VoterCert RootDocument; do
    "${TOOL}" --check --toplevel "${toplevel}" "${SPECDIR}"/{02,AB}-*.md
done
for toplevel in VoteDocument; do
    "${TOOL}" --check --toplevel "${toplevel}" "${SPECDIR}"/{02,03,AB}-*.md
done
