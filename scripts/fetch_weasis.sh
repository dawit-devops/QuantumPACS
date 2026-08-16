#!/bin/bash
# Fetch and verify weasis-pacs-connector 8.0.0 for the dcm4chee arc image
# (docker/dcm4chee/Dockerfile.arc COPYs the vendored war).
#
# The war is gitignored (binary) — this script is the supply-chain gate:
# it downloads from the official dcm4che SourceForge release and refuses any
# artifact whose SHA-256 does not match the pinned value (ADR-028 R14).
set -euo pipefail

DIR="$(cd "$(dirname "$0")/.." && pwd)"
WAR="$DIR/docker/dcm4chee/weasis-pacs-connector.war"
VERSION="8.0.0"
SHA256="c00027108e08ea5eff56bc4395a91374cded46a384076e75d0a7b31b57823f44"
URL="https://sourceforge.net/projects/dcm4che/files/Weasis/weasis-pacs-connector/${VERSION}/weasis-pacs-connector.war/download"

if [ -f "$WAR" ]; then
    if [ "$(sha256sum "$WAR" | awk '{print $1}')" = "$SHA256" ]; then
        echo "weasis-pacs-connector ${VERSION} present and verified"
        exit 0
    fi
    echo "existing $WAR has wrong SHA-256 — refetching" >&2
fi

echo "downloading weasis-pacs-connector ${VERSION} from SourceForge..."
curl -fsSL --max-time 300 -o "$WAR" "$URL"
echo "verifying SHA-256..."
actual="$(sha256sum "$WAR" | awk '{print $1}')"
if [ "$actual" != "$SHA256" ]; then
    echo "SHA-256 mismatch: expected $SHA256, got $actual" >&2
    rm -f "$WAR"
    exit 1
fi
echo "verified: docker/dcm4chee/weasis-pacs-connector.war (${SHA256:0:16}...)"
