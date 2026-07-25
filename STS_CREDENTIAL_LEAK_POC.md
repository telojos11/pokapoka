# PoC: Cloud STS Credential Exposure via SoundOn Web API

## Finding: GET /api/upload/vcloud/ststoken

### Severity: MEDIUM (P2/P3)
**Category**: Cloud Credential Exposure

---

## EXECUTIVE SUMMARY

SoundOn's `/api/upload/vcloud/ststoken` endpoint returns temporary cloud Security Token Service (STS) credentials to **any authenticated user**. These credentials grant upload access to ByteDance's cloud media infrastructure (ImageX + VOD) for 1 hour, refreshable indefinitely.

**Video walkthrough**: Run `python3 decode_sts_policy.py` for live demonstration.

---

## REPRODUCTION

### Step 1: Request Cloud Credentials

```
GET /api/upload/vcloud/ststoken HTTP/2
Host: www.soundon.global
Cookie: sessionid=<VALID_SESSION>; passport_csrf_token=<VALID_CSRF>
```

### Step 2: Response Contains Full STS Credentials

```json
{
  "token": {
    "AccessKeyId": "AKTP...[REDACTED]",
    "SecretAccessKey": "[REDACTED]",
    "SessionToken": "STS2eyJ...[REDACTED]",
    "ExpiredTime": "2026-07-25T10:XX:XXZ",
    "CurrentTime": "2026-07-25T09:XX:XXZ"
  },
  "baseResp": {"errorCode": 0}
}
```

The `SessionToken` is a base64-encoded JWT-like token containing a full IAM policy.

### Step 3: Decode the IAM Policy

Decoding the SessionToken reveals:

```
Effect: Allow
Actions:
  - ImageX:ApplyImageUpload       ← Request image upload session
  - ImageX:CommitImageUpload      ← Finalize image upload
  - ImageX:ApplyUploadImageFile   ← Request image file upload
  - ImageX:CommitUploadImageFile  ← Finalize image file upload
  - vod:ApplyUpload               ← Request video upload session
  - vod:CommitUpload              ← Finalize video upload
  - vod:ApplyUploadInner          ← Internal video upload
  - vod:CommitUploadInner         ← Finalize internal video upload
  - vod:GetUploadCandidates       ← List available upload slots
  - vod:UploadVideoByUrl          ← Upload video from arbitrary URL

Resources: *  (ALL resources)
Condition: PSM = ies.musician.avenue_api
```

---

## EVIDENCE

### 1. Real-time Credential Retrieval

Run: `python3 decode_sts_policy.py`

This script:
- Requests credentials from the live endpoint
- Decodes the full IAM policy
- Displays all permitted actions
- Saves credentials to `/tmp/soundon_sts_creds.json`

### 2. Credential Refreshability (No Rate Limit)

Each call returns a NEW set of credentials. Tested 5 sequential calls — all succeeded with unique keys. No rate limiting.

### 3. No Special Permissions Required

Works with a basic account: 0 albums, 0 songs, 0 revenue, no special roles.

### 4. GitHub Secret Scanning Detection

When the PoC document was pushed to GitHub with example AccessKeyId values (temporary, already expired), **GitHub Push Protection automatically detected them as "VolcEngine Access Key ID" secrets** and blocked the push. This confirms the credentials match known cloud credential patterns.

---

## IMPACT ANALYSIS

### What These Credentials Grant

| Service | Actions | Attack Scenario |
|---|---|---|
| ImageX | ApplyImageUpload, CommitImageUpload | Upload arbitrary images to TikTok's CDN (`*.tiktokcdn.com`, `*.ibytedtos.com`) |
| ImageX | ApplyUploadImageFile, CommitUploadImageFile | Direct file upload bypassing size/format restrictions |
| VOD | ApplyUpload, CommitUpload | Upload arbitrary videos to TikTok's CDN |
| VOD | ApplyUploadInner, CommitUploadInner | Internal upload path (potentially less restricted) |
| VOD | GetUploadCandidates | Enumerate upload infrastructure endpoints |
| VOD | UploadVideoByUrl | Server-side fetch from arbitrary URL → **SSRF vector** |

### Attack Scenarios

**Scenario 1 — Malicious Content on TikTok CDN**
Upload phishing pages, malware, or CSRF payloads hosted on `*.tiktokcdn.com`. TikTok's domain reputation helps bypass URL filters and security scanners.

**Scenario 2 — SSRF via UploadVideoByUrl**
The `vod:UploadVideoByUrl` action makes a server-side request. If it can reach internal ByteDance services (metadata endpoints, internal APIs), this becomes an SSRF vector.

**Scenario 3 — Resource Abuse**
Upload terabytes through SoundOn's quota. No rate limiting on credential endpoint means infinite refreshable upload capacity. Direct financial cost to ByteDance.

**Scenario 4 — Content Poisoning**
Malicious content appears as legitimate SoundOn album art/videos in TikTok's pipeline. Could bypass moderation and/or poison AI training data.

---

## REMEDIATION

1. Generate upload URLs server-side — never expose STS credentials to the frontend
2. Add per-user rate limiting on the STS endpoint
3. Narrow policy resources from `*` to user-specific buckets
4. Reduce token lifetime from 1 hour to 10 minutes
5. Add request signing so only the backend can generate tokens

---

## TOOLS

| File | Purpose |
|---|---|
| `decode_sts_policy.py` | Live credential retrieval + policy decode + impact analysis |
