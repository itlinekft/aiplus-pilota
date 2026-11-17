#!/usr/bin/env bash
# Point git at this repository's hooks (scripts/hooks/), so every commit runs the real-data and profile checks.
set -eu
root="$(git rev-parse --show-toplevel)"
git -C "$root" config core.hooksPath scripts/hooks
echo "install-hooks: core.hooksPath = scripts/hooks"
