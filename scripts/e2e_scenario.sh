#!/usr/bin/env bash
# End-to-end run: three headless Claude Code sessions (frontend, backend, deploy) work
# in one scratch workspace through handoff, then scripts/e2e_check.py checks what the
# deploy session sees. Leaves the result in FalkorDB for the browser at localhost:3000.
#
#   scripts/e2e_scenario.sh                 # graph "demo", knowledge graph "demo_kg"
#   E2E_GRAPH=demo2 scripts/e2e_scenario.sh
#   scripts/e2e_scenario.sh --no-knowledge  # skip the knowledge-graph step
#
# Needs: make db-up, uv sync --extra knowledge, and a Claude Code login (no API key).
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
BIN="$REPO/.venv/bin"
WORKSPACE="${E2E_WORKSPACE:-${TMPDIR:-/tmp}/handoff-e2e}"
KNOWLEDGE=1
[[ "${1:-}" == "--no-knowledge" ]] && KNOWLEDGE=0

export HANDOFF_GRAPH="${E2E_GRAPH:-demo}"
export HANDOFF_HOME="${HANDOFF_HOME:-$REPO/.handoff}"
export HANDOFF_MODEL_NAME="${E2E_MODEL:-haiku}"  # stand-in and knowledge model
export HANDOFF_KNOWLEDGE=off                      # sessions skip it; one worker runs below
export HANDOFF_WAIT_SECONDS=3

TOOLS="mcp__handoff__handoff mcp__handoff__why mcp__handoff__sessions"
TOOLS+=" mcp__handoff__record_decision mcp__handoff__record_need mcp__handoff__resolve_need"
TOOLS+=" mcp__handoff__send_message mcp__handoff__ask mcp__handoff__search"

step() { printf '\n== %s\n' "$*"; }

run_role() {  # run_role <role> <prompt>
  local role="$1" prompt="$2"
  step "$role session"
  echo "> $prompt"
  (cd "$WORKSPACE" && HANDOFF_ROLE="$role" timeout 300 claude -p "$prompt" \
    --permission-mode acceptEdits --setting-sources local --strict-mcp-config \
    --mcp-config "$WORKSPACE/.mcp.json" --allowedTools $TOOLS \
    --no-session-persistence --model "$HANDOFF_MODEL_NAME" < /dev/null \
    | tee "$WORKSPACE/$role.reply.txt")
}

step "fresh workspace $WORKSPACE and graph $HANDOFF_GRAPH"
rm -rf "$WORKSPACE" && mkdir -p "$WORKSPACE"
"$BIN/python" "$REPO/scripts/e2e_check.py" --reset
"$BIN/handoff" install "$WORKSPACE" --no-falkordb-mcp --graph "$HANDOFF_GRAPH" > /dev/null

run_role frontend "Create Checkout.tsx that shows the order total from order.totalPaise \
as rupees with two decimals. Record a decision: money stays in integer paise end to end, \
because floating-point rupees round wrongly. Record a need for the backend: the orders API \
must return totalPaise as an integer. Reply done."

run_role backend "Use the handoff tool to see what the frontend needs from you. Create \
api/orders.py with a function order_summary(order) that returns a dict whose totalPaise is \
an integer. Record a decision about it, resolve the frontend's need, then send the frontend \
a message that totalPaise is now returned by order_summary. Reply done."

run_role frontend "Carry on: is there any news from the other sessions? Reply in one line."

run_role deploy "Before deploying: use the handoff tool, and use the ask tool to ask the \
frontend role why amounts are kept in paise. Then tell me in three lines what the other \
sessions changed, why, and whether anything is still open."

if [[ "$KNOWLEDGE" == 1 ]]; then
  step "knowledge graph ${HANDOFF_GRAPH}_kg (one model call per item, about 20 s each)"
  HANDOFF_KNOWLEDGE=on "$BIN/handoff-knowledge" --once
fi

step "check"
"$BIN/python" "$REPO/scripts/e2e_check.py" --workspace "$WORKSPACE"
