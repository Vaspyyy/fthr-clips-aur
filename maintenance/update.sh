#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
# This package intentionally tracks the official Linux alpha release channel.
exec python maintenance/update.py --allow-prerelease "$@"
