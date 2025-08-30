from typing import Dict, List, Any


def summarize_memory(contact: str, items: List[Dict[str, Any]], call_ollama_fn=None) -> Dict[str, Any]:
    """Summarize conversation memory for a contact with both heuristic and LLM analysis."""
    if not isinstance(contact, str):
        contact = str(contact) if contact else "Unknown"
    
    if not isinstance(items, list):
        items = []
    
    # Simple stats
    goals = [x.get("goal") for x in items if isinstance(x, dict) and x.get("goal")]
    goal_counts: Dict[str, int] = {}
    for g in goals:
        if isinstance(g, str):
            goal_counts[g] = goal_counts.get(g, 0) + 1

    # Heuristic fallback summary
    summary = ""
    if not items:
        summary = f"No recent history for {contact}."
    else:
        try:
            last = items[-1] if isinstance(items[-1], dict) else {}
            last_inc = (last.get("incoming") or "").strip()[:60]
            last_draft = (last.get("draft") or last.get("final") or "").strip()[:60]
            common_goal = max(goal_counts, key=goal_counts.get) if goal_counts else "acknowledge_and_close"
            summary = (
                f"Recent goal trend: {common_goal}. Last incoming: '{last_inc}'. "
                f"Last reply: '{last_draft}'."
            )
        except (IndexError, AttributeError, ValueError):
            summary = f"Limited history available for {contact}."

    # If LLM available, try a short neutral summary (<= 2 sentences)
    if call_ollama_fn and items:
        try:
            lines = []
            for it in items[-5:]:
                if not isinstance(it, dict):
                    continue
                inc = str(it.get("incoming") or "").replace("\n", " ")[:100]
                rep = str(it.get("final") or it.get("draft") or "").replace("\n", " ")[:100]
                g = str(it.get("goal") or "")
                if inc or rep:
                    lines.append(f"- goal={g} incoming={inc} reply={rep}")
            
            if lines:
                prompt = (
                    "Summarize this chat context in 2 short, neutral sentences focusing on progress toward goals.\n"
                    + "\n".join(lines)
                )
                model_sum = call_ollama_fn(prompt, options={"temperature": 0.2, "num_predict": 80})
                if model_sum and isinstance(model_sum, str):
                    summary = model_sum.strip()
        except (ValueError, TypeError, KeyError) as e:
            print(f"LLM summary failed: {e}")
        except Exception as e:
            print(f"Unexpected error in memory summarization: {e}")

    return {"summary": summary, "goal_counts": goal_counts}

