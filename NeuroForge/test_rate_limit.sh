#!/bin/bash
echo "Testing rate limiting (max 5 requests/minute)"
for i in {1..7}; do
  HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:8000/api/v1/auth/login/json \
    -H "Content-Type: application/json" \
    -d '{"username": "test", "password": "pass"}')
  echo "Request $i: HTTP $HTTP_CODE"
  if [ "$HTTP_CODE" == "429" ]; then
    echo "✅ Rate limit working - request blocked"
  fi
done
