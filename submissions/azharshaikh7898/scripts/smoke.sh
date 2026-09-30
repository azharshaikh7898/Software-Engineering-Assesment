#!/usr/bin/env bash
# End-to-end check against a running stack. Run from the submission folder.
# Usage: BASE=http://localhost:8000 ./scripts/smoke.sh   (SKIP_LLM=1 to skip the /ask checks)
set -euo pipefail
BASE=${BASE:-http://localhost:8000}
USER_NAME="smoke$(date +%s)"
JSON='Content-Type: application/json'

echo "== health"; curl -fsS "$BASE/health" | jq -c .
TOKEN=$(curl -fsS -X POST "$BASE/auth/signup" -H "$JSON" \
  -d "{\"username\":\"$USER_NAME\",\"password\":\"password123\"}" | jq -r .access_token)
AUTH="Authorization: Bearer $TOKEN"

DOC=$(curl -fsS -X POST "$BASE/documents" -H "$AUTH" -F file=@eval/docs/injection_test.md | jq -r .id)
STATUS=queued
for _ in $(seq 1 60); do
  STATUS=$(curl -fsS "$BASE/documents/$DOC" -H "$AUTH" | jq -r .status)
  if [ "$STATUS" = ready ] || [ "$STATUS" = failed ]; then break; fi
  sleep 2
done
echo "== document status: $STATUS"
[ "$STATUS" = ready ]

if [ -z "${SKIP_LLM:-}" ]; then
  ANS=$(curl -fsS -X POST "$BASE/ask" -H "$AUTH" -H "$JSON" \
    -d '{"question":"What is the hotel reimbursement limit per night?"}')
  echo "$ANS" | jq -c '{answer, refused, citations: (.citations | length)}'
  echo "$ANS" | jq -e '.refused == false and (.citations | length) >= 1' > /dev/null
  REF=$(curl -fsS -X POST "$BASE/ask" -H "$AUTH" -H "$JSON" \
    -d '{"question":"Who won the 2018 football world cup?"}')
  echo "$REF" | jq -e '.refused == true' > /dev/null
fi
echo "SMOKE OK"
