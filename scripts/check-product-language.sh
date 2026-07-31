#!/usr/bin/env sh

# Product-facing runtime and current docs must not revive retired product terms.
# Historical migrations and tests are intentionally outside this boundary
# because they prove the cleanup itself.
set -eu

pattern='knowledge[-_ ]base|organisation|organization|\bteam\b|a2a|mcp|knowledge-extractor'

if matches="$(rg -n -i "$pattern" README.md \
  docs/architecture.md docs/concepts.md docs/learning-guide.md docs/local-models.md \
  backend/knowli frontend/src docker-compose.yml \
  --glob '!backend/knowli/infrastructure/postgres/migrations/**')"; then
  printf '%s\n' 'Retired product language found:' >&2
  printf '%s\n' "$matches" >&2
  exit 1
fi

# The only deliberate protocol reference is this explicit decision record.
if [ "$(rg -c --no-filename -i "$pattern" docs/decisions.md || true)" != "1" ] || \
  ! rg -q -i '^\*\*MCP and A2A are deferred\.\*\*' docs/decisions.md; then
  printf '%s\n' 'The deferred-protocol decision is missing or has changed.' >&2
  exit 1
fi
