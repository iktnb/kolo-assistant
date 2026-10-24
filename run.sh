#!/bin/sh
set -eu
PROJECT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec /home/iknow/.local/bin/uv run --no-sync --project "$PROJECT_DIR" kolo "$@"
