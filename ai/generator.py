from typing import Dict, Any


def build_reply_prompt(incoming: str, contact: str, profile: Dict[str, Any], analysis: Dict[str, Any]) -> str:
    style = profile.get("style_rules", "Short, blunt, respectful. Max 200 chars.")
    banned = ", ".join(profile.get("banned_words", [])) or "none"
    preferred = "; ".join(profile.get("preferred_phrases", [])) or "none"

    goal = analysis.get('goal') or 'acknowledge_and_close'
    memory = analysis.get('memory') or []
    recent = "\n".join(
        [
            (f"- incoming: {m.get('incoming')}" if m.get('incoming') else "") +
            (f"\n  draft: {m.get('draft')}" if m.get('draft') else "") +
            (f"\n  final: {m.get('final')}" if m.get('final') else "")
            for m in memory
        ]
    )

    return f'''
You write as Dayle.
Style: {style}
Banned words: {banned}
Preferred phrases: {preferred}

Analysis (use silently):
sentiment={analysis.get('sentiment')}, intent={analysis.get('intent')}, toxicity={analysis.get('toxicity')}, urgent={analysis.get('urgent')}, boundary_triggers={analysis.get('boundary_triggers')}

Goal: {goal}
Recent context (use lightly, optional):
{recent}

Incoming from {contact}:
"""{incoming}"""

Think step by step privately, then output only the FINAL REPLY, nothing else. One message, under 200 characters, that advances the stated Goal without over-explaining. If a simple "ok" works, use it.
'''


def postprocess_reply(text: str, profile: Dict[str, Any]) -> str:
    """Post-process generated reply text according to profile rules."""
    if not isinstance(text, str):
        text = str(text) if text is not None else ""
    
    t = text.strip()
    if not t:
        return "Ok."  # Fallback for empty responses
    
    try:
        max_len = int(profile.get("max_reply_len", 200))
    except (ValueError, TypeError):
        max_len = 200
    
    # Enforce banned words
    banned_words = profile.get("banned_words", [])
    if isinstance(banned_words, list):
        for w in banned_words:
            if w and isinstance(w, str) and w.lower() in t.lower():
                t = t.replace(w, "…")
    
    # Truncate if too long
    if len(t) > max_len:
        t = t[:max_len].rstrip()
        # Ensure we don't cut off mid-word
        if not t.endswith(('.', '!', '?')):
            t += "…"
    
    return t
