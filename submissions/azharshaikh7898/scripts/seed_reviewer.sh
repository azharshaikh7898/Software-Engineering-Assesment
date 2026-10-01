#!/usr/bin/env bash
# Creates the reviewer account (or logs in if it exists) and uploads the sample documents.
# Usage: BASE=https://your.domain REVIEWER_USER=reviewer REVIEWER_PASS='...' ./scripts/seed_reviewer.sh
set -euo pipefail
: "${BASE:?set BASE}" "${REVIEWER_USER:?set REVIEWER_USER}" "${REVIEWER_PASS:?set REVIEWER_PASS}"
JSON='Content-Type: application/json'
BODY=$(jq -n --arg u "$REVIEWER_USER" --arg p "$REVIEWER_PASS" '{username:$u,password:$p}')
TOKEN=$(curl -sS -X POST "$BASE/auth/signup" -H "$JSON" -d "$BODY" | jq -r '.access_token // empty')
if [ -z "$TOKEN" ]; then
  TOKEN=$(curl -fsS -X POST "$BASE/auth/login" -H "$JSON" -d "$BODY" | jq -r .access_token)
fi
AUTH="Authorization: Bearer $TOKEN"
EXISTING=$(curl -fsS "$BASE/documents" -H "$AUTH" | jq -r '.[].filename')
for f in eval/docs/*.md; do
  name=$(basename "$f")
  if grep -qx "$name" <<<"$EXISTING"; then echo "skip $name (already uploaded)"; continue; fi
  curl -fsS -X POST "$BASE/documents" -H "$AUTH" -F "file=@$f" | jq -c '{filename,status}'
done
for _ in $(seq 1 60); do
  PENDING=$(curl -fsS "$BASE/documents" -H "$AUTH" | jq '[.[] | select(.status=="queued" or .status=="processing")] | length')
  [ "$PENDING" = 0 ] && break
  sleep 2
done
curl -fsS "$BASE/documents" -H "$AUTH" | jq -c '.[] | {filename,status,error}'
