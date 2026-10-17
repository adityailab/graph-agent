#!/usr/bin/env bash
# The end-to-end proof now lives in the product: handoff demo (see handoff/demo/).
exec "$(cd "$(dirname "$0")/.." && pwd)/.venv/bin/handoff" demo "$@"
