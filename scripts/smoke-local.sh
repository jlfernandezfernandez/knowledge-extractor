#!/usr/bin/env sh

set -eu

base_url="${KNOWLI_URL:-http://localhost:${KNOWLI_PORT:-3000}}"
cookie_jar="$(mktemp)"
response_body="$(mktemp)"
trap 'rm -f "$cookie_jar" "$response_body"' EXIT HUP INT TERM

request_status() {
  curl --silent --show-error --output "$response_body" --write-out '%{http_code}' "$@"
}

for _ in $(seq 1 60); do
  status="$(request_status "$base_url/api/health/ready" 2>/dev/null || true)"
  if [ "$status" = "200" ]; then
    break
  fi
  sleep 1
done

if [ "${status:-}" != "200" ]; then
  echo "Knowli did not become ready at $base_url/api/health/ready (last status: ${status:-connection failed})" >&2
  exit 1
fi

suffix="$(date +%s)-$$"
email="smoke-$suffix@example.test"
payload="$(jq -nc --arg email "$email" '{email: $email, password: "correct horse battery staple", display_name: "Smoke Test"}')"

status="$(request_status --cookie-jar "$cookie_jar" --request POST --header 'Content-Type: application/json' --data "$payload" "$base_url/api/auth/register")"
if [ "$status" != "201" ]; then
  echo "Registration returned HTTP $status" >&2
  exit 1
fi

if [ "$(jq -r '.user.email // empty' "$response_body")" != "$email" ]; then
  echo "Registration response did not contain the registered user" >&2
  exit 1
fi

status="$(request_status --cookie "$cookie_jar" "$base_url/api/auth/me")"
if [ "$status" != "200" ]; then
  echo "Current-user request returned HTTP $status" >&2
  exit 1
fi

if [ "$(jq -r '.user.email // empty' "$response_body")" != "$email" ]; then
  echo "Current-user response did not match the registered user" >&2
  exit 1
fi

status="$(request_status --cookie "$cookie_jar" --request POST "$base_url/api/auth/logout")"
if [ "$status" != "204" ]; then
  echo "Logout returned HTTP $status" >&2
  exit 1
fi

echo "Local smoke test passed: $base_url"
