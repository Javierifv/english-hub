import os
import json
import urllib.request

key = ""
with open(".env") as f:
    for line in f:
        if line.startswith("GEMINI_API_KEY="):
            key = line.strip().split("=")[1]

models = ["gemini-flash-latest", "gemini-2.5-flash", "gemini-3.5-flash", "gemini-3.5-flash-lite"]

for m in models:
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={key}"
        payload = {
            "contents": [{"parts": [{"text": "Say hello in JSON format with key message."}]}],
            "generationConfig": {"response_mime_type": "application/json"}
        }
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            print(f"[OK] {m} works! Response:", data["candidates"][0]["content"]["parts"][0]["text"].strip())
            break
    except Exception as e:
        print(f"[FAIL] {m}: {e}")
