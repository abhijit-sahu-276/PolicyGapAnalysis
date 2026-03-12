import json
from llm_engine import safe_generate, one_line

CSF_FUNCTIONS = {
    "GV": "Govern",
    "ID": "Identify",
    "PR": "Protect",
    "DE": "Detect",
    "RS": "Respond",
    "RC": "Recover",
}


def _function_from_clause(clause):
    prefix = clause.split(".", 1)[0] if clause else ""
    return CSF_FUNCTIONS.get(prefix, "Identify")


def _priority_from_severity(sev):
    sev = (sev or "low").lower()
    if sev == "high":
        return "High"
    if sev == "med":
        return "Med"
    return "Low"


def _gap_to_action(gap):
    text = (gap.get("gap") or "").strip()
    if not text:
        clause = (gap.get("clause") or "").strip()
        return f"Address control {clause}".strip()
    lower = text.lower()
    if lower.startswith("no " ):
        text = "Define " + text[3:]
    elif lower.startswith("missing " ):
        text = "Implement " + text[8:]
    elif lower.startswith("lack of " ):
        text = "Establish " + text[8:]
    if text and text[0].islower():
        text = text[0].upper() + text[1:]
    return text


def _fallback_roadmap(gaps):
    if not gaps:
        return "- [Identify] Maintain scheduled policy reviews and monitoring (Priority: Low)"
    items = []
    for g in gaps[:10]:
        func = _function_from_clause(g.get("clause", ""))
        priority = _priority_from_severity(g.get("severity", "low"))
        action = _gap_to_action(g)
        items.append(f"- [{func}] {action} (Priority: {priority})")
    return "\n".join(items)


def _build_prompt(domain, reference_text, policy_summary, gaps_json):
    ref = one_line(reference_text, max_words=900)
    summary = one_line(policy_summary, max_words=200)
    lines = [
        f"You create an improvement roadmap for domain: {domain}.",
        f"Reference (authoritative): {ref}",
        f"Policy summary: {summary}",
        f"Gaps JSON: {gaps_json}",
        "Use only reference text. No new standards.",
        "Output bullet list: '- [CSF] Action (Priority: High|Med|Low)'.",
        "If no gaps, focus on maintenance and monitoring.",
        "Return bullets only.",
    ]
    return "\n".join(lines)


def generate_roadmap(policy_text, reference_text, gaps, domain):
    gaps_json = json.dumps(gaps[:50], ensure_ascii=False)
    policy_summary = policy_text
    prompt = _build_prompt(domain, reference_text, policy_summary, gaps_json)
    response = safe_generate(prompt, max_tokens=256)
    if response:
        return response
    return _fallback_roadmap(gaps)
