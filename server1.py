from flask import Flask, request, jsonify
from flask_cors import CORS
import requests, subprocess, json, os

app = Flask(__name__)
CORS(app)

DATA_DIR = "dayle_data"
PROFILE = os.path.join(DATA_DIR, "profile.json")
FEEDBACK = os.path.join(DATA_DIR, "feedback.jsonl")
os.makedirs(DATA_DIR, exist_ok=True)

DEFAULT_PROFILE = {
    "style_rules": "Short, blunt, no waffle. Acknowledge once, boundary second, closure last. Max 200 chars.",
    "preferred_phrases": ["Sweet, let’s keep it chill.", "I’m not chasing that argument.", "I’m here for respect."],
    "banned_words": []
}

def _detect_model(default="llama2-uncensored:7b"):
    try:
        out = subprocess.check_output(["ollama", "list"], text=True)
        for line in out.splitlines():
            if ":" in line:
                return line.split()[0].strip()
    except Exception:
        pass
    return default

MODEL_NAME = _detect_model("llama2-uncensored:7b")
OLLAMA_URL = "http://127.0.0.1:11434/api/generate"

def load_profile():
    if not os.path.exists(PROFILE):
        with open(PROFILE, "w") as f: json.dump(DEFAULT_PROFILE, f, indent=2)
        return dict(DEFAULT_PROFILE)
    return json.load(open(PROFILE))

def save_profile(p): json.dump(p, open(PROFILE, "w"), indent=2)

@app.post("/reply")
def reply():
    body = request.get_json(force=True) or {}
    incoming = body.get("incoming","").strip()
    contact  = body.get("contact","Unknown")
    if not incoming:
        return jsonify({"error":"missing 'incoming'"}), 400

    prof = load_profile()
    banned = ", ".join(prof.get("banned_words", [])) or "none"
    preferred = "; ".join(prof.get("preferred_phrases", [])) or "none"

    prompt = f"""You write as Dayle.
Style: {prof.get('style_rules')}
Banned words: {banned}
Preferred phrases: {preferred}

Incoming from {contact}:
\"\"\"{incoming}\"\"\"

Write ONE reply only, max 200 characters. If a simple 'ok' works, use it."""
    r = requests.post(OLLAMA_URL, json={"model": MODEL_NAME, "prompt": prompt, "stream": False}, timeout=60)
    r.raise_for_status()
    draft = r.json().get("response","").strip()
    return jsonify({"draft": draft})

@app.post("/feedback")
def feedback():
    data = request.get_json(force=True) or {}
    with open(FEEDBACK, "a", encoding="utf-8") as f:
        f.write(json.dumps(data, ensure_ascii=False) + "\n")

    # lightweight learning: add short phrases from accepted+edited finals
    final = (data.get("final") or "").strip()
    accepted = bool(data.get("accepted")); edited = bool(data.get("edited"))
    if final and accepted:
        prof = load_profile()
        for chunk in [c.strip() for c in final.split(".") if 6 <= len(c.strip()) <= 60]:
            if chunk not in prof["preferred_phrases"]:
                prof["preferred_phrases"].append(chunk)
        save_profile(prof)
    return jsonify({"ok": True})

@app.get("/profile")
def get_profile(): return jsonify(load_profile())

@app.post("/profile")
def set_profile():
    p = load_profile(); body = request.get_json(force=True) or {}
    for k in ["style_rules","preferred_phrases","banned_words"]:
        if k in body: p[k] = body[k]
    save_profile(p)
    return jsonify({"ok": True})

if __name__ == "__main__":
    print(f"[*] SMS AI server on :8081 using model {MODEL_NAME}")
    app.run(host="0.0.0.0", port=8081)
