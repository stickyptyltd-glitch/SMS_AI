import os
import json
import re
import ipaddress
from flask import Flask, request, jsonify
from flask import Response
import requests
from ai.analysis import analyze as analyze_message
from ai.generator import build_reply_prompt, postprocess_reply
from ai.summary import summarize_memory
from ai.conversation_context import get_context_manager, ConversationTurn
from ai.multi_model_manager import get_multi_model_manager, ModelCapability
from ai.adaptive_learning import get_adaptive_learning_system
from analytics.system_monitor import get_system_monitor
from utils.error_handling import (
    get_error_handler, handle_exceptions, validate_json_input,
    InputValidator, ValidationError, APIError, ErrorCategory, ErrorSeverity
)
from security.advanced_security import get_security_monitor, require_security_check
from integrations.webhook_manager import get_webhook_manager, IntegrationType, MessagePlatform
from performance.cache_manager import get_cache_manager, cache_result
from typing import List, Dict, Any
from functools import wraps
import random
import time
import asyncio
from user_management import get_user_manager, require_permission, require_user_auth
try:
    from licensing.license_manager import get_license_manager, LicenseError
except Exception:  # pragma: no cover - optional dependency in dev
    get_license_manager = None
    class LicenseError(Exception):
        pass

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    # Avoid loading .env during pytest runs to keep tests isolated
    import sys as _sys
    if 'pytest' not in _sys.modules:
        load_dotenv()
except ImportError:
    pass  # dotenv not installed, skip

# --- Config ---
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434/api/generate")
MODEL_NAME = os.environ.get("OLLAMA_MODEL", "llama2-uncensored:7b")
DISABLE_LLM = os.environ.get("OLLAMA_DISABLE", "0") in ("1", "true", "yes")
# OpenAI Configuration
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
USE_OPENAI = os.environ.get("USE_OPENAI", "0") in ("1", "true", "yes")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-3.5-turbo")
DATA_DIR = "synapseflow_data"
PROFILE_FILE = os.path.join(DATA_DIR, "profile.json")
FEEDBACK_FILE = os.path.join(DATA_DIR, "feedback.jsonl")
POLICY_FILE = os.path.join(DATA_DIR, "policy.json")
TEMPLATES_FILE = os.path.join(DATA_DIR, "templates.json")

app = Flask(__name__)
os.makedirs(DATA_DIR, exist_ok=True)

# Optional integration with local Admin GUI allowlist
ADMIN_ENFORCE_USERS = os.environ.get("ADMIN_ENFORCE_USERS", "0") in ("1", "true", "yes")
try:
    # Lazy import; admin GUI is optional
    from admin.manager import list_users as _admin_list_users
except Exception:  # pragma: no cover - optional component
    _admin_list_users = None

def _is_contact_allowed(contact: str) -> bool:
    """If ADMIN_ENFORCE_USERS=1, only allow contacts present and active in admin GUI."""
    if not ADMIN_ENFORCE_USERS:
        return True
    if not _admin_list_users:
        return True  # No admin module available; do not block
    try:
        users = _admin_list_users()
        # If enforcement is on and list is empty, deny by default
        if not users:
            return False
        key = (contact or "").strip()
        for u in users:
            if getattr(u, "username", None) == key and bool(getattr(u, "active", True)):
                return True
        return False
    except Exception:
        # Fail-open unless enforcement is explicitly strict; default open
        return False

def require_allowlisted_contact(fn):
    @wraps(fn)
    def _wrapped(*args, **kwargs):
        if not ADMIN_ENFORCE_USERS:
            return fn(*args, **kwargs)
        contact = None
        if request.is_json and isinstance(request.json, dict):
            contact = request.json.get("contact")
        if not contact:
            contact = request.args.get("contact")
        if not _is_contact_allowed(contact or ""):
            return jsonify({"error": "forbidden", "message": "Contact not allowed"}), 403
        return fn(*args, **kwargs)
    return _wrapped

DEFAULT_PROFILE = {
    "style_rules": "Short, blunt, no waffle. Acknowledge once, boundary second, closure last. Max 200 chars. No emojis unless seen first.",
    "preferred_phrases": ["Sweet, let’s keep it chill.", "I’m not chasing that argument.", "I’m here for respect."],
    "banned_words": [],
    "max_reply_len": 200
}

# --- Helpers ---
def load_profile():
    if not os.path.exists(PROFILE_FILE):
        with open(PROFILE_FILE, "w") as f:
            json.dump(DEFAULT_PROFILE, f, indent=2)
        return dict(DEFAULT_PROFILE)
    with open(PROFILE_FILE, "r") as f:
        return json.load(f)

def save_profile(profile):
    with open(PROFILE_FILE, "w") as f:
        json.dump(profile, f, indent=2)


# --- Licensing ---
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "").strip()


def _ensure_license(feature: str | None = None):
    # Read enforcement dynamically to reflect env changes in tests/ops
    if os.environ.get("LICENSE_ENFORCE", "0") not in ("1", "true", "yes") or not get_license_manager:
        return
    lm = get_license_manager()
    ok, info = lm.validate_license()
    if not ok:
        raise LicenseError(info.get("error", "License invalid"))
    if feature and not lm.check_feature(feature):
        raise LicenseError(f"Feature '{feature}' not licensed")


def require_admin(fn):
    @wraps(fn)
    def _wrapped(*args, **kwargs):
        token_env = os.environ.get("ADMIN_TOKEN", "").strip()
        if token_env:
            tok = request.headers.get("X-Admin-Token") or request.args.get("token")
            if not tok or tok != token_env:
                return Response("Unauthorized: missing or invalid admin token", status=401, mimetype="text/plain; charset=utf-8")
        return fn(*args, **kwargs)
    return _wrapped


# --- Simple rate limiting (per-IP, per-route) ---
_RL_BUCKETS: Dict[str, Dict[str, float]] = {}
_RL_TOTAL: Dict[str, int] = {}


def rate_limit(fn):
    @wraps(fn)
    def _wrapped(*args, **kwargs):
        try:
            cap = int(os.environ.get("RATE_LIMIT_PER_MIN", "120"))
            if cap > 0:
                ip = request.headers.get('X-Forwarded-For', request.remote_addr) or 'unknown'
                key = f"{ip}:{request.path}"
                now = time.time()
                bucket = _RL_BUCKETS.get(key, {"win": now, "cnt": 0})
                # reset window every 60s
                if now - bucket["win"] >= 60:
                    bucket = {"win": now, "cnt": 0}
                bucket["cnt"] += 1
                _RL_BUCKETS[key] = bucket
                if bucket["cnt"] > cap:
                    route = request.path
                    _RL_TOTAL[route] = _RL_TOTAL.get(route, 0) + 1
                    retry_after = max(1, int(60 - (now - bucket["win"])))
                    headers = {
                        "Retry-After": str(retry_after),
                        "X-RateLimit-Limit": str(cap),
                        "X-RateLimit-Remaining": "0",
                    }
                    return Response("Too Many Requests", status=429, headers=headers, mimetype="text/plain; charset=utf-8")
        except Exception:
            pass
        return fn(*args, **kwargs)
    return _wrapped


# --- Metrics (lightweight) ---
START_TIME = time.time()
REQ_TOTAL = {"/reply": 0, "/assist": 0}
ERR_TOTAL = {"/reply": 0, "/assist": 0}
REPLY_LAT_SUM = 0.0
REPLY_LAT_COUNT = 0


def _observe_reply_latency(seconds: float):
    global REPLY_LAT_SUM, REPLY_LAT_COUNT
    REPLY_LAT_SUM += float(seconds)
    REPLY_LAT_COUNT += 1


# --- Light Caching ---
_AN_CACHE: Dict[str, Dict[str, Any]] = {}
_AN_TTL = int(os.environ.get("ANALYSIS_CACHE_TTL", "60"))  # seconds


def _an_key(incoming: str, contact: str) -> str:
    return f"{contact}::{incoming.strip()[:160]}"


def get_analysis_cached(incoming: str, contact: str, profile: Dict[str, Any]) -> Dict[str, Any]:
    if _AN_TTL <= 0:
        return analyze_message(incoming, contact, profile, call_ollama_fn=call_llm)
    now = time.time()
    key = _an_key(incoming, contact)
    item = _AN_CACHE.get(key)
    if item and (now - item.get("ts", 0)) < _AN_TTL:
        return item["data"]
    data = analyze_message(incoming, contact, profile, call_ollama_fn=call_llm)
    # Simple size cap
    if len(_AN_CACHE) > 256:
        _AN_CACHE.clear()
    _AN_CACHE[key] = {"ts": now, "data": data}
    return data


# --- Memory ---
def _contact_key(name: str) -> str:
    return name.strip().lower().replace("/", "_") or "unknown"


def _contact_file(name: str) -> str:
    return os.path.join(DATA_DIR, "contacts", f"{_contact_key(name)}.jsonl")


def load_memory(contact: str, limit: int = 5) -> List[Dict]:
    path = _contact_file(contact)
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()[-limit:]
            return [json.loads(x) for x in lines if x.strip()]
    except FileNotFoundError:
        return []
    except Exception:
        return []


def append_memory(contact: str, record: Dict) -> None:
    os.makedirs(os.path.join(DATA_DIR, "contacts"), exist_ok=True)
    path = _contact_file(contact)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def infer_goal(analysis: Dict) -> str:
    tox = analysis.get("toxicity", 0) or 0
    intent = (analysis.get("intent") or "acknowledge").lower()
    urgent = bool(analysis.get("urgent"))
    triggers = analysis.get("boundary_triggers") or []
    if tox >= 1 or triggers:
        return "de-escalate+boundary"
    if intent == "setup_call":
        return "move_to_call"
    if intent == "make_plan":
        return "propose_time/place"
    if intent == "clarify":
        return "ask_concise_question"
    if urgent:
        return "acknowledge_then_brief_action"
    return "acknowledge_and_close"


# --- Templates & Policy (Bandit) ---
def _ensure_templates():
    if not os.path.exists(TEMPLATES_FILE):
        os.makedirs(DATA_DIR, exist_ok=True)
        default = {
            "ask_concise_question": [
                "Got it — what exactly do you need?",
                "Quick one: what’s the main point here?",
                "Can you clarify the key detail?"
            ],
            "propose_time/place": [
                "Free around {time1} or {time2}. What works?",
                "I can do {time1} or {time2}.",
                "{time1} or {time2} suits."
            ],
            "move_to_call": [
                "Let’s jump on a quick call? {time1} or {time2}.",
                "Call to sort this fast — {time1} or {time2}?"
            ],
            "de-escalate+boundary": [
                "I’m here to keep it respectful. Let’s keep it calm.",
                "I don’t want to argue. Happy to talk when it’s calm."
            ],
            "acknowledge_and_close": [
                "Noted, thanks.",
                "Ok, done.",
                "All good."
            ],
            "acknowledge_then_brief_action": [
                "Got it. I’ll handle it now.",
                "Thanks — I’ll sort it shortly."
            ]
        }
        with open(TEMPLATES_FILE, "w", encoding="utf-8") as f:
            json.dump(default, f, indent=2, ensure_ascii=False)


def load_templates() -> Dict[str, list]:
    _ensure_templates()
    with open(TEMPLATES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def load_policy() -> Dict[str, Dict[str, float]]:
    try:
        with open(POLICY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_policy(p: Dict[str, Dict[str, float]]):
    with open(POLICY_FILE, "w", encoding="utf-8") as f:
        json.dump(p, f, indent=2)


def choose_variant(goal: str, contact: str, variants: list, eps: float = 0.15) -> str:
    policy = load_policy()
    key = f"{goal}::{contact.lower()}"
    weights = policy.get(key) or {}
    # epsilon-greedy
    import random as _rnd
    if not variants:
        return ""
    if _rnd.random() < eps:
        return _rnd.choice(variants)
    # pick max weight
    scored = [(weights.get(v, 0.0), v) for v in variants]
    scored.sort(reverse=True)
    return scored[0][1]


def update_policy(goal: str, contact: str, variant: str, reward: float):
    policy = load_policy()
    key = f"{goal}::{contact.lower()}"
    w = policy.get(key) or {}
    current = w.get(variant, 0.0)
    # simple incremental update
    w[variant] = round(current + 0.1 * (reward - current), 4)
    policy[key] = w
    save_policy(policy)


def propose_times(now=None) -> Dict[str, str]:
    import datetime as dt
    now = now or dt.datetime.now()
    # next two 30-min slots
    minute = (now.minute // 30 + 1) * 30
    delta = dt.timedelta(minutes=(minute - now.minute))
    first = (now + delta).replace(second=0, microsecond=0)
    second = first + dt.timedelta(minutes=30)
    fmt = "%a %I:%M%p"  # e.g., Mon 06:30PM
    return {"time1": first.strftime(fmt), "time2": second.strftime(fmt)}


def fill_template(text: str, tokens: Dict[str, str]) -> str:
    out = text
    for k, v in tokens.items():
        out = out.replace("{" + k + "}", v)
    return out


def check_reply(goal: str, text: str, profile: Dict[str, Any]) -> bool:
    t = (text or "").strip()
    if not t or len(t) > int(profile.get("max_reply_len", 200)):
        return False
    for w in profile.get("banned_words", []):
        if w and w.lower() in t.lower():
            return False
    if goal == "ask_concise_question" and "?" not in t:
        return False
    # simple escalation words filter
    if any(w in t.lower() for w in ["idiot", "stupid", "hate"]):
        return False
    return True

def call_openai(prompt, options=None):
    """Call OpenAI ChatGPT API"""
    if not OPENAI_API_KEY:
        raise RuntimeError("OpenAI API key not configured")

    # Extract temperature and max_tokens from options
    temperature = 0.7
    max_tokens = 150
    if options:
        temperature = options.get("temperature", 0.7)
        max_tokens = options.get("num_predict", 150)  # Convert from Ollama format

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": OPENAI_MODEL,
        "messages": [
            {"role": "system", "content": "You are a helpful SMS assistant. Keep responses concise and natural."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": max_tokens,
        "temperature": temperature
    }

    r = requests.post("https://api.openai.com/v1/chat/completions",
                     json=payload, headers=headers, timeout=90)
    r.raise_for_status()
    data = r.json()

    if "choices" not in data or not data["choices"]:
        raise RuntimeError("No response from OpenAI")

    return data["choices"][0]["message"]["content"].strip()

def call_ollama(prompt, options=None):
    if DISABLE_LLM:
        raise RuntimeError("LLM disabled by OLLAMA_DISABLE env")
    payload = {"model": MODEL_NAME, "prompt": prompt, "stream": False}
    if options:
        payload["options"] = options
    r = requests.post(OLLAMA_URL, json=payload, timeout=90)
    r.raise_for_status()
    data = r.json()
    return (data.get("response") or "").strip()

def call_llm(prompt, options=None):
    """Call the configured LLM (OpenAI or Ollama)"""
    if USE_OPENAI and OPENAI_API_KEY:
        return call_openai(prompt, options)
    else:
        return call_ollama(prompt, options)

def classify_edit_type(original, edited):
    """Classify the type of edit made to improve response quality"""
    if not original or not edited:
        return "unknown"

    orig_len = len(original)
    edit_len = len(edited)

    if edit_len < orig_len * 0.7:
        return "shortened"
    elif edit_len > orig_len * 1.3:
        return "expanded"
    elif "?" in edited and "?" not in original:
        return "made_question"
    elif "!" in edited and "!" not in original:
        return "added_emphasis"
    elif any(word in edited.lower() for word in ["please", "thanks", "sorry"]) and not any(word in original.lower() for word in ["please", "thanks", "sorry"]):
        return "added_politeness"
    else:
        return "refined"

def update_sentiment_learning(feedback_data):
    """Update sentiment learning based on feedback"""
    try:
        sentiment_file = os.path.join(DATA_DIR, "sentiment_learning.json")

        # Load existing learning data
        if os.path.exists(sentiment_file):
            with open(sentiment_file, "r") as f:
                learning_data = json.load(f)
        else:
            learning_data = {
                "successful_patterns": {},
                "failed_patterns": {},
                "edit_patterns": {},
                "contact_preferences": {}
            }

        contact = feedback_data.get("contact", "Unknown")
        incoming = feedback_data.get("incoming", "")
        draft = feedback_data.get("draft", "")
        final = feedback_data.get("final", "")
        accepted = feedback_data.get("accepted", False)
        edited = feedback_data.get("edited", False)

        # Learn from successful patterns
        if accepted and not edited:
            pattern_key = f"{len(incoming.split())}words_{feedback_data.get('goal', 'unknown')}"
            if pattern_key not in learning_data["successful_patterns"]:
                learning_data["successful_patterns"][pattern_key] = []
            learning_data["successful_patterns"][pattern_key].append({
                "incoming_sentiment": feedback_data.get("analysis", {}).get("sentiment", "neutral"),
                "response_style": classify_response_style(draft),
                "contact": contact
            })

        # Learn from edit patterns
        if edited and final:
            edit_type = classify_edit_type(draft, final)
            if edit_type not in learning_data["edit_patterns"]:
                learning_data["edit_patterns"][edit_type] = 0
            learning_data["edit_patterns"][edit_type] += 1

        # Learn contact preferences
        if contact not in learning_data["contact_preferences"]:
            learning_data["contact_preferences"][contact] = {
                "preferred_length": "medium",
                "preferred_tone": "neutral",
                "successful_responses": 0,
                "total_responses": 0
            }

        contact_prefs = learning_data["contact_preferences"][contact]
        contact_prefs["total_responses"] += 1
        if accepted:
            contact_prefs["successful_responses"] += 1
            if final:
                # Learn preferred length and tone
                if len(final) < 50:
                    contact_prefs["preferred_length"] = "short"
                elif len(final) > 100:
                    contact_prefs["preferred_length"] = "long"

        # Save updated learning data
        with open(sentiment_file, "w") as f:
            json.dump(learning_data, f, indent=2)

    except Exception as e:
        print(f"Error updating sentiment learning: {e}")

def classify_response_style(text):
    """Classify the style of a response"""
    if not text:
        return "unknown"

    text_lower = text.lower()

    if any(word in text_lower for word in ["please", "thank", "appreciate"]):
        return "polite"
    elif "?" in text:
        return "questioning"
    elif "!" in text:
        return "enthusiastic"
    elif len(text) < 30:
        return "brief"
    elif any(word in text_lower for word in ["ok", "sure", "yes", "no"]):
        return "direct"
    else:
        return "conversational"

# --- Routes ---
@app.post("/reply")
@rate_limit
@require_allowlisted_contact
def reply():
    start = time.time(); REQ_TOTAL["/reply"] += 1
    try:
        _ensure_license("core")
    except LicenseError as e:
        ERR_TOTAL["/reply"] += 1
        return jsonify({"error": "license", "message": str(e)}), 403
    data = request.json or {}
    incoming = data.get("incoming", "")
    contact = data.get("contact", "Unknown")

    profile = load_profile()
    # 1) Analyze
    analysis = get_analysis_cached(incoming, contact, profile)
    # 1b) Goal selection
    goal = infer_goal(analysis)
    # 1c) Load recent memory (for light continuity)
    memory = load_memory(contact, limit=3)
    # 2) Choose template variant (bandit) and tokens
    # Load templates (lightweight; original function ensures defaults on first call)
    templates = load_templates()
    variants = templates.get(goal, [])
    tokens = {}
    if goal in ("propose_time/place", "move_to_call"):
        tokens.update(propose_times())

    chosen = choose_variant(goal, contact, variants)
    templated = fill_template(chosen, tokens) if chosen else ""

    # 2b) Generate or polish
    prompt = build_reply_prompt(incoming, contact, profile, {**analysis, "goal": goal, "memory": memory})
    intent = (analysis.get("intent") or "").lower()
    if goal in ("propose_time/place", "move_to_call", "ask_concise_question") or intent in ("make_plan", "setup_call", "clarify"):
        opts = {"temperature": 0.2, "top_p": 0.8, "num_predict": 100}
    elif goal.startswith("de-escalate"):
        opts = {"temperature": 0.5, "top_p": 0.9, "num_predict": 120}
    else:
        opts = {"temperature": 0.3, "top_p": 0.9, "num_predict": 110}
    try:
        # If OpenAI is enabled, prioritize pure LLM generation
        if USE_OPENAI and OPENAI_API_KEY:
            draft = call_llm(prompt, options=opts)
        else:
            # Use template-based approach for Ollama/local models
            base = templated or ""
            if base:
                # Ask model to lightly polish base into final under constraints
                polish = f"Refine this into a single SMS under {profile.get('max_reply_len',200)} chars, keep meaning: \n'''{base}'''"
                draft = call_llm(polish, options={"temperature": 0.2, "num_predict": 120})
            else:
                draft = call_llm(prompt, options=opts)
    except Exception as e:
        # Fallback to safe template if LLM fails or disabled
        safe = templated or fill_template((templates.get(goal) or ["Ok."])[0], tokens)
        draft = safe or "Ok."
        analysis["llm_failed"] = True
        print(f"LLM call failed: {e}")  # Debug logging
    # 3) Post-process
    draft = postprocess_reply(draft, profile)
    # 3b) Self-check; on failure, fallback to safe template
    if not check_reply(goal, draft, profile):
        safe = fill_template((templates.get(goal) or ["Ok."])[0], tokens)
        draft = postprocess_reply(safe, profile)
    # record memory of this turn (incoming + draft + goal)
    append_memory(contact, {"incoming": incoming, "draft": draft, "goal": goal, "ts": (request.headers.get('X-Time') or '')})
    variant = chosen or random.choice(["A", "B"])  # variant used
    _observe_reply_latency(time.time() - start)
    return jsonify({"draft": draft, "analysis": analysis, "goal": goal, "variant": variant})

def generate_reply_with_context(context_prompt: str, incoming: str, contact: str, analysis: Dict, personality) -> tuple:
    """Generate reply using conversation context and personality"""
    profile = load_profile()

    # Use context-aware prompt
    opts = {"temperature": 0.4, "top_p": 0.9, "max_tokens": 150}

    try:
        # Try multi-model system first
        multi_model_manager = get_multi_model_manager()

        # Use async call in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            response = loop.run_until_complete(
                multi_model_manager.generate_response(
                    context_prompt,
                    ModelCapability.CONVERSATION,
                    opts
                )
            )
            if response:
                draft = response.content
            else:
                # Fallback to standard generation
                return generate_reply(incoming, contact, analysis)
        finally:
            loop.close()

    except Exception as e:
        print(f"Multi-model LLM call failed: {e}")
        try:
            if USE_OPENAI and OPENAI_API_KEY:
                draft = call_llm(context_prompt, options=opts)
            else:
                # Fallback to standard generation
                return generate_reply(incoming, contact, analysis)
        except Exception as e2:
            print(f"Fallback LLM call failed: {e2}")
            return generate_reply(incoming, contact, analysis)

    # Post-process with personality considerations
    if personality:
        draft = apply_personality_style(draft, personality)

    draft = postprocess_reply(draft, profile)

    return draft, analysis

def apply_personality_style(draft: str, personality) -> str:
    """Apply personality-specific styling to response"""
    # Adjust emoji usage
    if personality.emoji_usage == "none":
        draft = re.sub(r'[😀-🿿]', '', draft)  # Remove emojis
    elif personality.emoji_usage == "frequent" and not re.search(r'[😀-🿿]', draft):
        # Add appropriate emoji if none present
        if "great" in draft.lower() or "awesome" in draft.lower():
            draft += " 😊"
        elif "sorry" in draft.lower():
            draft += " 😔"

    # Adjust response length
    if personality.response_length_preference == "brief" and len(draft) > 100:
        # Truncate while preserving meaning
        sentences = draft.split('.')
        if len(sentences) > 1:
            draft = sentences[0] + '.'
    elif personality.response_length_preference == "detailed" and len(draft) < 50:
        # Add more context (simple approach)
        if "yes" in draft.lower():
            draft = draft.replace("Yes", "Yes, absolutely")
        elif "no" in draft.lower():
            draft = draft.replace("No", "No, unfortunately")

    return draft

@app.post("/feedback")
@require_permission("feedback")
@rate_limit
def feedback():
    data = request.json or {}
    with open(FEEDBACK_FILE, "a") as f:
        f.write(json.dumps(data, ensure_ascii=False) + "\n")

    # Lightweight learning from accepted+edited finals
    prof = load_profile()
    final = (data.get("final") or "").strip()
    accepted = bool(data.get("accepted"))
    edited = bool(data.get("edited"))
    # Update memory with final when provided
    contact = data.get("contact") or "Unknown"
    if final:
        append_memory(contact, {"final": final, "accepted": accepted, "edited": edited, "ts": data.get("ts")})
    # Structured tags for future learning
    tags = data.get("tags") or {}
    if final and accepted:
        # Add short phrases (not single words) to preferred list
        for chunk in final.split("."):
            chunk = chunk.strip()
            if 6 <= len(chunk) <= 60 and chunk not in prof["preferred_phrases"]:
                prof["preferred_phrases"].append(chunk)
    save_profile(prof)

    # Apply enhanced sentiment learning
    update_sentiment_learning(data)

    return jsonify({"ok": True, "learning_applied": True})

@app.post("/outcome")
@require_admin
@rate_limit
def outcome():
    body = request.json or {}
    contact = body.get("contact") or "Unknown"
    goal = body.get("goal") or ""
    variant = body.get("variant") or ""
    outcome = (body.get("outcome") or "").lower()  # success/progress/stall/escalation
    reward = {"success": 1.0, "progress": 0.6, "stall": 0.1, "escalation": 0.0}.get(outcome, 0.2)
    try:
        if goal and variant:
            update_policy(goal, contact, variant, reward)
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.post("/assist")
@rate_limit
@require_allowlisted_contact
def assist():
    REQ_TOTAL["/assist"] += 1
    try:
        _ensure_license("core")
    except LicenseError as e:
        ERR_TOTAL["/assist"] += 1
        return jsonify({"error": "license", "message": str(e)}), 403
    body = request.json or {}
    action = (body.get("action") or "").lower()  # propose_time | move_to_call | ask_clarify
    incoming = body.get("incoming") or ""
    contact = body.get("contact") or "Unknown"
    tokens = {}
    if action in ("propose_time", "move_to_call"):
        tokens.update(propose_times())
    templates = load_templates()
    goal_map = {"propose_time": "propose_time/place", "move_to_call": "move_to_call", "ask_clarify": "ask_concise_question"}
    goal = goal_map.get(action, "acknowledge_and_close")
    variants = templates.get(goal, [])
    chosen = choose_variant(goal, contact, variants)
    text = fill_template(chosen or (variants[0] if variants else "Ok."), tokens)
    return jsonify({"text": text, "goal": goal})

@app.get("/memory")
def get_memory():
    contact = request.args.get("contact") or "Unknown"
    limit = int(request.args.get("limit", 5))
    return jsonify({"contact": contact, "items": load_memory(contact, limit=limit)})

@app.get("/memory/summary")
def get_memory_summary():
    contact = request.args.get("contact") or "Unknown"
    limit = int(request.args.get("limit", 10))
    items = load_memory(contact, limit=limit)
    return jsonify({"contact": contact, **summarize_memory(contact, items, call_ollama_fn=call_llm)})

@app.delete("/memory")
@require_admin
def delete_memory():
    contact = request.args.get("contact") or "Unknown"
    path = _contact_file(contact)
    try:
        if os.path.exists(path):
            os.remove(path)
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.get("/goals")
def get_goals():
    contact = request.args.get("contact") or "Unknown"
    limit = int(request.args.get("limit", 10))
    items = load_memory(contact, limit=limit)
    goals = [x.get("goal") for x in items if x.get("goal")]
    return jsonify({"contact": contact, "goals": goals})

@app.get("/profile")
def get_profile():
    return jsonify(load_profile())

@app.post("/profile")
@require_admin
def update_profile():
    body = request.json or {}
    prof = load_profile()
    for k in ["style_rules", "preferred_phrases", "banned_words"]:
        if k in body:
            prof[k] = body[k]
    save_profile(prof)
    return jsonify({"ok": True})

@app.get("/config")
def get_config():
    """Get current AI configuration"""
    return jsonify({
        "use_openai": USE_OPENAI,
        "has_openai_key": bool(OPENAI_API_KEY),
        "openai_model": OPENAI_MODEL,
        "ollama_model": MODEL_NAME,
        "llm_disabled": DISABLE_LLM
    })

@app.post("/config")
@require_admin
def update_config():
    """Update AI configuration"""
    global OPENAI_API_KEY, USE_OPENAI, OPENAI_MODEL
    body = request.json or {}

    if "openai_api_key" in body:
        OPENAI_API_KEY = body["openai_api_key"].strip()
        os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY

    if "use_openai" in body:
        USE_OPENAI = bool(body["use_openai"])
        os.environ["USE_OPENAI"] = "1" if USE_OPENAI else "0"

    if "openai_model" in body:
        OPENAI_MODEL = body["openai_model"].strip() or "gpt-3.5-turbo"
        os.environ["OPENAI_MODEL"] = OPENAI_MODEL

    return jsonify({"ok": True})


# --- License endpoints ---
@app.get("/license/status")
def license_status():
    lm = get_license_manager()
    return jsonify(lm.get_license_info())


@app.post("/license/activate")
def license_activate():
    body = request.json or {}
    key = (body.get("key") or "").strip()
    if not key:
        return jsonify({"ok": False, "error": "missing key"}), 400
    lm = get_license_manager()
    try:
        ok = lm.activate_license(key)
        return jsonify({"ok": bool(ok)})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400


@app.get("/license/hwid")
def license_hwid():
    lm = get_license_manager()
    # Expose the hardware ID to allow hardware-bound token issuance
    return jsonify({"hardware_id": lm.hardware_id})


@app.get("/")
def index():
    # Simple landing page with links to available interfaces
    html = """
<!doctype html>
<html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'>
<title>SMS AI Server</title>
<style>
body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;margin:32px;line-height:1.6;max-width:800px}
.card{border:1px solid #ddd;padding:20px;margin:16px 0;border-radius:8px;background:#f9f9f9}
.btn{display:inline-block;padding:10px 16px;margin:8px 8px 8px 0;background:#007bff;color:white;text-decoration:none;border-radius:4px}
.btn:hover{background:#0056b3}
h1{color:#333}
.status{color:#28a745;font-weight:bold}
</style>
</head><body>
<h1>🤖 SMS AI Server</h1>
<div class="card">
    <h2>Server Status</h2>
    <p class="status">✅ Running and Ready</p>
    <p>The SMS AI server is operational and ready to process messages.</p>
</div>

<div class="card">
    <h2>🧪 Test Interface</h2>
    <p>Try out the SMS AI functionality with a simple web interface.</p>
    <a href="/client" class="btn">Open Test Client</a>
    <a href="/config-ui" class="btn">AI Configuration</a>
</div>

<div class="card">
    <h2>⚙️ Admin Panel</h2>
    <p>Configure profiles, manage memory, and view system settings.</p>
    <a href="/admin" class="btn">Admin Panel</a>
    <a href="/admin/login" class="btn">Admin Login</a>
</div>

<div class="card">
    <h2>👥 User Management</h2>
    <p>Manage user accounts, API tokens, and permissions.</p>
    <a href="/users/login-ui" class="btn">User Login</a>
    <a href="/users/dashboard" class="btn">User Dashboard</a>
</div>

<div class="card">
    <h2>📊 System Info</h2>
    <p>Monitor server health and performance metrics.</p>
    <a href="/health" class="btn">Health Check</a>
    <a href="/metrics" class="btn">Metrics</a>
    <a href="/privacy" class="btn">Privacy Policy</a>
</div>

<div class="card">
    <h2>📱 Mobile Access</h2>
    <p>Access this interface from your phone at:</p>
    <code>http://192.168.1.107:8081</code>
</div>
</body></html>
"""
    return Response(html, mimetype="text/html; charset=utf-8")

@app.get("/health")
def health():
    """Basic liveness probe - returns immediately"""
    return jsonify({"ok": True, "status": "alive"}), 200

@app.get("/health/detailed")
async def detailed_health():
    """Comprehensive health check including external services"""
    try:
        from utils.health_checker import perform_health_check
        health_summary = await perform_health_check()

        # Return appropriate HTTP status based on overall health
        status_code = 200
        if health_summary['overall_status'] == 'unhealthy':
            status_code = 503  # Service Unavailable
        elif health_summary['overall_status'] == 'degraded':
            status_code = 200  # OK but with warnings

        return jsonify(health_summary), status_code

    except ImportError:
        return jsonify({
            "ok": False,
            "error": "Health checker not available",
            "overall_status": "unknown"
        }), 500
    except Exception as e:
        return jsonify({
            "ok": False,
            "error": f"Health check failed: {str(e)}",
            "overall_status": "unhealthy"
        }), 500


@app.get("/metrics")
def metrics():
    # Minimal Prometheus-like text exposition
    uptime = time.time() - START_TIME
    lines = []
    lines.append(f"smsai_uptime_seconds {uptime:.3f}")
    for route, c in REQ_TOTAL.items():
        lines.append(f"smsai_requests_total{{route=\"{route}\"}} {c}")
    for route, c in ERR_TOTAL.items():
        lines.append(f"smsai_errors_total{{route=\"{route}\"}} {c}")
    for route, c in _RL_TOTAL.items():
        lines.append(f"smsai_rate_limited_total{{route=\"{route}\"}} {c}")
    lines.append(f"smsai_reply_latency_seconds_sum {REPLY_LAT_SUM:.6f}")
    lines.append(f"smsai_reply_latency_seconds_count {REPLY_LAT_COUNT}")
    body = "\n".join(lines) + "\n"
    return app.response_class(response=body, status=200, mimetype="text/plain; version=0.0.4")


@app.get("/privacy")
def privacy():
    # Serve a static privacy policy HTML if present
    try:
        path = os.path.join(os.path.dirname(__file__), "docs", "privacy_policy.html")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                html = f.read()
        else:
            html = """
<!doctype html>
<html><head><meta charset='utf-8'><title>Privacy Policy — SynapseFlow AI</title></head>
<body><h1>Privacy Policy — SynapseFlow AI</h1>
<p>We process message content to generate auto‑replies and maintain lightweight memory on your server. We do not sell data. Optional integrations (Twilio/Messenger) are used only if configured by you. License data is encrypted on disk. You can purge stored memory per contact at any time.</p>
<p>Contact: support@st1cky.pty.ltd</p>
</body></html>
"""
        return Response(html, mimetype="text/html; charset=utf-8")
    except Exception as e:
        return Response(f"Privacy policy unavailable: {e}", mimetype="text/plain; charset=utf-8", status=500)


@app.get("/admin")
def admin():
    # Require admin token when provided in environment (header X-Admin-Token or query token)
    token_env = os.environ.get("ADMIN_TOKEN", "").strip()
    if token_env:
        tok = request.headers.get("X-Admin-Token") or request.args.get("token")
        if not tok or tok != token_env:
            return Response("Unauthorized: missing or invalid admin token", status=401, mimetype="text/plain; charset=utf-8")
    # Minimal admin panel for profile, memory, policy, and license
    html = """
<!doctype html>
<html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'>
<title>SynapseFlow AI Admin</title>
<style>body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;margin:16px;line-height:1.4}section{border:1px solid #ddd;padding:12px;margin:12px 0;border-radius:6px}input,textarea{width:100%;margin:4px 0;padding:6px}button{margin:4px 0;padding:6px 10px}.banner{background:#f4f8ff;border:1px solid #cfe0ff;padding:8px;border-radius:6px;margin:12px 0}.row{display:flex;gap:8px;flex-wrap:wrap}.row>*{flex:1}</style>
</head><body>
<h1>SynapseFlow AI Admin</h1>

<div class='banner'>
  <strong>Rate limit:</strong> __RL_CAP__/min
  &nbsp; | &nbsp; <strong>Model:</strong> __MODEL__
  &nbsp; | &nbsp; <strong>LLM:</strong> __LLM_STATUS__
  &nbsp; | &nbsp; <strong>License:</strong> <span id='licStatus'>checking…</span>
</div>

<section>
<h2>Profile</h2>
<div>
  <label>Style Rules</label>
  <textarea id='style' rows='2'></textarea>
  <label>Preferred Phrases (comma separated)</label>
  <input id='pref' type='text' />
  <label>Banned Words (comma separated)</label>
  <input id='banned' type='text' />
  <div class='row'>
    <button onclick='saveProfile()'>Save Profile</button>
    <button onclick='exportProfile()'>Export Profile</button>
    <label style='display:inline-block'>Import <input id='profFile' type='file' accept='application/json' onchange='importProfile(event)'></label>
  </div>
  <span id='pmsg'></span>
</div>
</section>

<section>
<h2>Memory</h2>
<div>
  <input id='contact' placeholder='Contact name' />
  <button onclick='loadMem()'>Load</button>
  <button onclick='purgeMem()'>Purge</button>
  <pre id='mem' style='white-space:pre-wrap;background:#f7f7f7;padding:8px;border-radius:4px;'></pre>
</div>
</section>

<section>
<h2>Policy (Bandit Weights)</h2>
<div>
  <div class='row'>
    <button onclick='loadPolicy()'>Load Policy</button>
    <button onclick='savePolicy()'>Save Policy</button>
    <button onclick='exportPolicy()'>Export Policy</button>
    <label style='display:inline-block'>Import <input id='polFile' type='file' accept='application/json' onchange='importPolicy(event)'></label>
  </div>
  <textarea id='policyJson' rows='6' placeholder='{}'></textarea>
  <span id='polmsg'></span>
  <small>Note: format is a JSON object like {"goal::contact": {"variant": weight, ...}}.</small>
  
</div>
</section>

<section>
<h2>License</h2>
<div>
  <button onclick='checkLic()'>Check Status</button>
  <button onclick='getHwid()'>Get HWID</button>
  <input id='token' placeholder='Paste activation token' />
  <div class='row'>
    <button onclick='activate()'>Activate</button>
    <button onclick='copyStatus()'>Copy Status</button>
    <button onclick='copyToken()'>Copy Token</button>
  </div>
  <pre id='lic' style='white-space:pre-wrap;background:#f7f7f7;padding:8px;border-radius:4px;'></pre>
</div>
</section>

<script>
async function fetchJson(url, opts={}){const r=await fetch(url, Object.assign({headers:{'Content-Type':'application/json'}}, opts)); if(!r.ok){throw new Error((await r.text())||r.statusText)} return await r.json()}
async function loadProfile(){try{const p=await fetchJson('/profile'); document.getElementById('style').value=p.style_rules||''; document.getElementById('pref').value=(p.preferred_phrases||[]).join(', '); document.getElementById('banned').value=(p.banned_words||[]).join(', ')}catch(e){document.getElementById('pmsg').textContent='Err: '+e.message}}
async function saveProfile(){try{const body={}; body.style_rules=document.getElementById('style').value; body.preferred_phrases=document.getElementById('pref').value.split(',').map(s=>s.trim()).filter(Boolean); body.banned_words=document.getElementById('banned').value.split(',').map(s=>s.trim()).filter(Boolean); await fetchJson('/profile',{method:'POST',body:JSON.stringify(body)}); document.getElementById('pmsg').textContent='Saved'}catch(e){document.getElementById('pmsg').textContent='Err: '+e.message}}
function exportProfile(){const p={style_rules:document.getElementById('style').value, preferred_phrases:document.getElementById('pref').value.split(',').map(s=>s.trim()).filter(Boolean), banned_words:document.getElementById('banned').value.split(',').map(s=>s.trim()).filter(Boolean)}; const blob=new Blob([JSON.stringify(p,null,2)],{type:'application/json'}); const a=document.createElement('a'); a.href=URL.createObjectURL(blob); a.download='profile.json'; a.click(); URL.revokeObjectURL(a.href)}
function importProfile(ev){const f=ev.target.files[0]; if(!f) return; const rd=new FileReader(); rd.onload=async ()=>{try{const pj=JSON.parse(rd.result); await fetchJson('/profile',{method:'POST',body:JSON.stringify(pj)}); document.getElementById('pmsg').textContent='Imported'; loadProfile()}catch(e){document.getElementById('pmsg').textContent='Err: '+e.message}}; rd.readAsText(f)}
async function loadMem(){const c=document.getElementById('contact').value.trim(); if(!c){alert('Enter contact');return} try{const r=await fetchJson('/memory?contact='+encodeURIComponent(c)+'&limit=10'); document.getElementById('mem').textContent=JSON.stringify(r.items||[], null, 2)}catch(e){document.getElementById('mem').textContent='Err: '+e.message}}
async function purgeMem(){const c=document.getElementById('contact').value.trim(); if(!c){alert('Enter contact');return} try{await fetchJson('/memory?contact='+encodeURIComponent(c),{method:'DELETE'}); document.getElementById('mem').textContent='Purged'}catch(e){document.getElementById('mem').textContent='Err: '+e.message}}
async function checkLic(){try{const r=await fetchJson('/license/status'); document.getElementById('lic').textContent=JSON.stringify(r,null,2); var s=(r.status||'unknown')+(r.tier?(' / '+r.tier):'')+(r.days_remaining!=null?(' / '+r.days_remaining+'d'):''); document.getElementById('licStatus').textContent=s}catch(e){document.getElementById('lic').textContent='Err: '+e.message; document.getElementById('licStatus').textContent='error'}}
async function getHwid(){try{const r=await fetchJson('/license/hwid'); document.getElementById('lic').textContent=JSON.stringify(r,null,2)}catch(e){document.getElementById('lic').textContent='Err: '+e.message}}
async function activate(){try{const t=document.getElementById('token').value.trim(); const r=await fetchJson('/license/activate',{method:'POST',body:JSON.stringify({key:t})}); document.getElementById('lic').textContent=JSON.stringify(r,null,2)}catch(e){document.getElementById('lic').textContent='Err: '+e.message}}
function copyStatus(){const txt=document.getElementById('lic').textContent||''; navigator.clipboard.writeText(txt).catch(()=>{})}
function copyToken(){const v=document.getElementById('token').value||''; navigator.clipboard.writeText(v).catch(()=>{})}

async function loadPolicy(){try{const p=await fetchJson('/admin/policy'); document.getElementById('policyJson').value=JSON.stringify(p,null,2); document.getElementById('polmsg').textContent='Loaded'}catch(e){document.getElementById('polmsg').textContent='Err: '+e.message}}
async function savePolicy(){try{const raw=document.getElementById('policyJson').value||'{}'; const obj=JSON.parse(raw); await fetchJson('/admin/policy',{method:'POST',body:JSON.stringify(obj)}); document.getElementById('polmsg').textContent='Saved'}catch(e){document.getElementById('polmsg').textContent='Err: '+e.message}}
function exportPolicy(){const raw=document.getElementById('policyJson').value||'{}'; const blob=new Blob([raw],{type:'application/json'}); const a=document.createElement('a'); a.href=URL.createObjectURL(blob); a.download='policy.json'; a.click(); URL.revokeObjectURL(a.href)}
function importPolicy(ev){const f=ev.target.files[0]; if(!f) return; const rd=new FileReader(); rd.onload=()=>{document.getElementById('policyJson').value=rd.result}; rd.readAsText(f)}
loadProfile(); checkLic();
</script>
</body></html>
"""
    html = html.replace("__RL_CAP__", str(int(os.environ.get("RATE_LIMIT_PER_MIN", "120"))))
    html = html.replace("__MODEL__", os.environ.get("OLLAMA_MODEL", MODEL_NAME))
    html = html.replace("__LLM_STATUS__", ("disabled" if os.environ.get("OLLAMA_DISABLE", "0") in ("1", "true", "yes") else "enabled"))
    return Response(html, mimetype="text/html; charset=utf-8")


@app.get("/config-ui")
def config_ui():
    """AI Configuration Interface"""
    html = """
<!doctype html>
<html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'>
<title>AI Configuration - SMS AI</title>
<style>
body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;margin:32px;line-height:1.6;max-width:600px}
.card{border:1px solid #ddd;padding:20px;margin:16px 0;border-radius:8px;background:#f9f9f9}
input,select{width:100%;padding:8px;margin:4px 0;border:1px solid #ddd;border-radius:4px}
button{padding:10px 16px;margin:8px 8px 8px 0;background:#007bff;color:white;border:none;border-radius:4px;cursor:pointer}
button:hover{background:#0056b3}
.status{padding:10px;margin:10px 0;border-radius:4px}
.success{background:#d4edda;color:#155724;border:1px solid #c3e6cb}
.error{background:#f8d7da;color:#721c24;border:1px solid #f5c6cb}
.info{background:#d1ecf1;color:#0c5460;border:1px solid #bee5eb}
label{display:block;margin-top:10px;font-weight:bold}
</style>
</head><body>
<h1>🤖 AI Configuration</h1>

<div class="card">
    <h2>Current Status</h2>
    <div id="status" class="status info">Loading...</div>
</div>

<div class="card">
    <h2>OpenAI Configuration</h2>
    <label>
        <input type="checkbox" id="useOpenAI"> Use OpenAI ChatGPT
    </label>
    <label>OpenAI API Key:</label>
    <input type="password" id="apiKey" placeholder="sk-...">
    <label>Model:</label>
    <select id="model">
        <option value="gpt-3.5-turbo">GPT-3.5 Turbo (Recommended)</option>
        <option value="gpt-4">GPT-4 (More expensive)</option>
        <option value="gpt-4-turbo">GPT-4 Turbo</option>
    </select>
    <button onclick="saveConfig()">Save Configuration</button>
    <button onclick="testAPI()">Test API</button>
</div>

<div class="card">
    <h2>Response Quality</h2>
    <p>Using ChatGPT will provide:</p>
    <ul>
        <li>✅ More natural, contextual responses</li>
        <li>✅ Better understanding of nuance and emotion</li>
        <li>✅ Improved conversation flow</li>
        <li>✅ Adaptive communication style</li>
    </ul>
    <p><strong>Note:</strong> Requires valid OpenAI API key and will incur usage costs.</p>
</div>

<div id="result" class="status" style="display:none"></div>

<script>
async function loadConfig() {
    try {
        const r = await fetch('/config');
        const config = await r.json();

        document.getElementById('useOpenAI').checked = config.use_openai;
        document.getElementById('model').value = config.openai_model;

        let statusText = `Current: ${config.use_openai ? 'OpenAI ChatGPT' : 'Local Templates'}`;
        if (config.use_openai) {
            statusText += config.has_openai_key ? ' ✅ API Key Set' : ' ❌ No API Key';
        }
        if (config.llm_disabled) {
            statusText += ' (LLM Disabled)';
        }

        document.getElementById('status').textContent = statusText;
    } catch (e) {
        document.getElementById('status').textContent = 'Error loading config: ' + e.message;
        document.getElementById('status').className = 'status error';
    }
}

async function saveConfig() {
    const config = {
        use_openai: document.getElementById('useOpenAI').checked,
        openai_api_key: document.getElementById('apiKey').value,
        openai_model: document.getElementById('model').value
    };

    try {
        const r = await fetch('/config', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(config)
        });

        if (r.ok) {
            showResult('Configuration saved successfully!', 'success');
            loadConfig();
            document.getElementById('apiKey').value = ''; // Clear for security
        } else {
            showResult('Error saving configuration: ' + r.statusText, 'error');
        }
    } catch (e) {
        showResult('Error: ' + e.message, 'error');
    }
}

async function testAPI() {
    const result = document.getElementById('result');
    result.style.display = 'block';
    result.textContent = 'Testing API...';
    result.className = 'status info';

    try {
        const r = await fetch('/reply', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                incoming: 'Hello, this is a test message',
                contact: 'TestUser'
            })
        });

        const data = await r.json();
        if (r.ok && data.draft) {
            showResult(`API Test Successful! Response: "${data.draft}"`, 'success');
        } else {
            showResult('API Test Failed: ' + (data.error || 'Unknown error'), 'error');
        }
    } catch (e) {
        showResult('API Test Error: ' + e.message, 'error');
    }
}

function showResult(message, type) {
    const result = document.getElementById('result');
    result.textContent = message;
    result.className = 'status ' + type;
    result.style.display = 'block';
}

loadConfig();
</script>
</body></html>
"""
    return Response(html, mimetype="text/html; charset=utf-8")

@app.get("/client")
def client_page():
    # Minimal HTML client for testing /reply and /assist
    html = """
<!doctype html>
<html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'>
<title>SynapseFlow AI Platform</title>
<style>body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;margin:16px;line-height:1.4}input,textarea,select{width:100%;padding:8px;margin:4px 0}button{padding:8px 12px;margin:4px 0}</style>
</head><body>
<h1>SynapseFlow AI Platform</h1>
<section style='border:1px solid #ddd;padding:12px;border-radius:6px'>
  <h2>Reply</h2>
  <input id='contact' placeholder='Contact (e.g., Tester)'>
  <textarea id='incoming' rows='3' placeholder='Incoming message'></textarea>
  <button onclick='sendReply()'>Get Draft</button>
  <pre id='out' style='white-space:pre-wrap;background:#f7f7f7;padding:8px;border-radius:4px'></pre>
</section>
<section style='border:1px solid #ddd;padding:12px;border-radius:6px'>
  <h2>Assist</h2>
  <select id='action'>
    <option value='ask_clarify'>Ask Clarify</option>
    <option value='propose_time'>Propose Time</option>
    <option value='move_to_call'>Move to Call</option>
  </select>
  <button onclick='assist()'>Generate</button>
  <pre id='assistOut' style='white-space:pre-wrap;background:#f7f7f7;padding:8px;border-radius:4px'></pre>
</section>
<script>
async function sendReply(){
  const contact = document.getElementById('contact').value.trim()||'Tester';
  const incoming = document.getElementById('incoming').value.trim();
  if(!incoming){ alert('Enter incoming'); return }
  const r = await fetch('/reply',{method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({incoming, contact})});
  const t = await r.text();
  document.getElementById('out').textContent = t;
}
async function assist(){
  const action = document.getElementById('action').value;
  const r = await fetch('/assist',{method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({action})});
  const t = await r.text();
  document.getElementById('assistOut').textContent = t;
}
</script>
</body></html>
"""
    return Response(html, mimetype="text/html; charset=utf-8")


@app.get("/admin/login")
def admin_login():
    # Simple login page that redirects to /admin?token=...
    html = """
<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'>
<title>Admin Login</title>
<style>body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;margin:32px;line-height:1.4}input{width:100%;padding:8px}button{padding:8px 12px;margin-top:8px}</style>
</head><body>
<h1>Admin Login</h1>
<p>Enter your admin token to continue.</p>
<input id='t' type='password' placeholder='Admin token'/>
<button onclick='go()'>Continue</button>
<script>
function go(){var v=document.getElementById('t').value.trim(); if(!v){alert('Enter token'); return} localStorage.setItem('admin_token', v); var u=new URL('/admin', location.origin); u.searchParams.set('token', v); location.href=u.toString();}
// Auto-fill from localStorage
document.getElementById('t').value = localStorage.getItem('admin_token')||'';
</script>
</body></html>
"""
    return Response(html, mimetype="text/html; charset=utf-8")


# --- Admin Policy Endpoints ---
@app.get("/admin/policy")
@require_admin
def admin_get_policy():
    return jsonify(load_policy())


@app.post("/admin/policy")
@require_admin
def admin_set_policy():
    body = request.json or {}
    if not isinstance(body, dict):
        return jsonify({"ok": False, "error": "invalid policy format"}), 400
    try:
        save_policy(body)
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# --- User Management Endpoints ---
@app.post("/users/register")
@require_admin
def register_user():
    """Register a new user (admin only)"""
    body = request.json or {}
    username = body.get("username", "").strip()
    password = body.get("password", "").strip()
    email = body.get("email", "").strip()
    role = body.get("role", "user").strip()

    if not all([username, password, email]):
        return jsonify({"ok": False, "error": "username, password, and email required"}), 400

    um = get_user_manager()
    success, result = um.create_user(username, password, email, role)

    if success:
        return jsonify({"ok": True, "user_id": result, "username": username, "role": role})
    else:
        return jsonify({"ok": False, "error": result}), 400

@app.post("/users/login")
def login_user():
    """User login to get API token"""
    body = request.json or {}
    username = body.get("username", "").strip()
    password = body.get("password", "").strip()
    expires_days = int(body.get("expires_days", 30))
    description = body.get("description", "").strip()

    if not all([username, password]):
        return jsonify({"ok": False, "error": "username and password required"}), 400

    um = get_user_manager()
    auth_success, user = um.authenticate_user(username, password)

    if not auth_success:
        return jsonify({"ok": False, "error": "invalid credentials"}), 401

    token_success, token = um.generate_token(username, expires_days, description)

    if token_success:
        return jsonify({
            "ok": True,
            "token": token,
            "user": {
                "username": username,
                "role": user["role"],
                "email": user["email"]
            },
            "expires_days": expires_days
        })
    else:
        return jsonify({"ok": False, "error": "failed to generate token"}), 500

@app.get("/users/me")
@require_user_auth
def get_current_user():
    """Get current user info"""
    user = request.current_user
    token = request.current_token

    return jsonify({
        "username": user.get("username"),
        "email": user.get("email"),
        "role": user.get("role"),
        "created_at": user.get("created_at"),
        "last_login": user.get("last_login"),
        "usage_stats": user.get("usage_stats"),
        "token_info": {
            "created_at": token.get("created_at"),
            "expires_at": token.get("expires_at"),
            "usage_count": token.get("usage_count"),
            "description": token.get("description")
        }
    })

@app.get("/users/tokens")
@require_user_auth
def list_user_tokens():
    """List user's API tokens"""
    user = request.current_user
    um = get_user_manager()
    tokens = um.list_user_tokens(user["username"])
    return jsonify({"tokens": tokens})

@app.post("/users/tokens/revoke")
@require_user_auth
def revoke_token():
    """Revoke an API token"""
    body = request.json or {}
    token = body.get("token", "").strip()

    if not token:
        return jsonify({"ok": False, "error": "token required"}), 400

    um = get_user_manager()
    success = um.revoke_token(token)

    return jsonify({"ok": success})

@app.get("/users/list")
@require_permission("admin")
def list_users():
    """List all users (admin only)"""
    um = get_user_manager()
    users = []
    for username, user in um.users.items():
        users.append({
            "username": username,
            "email": user.get("email"),
            "role": user.get("role"),
            "created_at": user.get("created_at"),
            "last_login": user.get("last_login"),
            "active": user.get("active"),
            "usage_stats": user.get("usage_stats")
        })
    return jsonify({"users": users})

@app.get("/users/roles")
def get_roles():
    """Get available roles and permissions"""
    from user_management import ROLES
    return jsonify({"roles": ROLES})

# --- Advanced Analytics Endpoints ---
@app.get("/analytics/system-health")
@require_permission("admin")
def get_system_health():
    """Get comprehensive system health status"""
    try:
        system_monitor = get_system_monitor()
        health_data = system_monitor.get_system_health()
        return jsonify(health_data)
    except Exception as e:
        return jsonify({"error": f"Failed to get system health: {e}"}), 500

@app.get("/analytics/usage")
@require_permission("admin")
def get_usage_analytics():
    """Get usage analytics"""
    try:
        days = int(request.args.get('days', 7))
        system_monitor = get_system_monitor()
        usage_data = system_monitor.get_usage_analytics(days)
        return jsonify(usage_data)
    except Exception as e:
        return jsonify({"error": f"Failed to get usage analytics: {e}"}), 500

@app.post("/analytics/start-monitoring")
@require_permission("admin")
def start_system_monitoring():
    """Start system monitoring"""
    try:
        interval = int(request.json.get('interval', 60))
        system_monitor = get_system_monitor()
        system_monitor.start_monitoring(interval)
        return jsonify({"ok": True, "message": f"Monitoring started with {interval}s interval"})
    except Exception as e:
        return jsonify({"error": f"Failed to start monitoring: {e}"}), 500

@app.post("/analytics/stop-monitoring")
@require_permission("admin")
def stop_system_monitoring():
    """Stop system monitoring"""
    try:
        system_monitor = get_system_monitor()
        system_monitor.stop_monitoring()
        return jsonify({"ok": True, "message": "Monitoring stopped"})
    except Exception as e:
        return jsonify({"error": f"Failed to stop monitoring: {e}"}), 500

# --- Security Endpoints ---
@app.get("/security/summary")
@require_permission("admin")
def get_security_summary():
    """Get security summary and threat analysis"""
    try:
        security_monitor = get_security_monitor()
        summary = security_monitor.get_security_summary()
        return jsonify(summary)
    except Exception as e:
        return jsonify({"error": f"Failed to get security summary: {e}"}), 500

@app.post("/security/block-ip")
@require_permission("admin")
@validate_json_input(required_fields=['ip'], optional_fields=['duration', 'reason'])
def block_ip():
    """Block an IP address"""
    try:
        data = request.json
        ip = data['ip']
        duration = data.get('duration', 3600)  # 1 hour default
        reason = data.get('reason', 'Manual block')

        # Validate IP format
        try:
            ipaddress.ip_address(ip)
        except ValueError:
            return jsonify({"error": "Invalid IP address format"}), 400

        security_monitor = get_security_monitor()
        security_monitor.rate_limiter.block_ip(ip, duration)

        return jsonify({
            "ok": True,
            "message": f"IP {ip} blocked for {duration} seconds",
            "reason": reason
        })
    except Exception as e:
        return jsonify({"error": f"Failed to block IP: {e}"}), 500

# --- Conversation Context Endpoints ---
@app.get("/conversation/<contact>/summary")
@require_user_auth
def get_conversation_summary(contact):
    """Get conversation summary for a contact"""
    try:
        context_manager = get_context_manager()
        summary = context_manager.get_conversation_summary(contact)
        return jsonify({"contact": contact, "summary": summary})
    except Exception as e:
        return jsonify({"error": f"Failed to get conversation summary: {e}"}), 500

@app.get("/conversation/<contact>/analytics")
@require_user_auth
def get_conversation_analytics(contact):
    """Get conversation analytics for a contact"""
    try:
        context_manager = get_context_manager()
        analytics = context_manager.analyze_conversation_patterns(contact)
        return jsonify({"contact": contact, "analytics": analytics})
    except Exception as e:
        return jsonify({"error": f"Failed to get conversation analytics: {e}"}), 500

@app.post("/personality")
@require_permission("profile_write")
@validate_json_input(required_fields=['name'], optional_fields=[
    'base_traits', 'communication_style', 'response_length_preference',
    'emoji_usage', 'topics_of_interest', 'topics_to_avoid', 'custom_phrases'
])
def create_personality():
    """Create or update personality profile"""
    try:
        from ai.conversation_context import PersonalityProfile

        data = request.json
        personality = PersonalityProfile(
            name=data['name'],
            base_traits=data.get('base_traits', ['helpful', 'friendly']),
            communication_style=data.get('communication_style', 'casual'),
            response_length_preference=data.get('response_length_preference', 'brief'),
            emoji_usage=data.get('emoji_usage', 'minimal'),
            topics_of_interest=data.get('topics_of_interest', []),
            topics_to_avoid=data.get('topics_to_avoid', []),
            custom_phrases=data.get('custom_phrases', []),
            relationship_context=data.get('relationship_context', {})
        )

        context_manager = get_context_manager()
        context_manager.save_personality(personality)

        return jsonify({"ok": True, "personality": data['name']})
    except Exception as e:
        return jsonify({"error": f"Failed to create personality: {e}"}), 500

@app.get("/personality/<name>")
@require_user_auth
def get_personality(name):
    """Get personality profile"""
    try:
        context_manager = get_context_manager()
        personality = context_manager.load_personality(name)

        if personality:
            from dataclasses import asdict
            return jsonify({"personality": asdict(personality)})
        else:
            return jsonify({"error": "Personality not found"}), 404
    except Exception as e:
        return jsonify({"error": f"Failed to get personality: {e}"}), 500

# --- Multi-Model AI Endpoints ---
@app.get("/ai/models")
@require_permission("admin")
def get_available_models():
    """Get available AI models and their performance"""
    try:
        multi_model_manager = get_multi_model_manager()
        performance_report = multi_model_manager.get_model_performance_report()

        models_info = {}
        for model_key, model_config in multi_model_manager.models.items():
            models_info[model_key] = {
                "provider": model_config.provider.value,
                "model_name": model_config.model_name,
                "capabilities": [cap.value for cap in model_config.capabilities],
                "max_tokens": model_config.max_tokens,
                "cost_per_token": model_config.cost_per_token,
                "reliability_score": model_config.reliability_score,
                "priority": model_config.priority,
                "performance": performance_report.get(model_key, {})
            }

        return jsonify({
            "models": models_info,
            "total_models": len(models_info)
        })
    except Exception as e:
        return jsonify({"error": f"Failed to get models: {e}"}), 500

@app.post("/ai/generate")
@require_permission("reply")
@validate_json_input(required_fields=['prompt'], optional_fields=['capability', 'options'])
async def generate_ai_response():
    """Generate response using multi-model AI system"""
    try:
        data = request.json
        prompt = data['prompt']
        capability = ModelCapability(data.get('capability', 'text_generation'))
        options = data.get('options', {})

        multi_model_manager = get_multi_model_manager()
        response = await multi_model_manager.generate_response(prompt, capability, options)

        if response:
            return jsonify({
                "success": True,
                "response": response.content,
                "provider": response.provider.value,
                "model": response.model_name,
                "tokens_used": response.tokens_used,
                "cost": response.cost,
                "confidence": response.confidence
            })
        else:
            return jsonify({"error": "No suitable model available"}), 503

    except Exception as e:
        return jsonify({"error": f"Failed to generate response: {e}"}), 500

# --- Adaptive Learning Endpoints ---
@app.post("/learning/feedback")
@require_user_auth
@validate_json_input(required_fields=['input_text', 'response_text'],
                    optional_fields=['feedback_score', 'contact', 'success_metrics'])
def submit_learning_feedback():
    """Submit feedback for adaptive learning"""
    try:
        data = request.json
        learning_system = get_adaptive_learning_system()

        learning_system.add_learning_example(
            input_text=data['input_text'],
            response_text=data['response_text'],
            user_feedback=data.get('feedback_score'),
            contact=data.get('contact', 'Unknown'),
            success_metrics=data.get('success_metrics', {})
        )

        return jsonify({"ok": True, "message": "Feedback recorded"})
    except Exception as e:
        return jsonify({"error": f"Failed to record feedback: {e}"}), 500

@app.get("/learning/stats")
@require_permission("admin")
def get_learning_stats():
    """Get adaptive learning statistics"""
    try:
        learning_system = get_adaptive_learning_system()
        stats = learning_system.get_learning_stats()
        return jsonify(stats)
    except Exception as e:
        return jsonify({"error": f"Failed to get learning stats: {e}"}), 500

@app.get("/learning/suggestion")
@require_user_auth
def get_response_suggestion():
    """Get AI response suggestion based on learned patterns"""
    try:
        input_text = request.args.get('input_text', '')
        contact = request.args.get('contact', 'Unknown')

        if not input_text:
            return jsonify({"error": "input_text parameter required"}), 400

        learning_system = get_adaptive_learning_system()
        suggestion = learning_system.get_response_suggestion(input_text, contact=contact)

        return jsonify({
            "suggestion": suggestion,
            "has_suggestion": suggestion is not None
        })
    except Exception as e:
        return jsonify({"error": f"Failed to get suggestion: {e}"}), 500

# --- Webhook Integration Endpoints ---
@app.post("/webhooks/register")
@require_permission("admin")
@validate_json_input(required_fields=['name', 'platform', 'endpoint_url'],
                    optional_fields=['secret_key', 'headers', 'retry_attempts'])
def register_webhook():
    """Register a new webhook integration"""
    try:
        data = request.json
        webhook_manager = get_webhook_manager()

        webhook_id = webhook_manager.register_webhook(
            name=data['name'],
            integration_type=IntegrationType.WEBHOOK_INCOMING,
            platform=MessagePlatform(data['platform']),
            endpoint_url=data['endpoint_url'],
            secret_key=data.get('secret_key'),
            headers=data.get('headers', {}),
            retry_attempts=data.get('retry_attempts', 3)
        )

        return jsonify({
            "ok": True,
            "webhook_id": webhook_id,
            "message": "Webhook registered successfully"
        })
    except Exception as e:
        return jsonify({"error": f"Failed to register webhook: {e}"}), 500

@app.post("/webhooks/<webhook_id>/process")
@require_security_check(check_rate_limit=True, limit_type='webhook')
async def process_webhook(webhook_id):
    """Process incoming webhook"""
    try:
        webhook_manager = get_webhook_manager()
        payload = request.json or {}
        headers = dict(request.headers)
        source_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)

        response = await webhook_manager.process_incoming_webhook(
            webhook_id, payload, headers, source_ip
        )

        return jsonify(response.response_data), response.status_code

    except Exception as e:
        return jsonify({"error": f"Failed to process webhook: {e}"}), 500

@app.get("/webhooks/stats")
@require_permission("admin")
def get_webhook_stats():
    """Get webhook statistics"""
    try:
        webhook_manager = get_webhook_manager()
        webhook_id = request.args.get('webhook_id')
        stats = webhook_manager.get_webhook_stats(webhook_id)
        return jsonify(stats)
    except Exception as e:
        return jsonify({"error": f"Failed to get webhook stats: {e}"}), 500

# --- Performance and Caching Endpoints ---
@app.get("/cache/stats")
@require_permission("admin")
def get_cache_stats():
    """Get cache performance statistics"""
    try:
        cache_manager = get_cache_manager()
        namespace = request.args.get('namespace')
        stats = cache_manager.get_performance_stats(namespace)
        return jsonify(stats)
    except Exception as e:
        return jsonify({"error": f"Failed to get cache stats: {e}"}), 500

@app.post("/cache/clear")
@require_permission("admin")
@validate_json_input(optional_fields=['namespace'])
def clear_cache():
    """Clear cache entries"""
    try:
        data = request.json or {}
        cache_manager = get_cache_manager()
        namespace = data.get('namespace')

        if namespace:
            cache_manager.clear_namespace(namespace)
            message = f"Cleared cache for namespace: {namespace}"
        else:
            # Clear all caches
            cache_manager.memory_cache.clear()
            message = "Cleared all cache entries"

        return jsonify({"ok": True, "message": message})
    except Exception as e:
        return jsonify({"error": f"Failed to clear cache: {e}"}), 500

# --- Advanced Analytics Endpoints ---
@app.get("/analytics/predictive")
@require_permission("admin")
def get_predictive_analytics():
    """Get predictive analytics and forecasting"""
    try:
        system_monitor = get_system_monitor()
        analytics = system_monitor.get_predictive_analytics()
        return jsonify(analytics)
    except Exception as e:
        return jsonify({"error": f"Failed to get predictive analytics: {e}"}), 500

@app.get("/analytics/advanced")
@require_permission("admin")
def get_advanced_analytics():
    """Get advanced usage analytics"""
    try:
        days = request.args.get('days', 7, type=int)
        system_monitor = get_system_monitor()
        analytics = system_monitor.get_advanced_usage_analytics(days)
        return jsonify(analytics)
    except Exception as e:
        return jsonify({"error": f"Failed to get advanced analytics: {e}"}), 500

# --- Enhanced Security Endpoints ---
@app.get("/security/advanced")
@require_permission("admin")
def get_advanced_security_analytics():
    """Get advanced security analytics"""
    try:
        security_monitor = get_security_monitor()
        analytics = security_monitor.get_advanced_security_analytics()
        return jsonify(analytics)
    except Exception as e:
        return jsonify({"error": f"Failed to get security analytics: {e}"}), 500

# --- Enhanced User Management Endpoints ---
@app.get("/users/analytics")
@require_permission("admin")
def get_user_analytics():
    """Get comprehensive user analytics"""
    try:
        user_manager = get_user_manager()
        analytics = user_manager.get_user_analytics()
        return jsonify(analytics)
    except Exception as e:
        return jsonify({"error": f"Failed to get user analytics: {e}"}), 500

@app.get("/users/activity")
@require_permission("admin")
def get_user_activity_report():
    """Get user activity report"""
    try:
        user_id = request.args.get('user_id')
        days = request.args.get('days', 30, type=int)

        user_manager = get_user_manager()
        report = user_manager.get_user_activity_report(user_id, days)
        return jsonify(report)
    except Exception as e:
        return jsonify({"error": f"Failed to get activity report: {e}"}), 500

@app.get("/users/audit")
@require_permission("admin")
def get_security_audit_log():
    """Get security audit log"""
    try:
        days = request.args.get('days', 7, type=int)
        user_manager = get_user_manager()
        audit_log = user_manager.get_security_audit_log(days)
        return jsonify(audit_log)
    except Exception as e:
        return jsonify({"error": f"Failed to get audit log: {e}"}), 500

# --- Learning System Endpoints ---
@app.get("/learning/recommendations")
@require_user_auth
def get_personalized_recommendations():
    """Get personalized response recommendations"""
    try:
        contact = request.args.get('contact', 'Unknown')
        input_text = request.args.get('input_text', '')

        learning_system = get_adaptive_learning_system()
        recommendations = learning_system.get_personalized_recommendations(contact, input_text)
        return jsonify(recommendations)
    except Exception as e:
        return jsonify({"error": f"Failed to get recommendations: {e}"}), 500

# --- Cache Analytics Endpoints ---
@app.get("/cache/analytics")
@require_permission("admin")
def get_cache_analytics():
    """Get detailed cache analytics"""
    try:
        hours = request.args.get('hours', 24, type=int)
        cache_manager = get_cache_manager()
        analytics = cache_manager.get_cache_analytics(hours)
        return jsonify(analytics)
    except Exception as e:
        return jsonify({"error": f"Failed to get cache analytics: {e}"}), 500

@app.get("/cache/recommendations")
@require_permission("admin")
def get_cache_recommendations():
    """Get cache optimization recommendations"""
    try:
        cache_manager = get_cache_manager()
        recommendations = cache_manager.get_cache_recommendations()
        return jsonify(recommendations)
    except Exception as e:
        return jsonify({"error": f"Failed to get cache recommendations: {e}"}), 500

# --- Webhook Health Endpoints ---
@app.get("/webhooks/health")
@require_permission("admin")
def get_webhook_health():
    """Get webhook health report"""
    try:
        webhook_manager = get_webhook_manager()
        health_report = webhook_manager.get_webhook_health_report()
        return jsonify(health_report)
    except Exception as e:
        return jsonify({"error": f"Failed to get webhook health: {e}"}), 500

@app.get("/users/login-ui")
def user_login_ui():
    """User login interface"""
    html = """
<!doctype html>
<html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'>
<title>User Login - SMS AI</title>
<style>
body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;margin:32px;line-height:1.6;max-width:400px}
.card{border:1px solid #ddd;padding:20px;margin:16px 0;border-radius:8px;background:#f9f9f9}
input{width:100%;padding:8px;margin:4px 0;border:1px solid #ddd;border-radius:4px;box-sizing:border-box}
button{width:100%;padding:10px;margin:8px 0;background:#007bff;color:white;border:none;border-radius:4px;cursor:pointer}
button:hover{background:#0056b3}
.status{padding:10px;margin:10px 0;border-radius:4px}
.success{background:#d4edda;color:#155724;border:1px solid #c3e6cb}
.error{background:#f8d7da;color:#721c24;border:1px solid #f5c6cb}
label{display:block;margin-top:10px;font-weight:bold}
</style>
</head><body>
<h1>🔐 User Login</h1>

<div class="card">
    <h2>Login to SMS AI</h2>
    <label>Username:</label>
    <input type="text" id="username" placeholder="Enter username">

    <label>Password:</label>
    <input type="password" id="password" placeholder="Enter password">

    <label>Token Description (optional):</label>
    <input type="text" id="description" placeholder="e.g., 'My Phone App'">

    <label>Token Expires (days):</label>
    <input type="number" id="expires" value="30" min="1" max="365">

    <button onclick="login()">Login & Get API Token</button>
</div>

<div id="result" class="status" style="display:none"></div>

<script>
async function login() {
    const username = document.getElementById('username').value.trim();
    const password = document.getElementById('password').value.trim();
    const description = document.getElementById('description').value.trim();
    const expires_days = parseInt(document.getElementById('expires').value) || 30;

    if (!username || !password) {
        showResult('Please enter username and password', 'error');
        return;
    }

    try {
        const r = await fetch('/users/login', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                username: username,
                password: password,
                description: description,
                expires_days: expires_days
            })
        });

        const data = await r.json();

        if (r.ok && data.ok) {
            localStorage.setItem('sms_ai_token', data.token);
            localStorage.setItem('sms_ai_user', JSON.stringify(data.user));

            showResult(`Login successful! Your API token: ${data.token}`, 'success');

            setTimeout(() => {
                window.location.href = '/users/dashboard';
            }, 2000);
        } else {
            showResult('Login failed: ' + (data.error || 'Unknown error'), 'error');
        }
    } catch (e) {
        showResult('Error: ' + e.message, 'error');
    }
}

function showResult(message, type) {
    const result = document.getElementById('result');
    result.textContent = message;
    result.className = 'status ' + type;
    result.style.display = 'block';
}
</script>
</body></html>
"""
    return Response(html, mimetype="text/html; charset=utf-8")

@app.get("/users/dashboard")
def user_dashboard():
    """User dashboard interface"""
    html = """
<!doctype html>
<html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'>
<title>User Dashboard - SMS AI</title>
<style>
body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;margin:32px;line-height:1.6;max-width:800px}
.card{border:1px solid #ddd;padding:20px;margin:16px 0;border-radius:8px;background:#f9f9f9}
.btn{display:inline-block;padding:8px 12px;margin:4px;background:#007bff;color:white;text-decoration:none;border-radius:4px;border:none;cursor:pointer}
.btn:hover{background:#0056b3}
.btn-danger{background:#dc3545}
.btn-danger:hover{background:#c82333}
.status{padding:10px;margin:10px 0;border-radius:4px}
.success{background:#d4edda;color:#155724;border:1px solid #c3e6cb}
.error{background:#f8d7da;color:#721c24;border:1px solid #f5c6cb}
.info{background:#d1ecf1;color:#0c5460;border:1px solid #bee5eb}
table{width:100%;border-collapse:collapse;margin:10px 0}
th,td{padding:8px;text-align:left;border-bottom:1px solid #ddd}
th{background:#f8f9fa}
code{background:#f8f9fa;padding:2px 4px;border-radius:3px;font-family:monospace}
</style>
</head><body>
<h1>👤 User Dashboard</h1>

<div id="userInfo" class="card">
    <h2>Loading...</h2>
</div>

<div class="card">
    <h2>🔑 API Token Usage</h2>
    <p>Use your API token to access SMS AI endpoints:</p>
    <code>curl -H "X-API-Token: YOUR_TOKEN" http://127.0.0.1:8081/reply</code>
    <p>Or in the Authorization header:</p>
    <code>curl -H "Authorization: Bearer YOUR_TOKEN" http://127.0.0.1:8081/reply</code>
</div>

<div class="card">
    <h2>🎯 Test API Access</h2>
    <p>Test your API token with a sample message:</p>
    <input type="text" id="testMessage" placeholder="Enter test message" style="width:70%;padding:8px;margin:4px">
    <button class="btn" onclick="testAPI()">Test Reply</button>
    <div id="testResult" style="margin-top:10px"></div>
</div>

<div class="card">
    <h2>🔐 Your API Tokens</h2>
    <div id="tokensList">Loading tokens...</div>
    <button class="btn" onclick="refreshTokens()">Refresh Tokens</button>
</div>

<script>
let currentToken = localStorage.getItem('sms_ai_token');

async function loadUserInfo() {
    if (!currentToken) {
        document.getElementById('userInfo').innerHTML = '<h2>❌ Not Logged In</h2><p><a href="/users/login-ui">Please login first</a></p>';
        return;
    }

    try {
        const r = await fetch('/users/me', {
            headers: {'X-API-Token': currentToken}
        });

        if (r.ok) {
            const user = await r.json();
            document.getElementById('userInfo').innerHTML = `
                <h2>👤 ${user.username}</h2>
                <p><strong>Role:</strong> ${user.role}</p>
                <p><strong>Email:</strong> ${user.email}</p>
                <p><strong>Total Requests:</strong> ${user.usage_stats.total_requests}</p>
                <p><strong>Last Request:</strong> ${user.usage_stats.last_request || 'Never'}</p>
                <p><strong>Token Usage:</strong> ${user.token_info.usage_count} times</p>
                <p><strong>Token Expires:</strong> ${new Date(user.token_info.expires_at).toLocaleDateString()}</p>
            `;
        } else {
            document.getElementById('userInfo').innerHTML = '<h2>❌ Invalid Token</h2><p><a href="/users/login-ui">Please login again</a></p>';
        }
    } catch (e) {
        document.getElementById('userInfo').innerHTML = '<h2>❌ Error</h2><p>Failed to load user info</p>';
    }
}

async function testAPI() {
    const message = document.getElementById('testMessage').value.trim();
    if (!message) {
        document.getElementById('testResult').innerHTML = '<div class="status error">Please enter a test message</div>';
        return;
    }

    try {
        const r = await fetch('/reply', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-API-Token': currentToken
            },
            body: JSON.stringify({
                incoming: message,
                contact: 'TestUser'
            })
        });

        const data = await r.json();

        if (r.ok) {
            document.getElementById('testResult').innerHTML = `
                <div class="status success">
                    <strong>AI Response:</strong> "${data.draft}"<br>
                    <strong>Analysis:</strong> ${data.analysis.sentiment} sentiment, ${data.analysis.intent} intent
                </div>
            `;
        } else {
            document.getElementById('testResult').innerHTML = `<div class="status error">Error: ${data.error || 'Unknown error'}</div>`;
        }
    } catch (e) {
        document.getElementById('testResult').innerHTML = `<div class="status error">Error: ${e.message}</div>`;
    }
}

async function refreshTokens() {
    try {
        const r = await fetch('/users/tokens', {
            headers: {'X-API-Token': currentToken}
        });

        if (r.ok) {
            const data = await r.json();
            let html = '<table><tr><th>Token</th><th>Description</th><th>Created</th><th>Usage</th><th>Actions</th></tr>';

            data.tokens.forEach(token => {
                html += `<tr>
                    <td><code>${token.token_preview}</code></td>
                    <td>${token.description || 'No description'}</td>
                    <td>${new Date(token.created_at).toLocaleDateString()}</td>
                    <td>${token.usage_count} times</td>
                    <td><button class="btn btn-danger" onclick="revokeToken('${token.token_preview}')">Revoke</button></td>
                </tr>`;
            });

            html += '</table>';
            document.getElementById('tokensList').innerHTML = html;
        } else {
            document.getElementById('tokensList').innerHTML = '<div class="status error">Failed to load tokens</div>';
        }
    } catch (e) {
        document.getElementById('tokensList').innerHTML = '<div class="status error">Error loading tokens</div>';
    }
}

loadUserInfo();
refreshTokens();
</script>
</body></html>
"""
    return Response(html, mimetype="text/html; charset=utf-8")

if __name__ == "__main__":
    # Validate configuration before starting server
    try:
        from utils.config_validator import validate_environment
        if not validate_environment():
            print("❌ Configuration validation failed. Server startup aborted.")
            exit(1)
        print("✅ Configuration validation passed. Starting server...")
    except ImportError as e:
        print(f"⚠️  Configuration validator not available: {e}")
        print("Starting server without validation...")

    app.run(host="0.0.0.0", port=8081)
