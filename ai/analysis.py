import json
import re
from typing import Dict, Any, Optional


def _heuristic_analysis(incoming: str) -> Dict[str, Any]:
    s = incoming.lower()
    toxicity = int(any(w in s for w in ["stupid", "idiot", "narcissist", "hate", "die"]))
    urgent = int(any(w in s for w in ["urgent", "now", "asap", "emergency", "help"]))
    short = len(incoming.strip()) < 10
    question = int("?" in incoming)
    sentiment = (
        "negative" if any(w in s for w in ["angry", "upset", "annoyed", "hate", "mad"]) else
        "positive" if any(w in s for w in ["love", "thanks", "appreciate", "yay"]) else
        "neutral"
    )
    intent = (
        "setup_call" if any(w in s for w in ["call", "phone", "ring"]) else
        "make_plan" if any(w in s for w in ["meet", "later", "when", "time"]) else
        "clarify" if question else
        "acknowledge"
    )
    boundary_triggers = [w for w in ["accuse", "blame", "gaslight", "cheat", "narcissist"] if w in s]
    return {
        "sentiment": sentiment,
        "intent": intent,
        "toxicity": toxicity,
        "urgent": urgent,
        "short": short,
        "boundary_triggers": boundary_triggers,
    }


def parse_json_safely(text: str) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(text)
    except Exception:
        # Try to extract JSON substring if wrapped
        m = re.search(r"\{[\s\S]*\}", text)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                return None
        return None


def build_analysis_prompt(incoming: str, contact: str, profile: Dict[str, Any]) -> str:
    return f'''
You are a conversational analyst. Analyze the incoming message and return a compact JSON object only, no extra text.

Fields: sentiment(one of positive,neutral,negative), intent(one of acknowledge,clarify,make_plan,setup_call,other),
toxicity(0-2), urgent(0/1), short(0/1), emotions(list), boundary_triggers(list)

Incoming from {contact}:
"""{incoming}"""

Return JSON only.
'''


def analyze(incoming: str, contact: str, profile: Dict[str, Any], call_ollama_fn) -> Dict[str, Any]:
    """Analyze incoming message combining heuristics and optional LLM analysis."""
    if not incoming or not isinstance(incoming, str):
        return {"sentiment": "neutral", "intent": "acknowledge", "toxicity": 0, "urgent": 0, "short": True, "boundary_triggers": [], "emotions": []}
    
    # Start with heuristics
    base = _heuristic_analysis(incoming)
    
    # Optional LLM analysis overlay
    if call_ollama_fn:
        try:
            prompt = build_analysis_prompt(incoming, contact, profile)
            raw = call_ollama_fn(prompt, options={"temperature": 0.2})
            js = parse_json_safely(raw)
            if isinstance(js, dict):
                base.update({k: v for k, v in js.items() if k in base or k in ("emotions",)})
        except (ValueError, TypeError, KeyError) as e:
            # Log but continue with heuristic analysis
            print(f"LLM analysis failed: {e}")
        except Exception as e:
            # Catch-all for network/timeout errors
            print(f"Unexpected error in LLM analysis: {e}")
    
    # Ensure defaults
    base.setdefault("emotions", [])
    return base
