import json
from llm_engine import safe_generate, one_line


def _word_count(text):
    return len(text.split())


def _build_full_prompt(domain, reference_text, policy_text, gaps_json):
    ref = one_line(reference_text, max_words=900)
    policy = one_line(policy_text, max_words=900)
    lines = [
        f"You revise a policy for domain: {domain}.",
        f"Reference (authoritative): {ref}",
        f"Original policy: {policy}",
        f"Gaps JSON: {gaps_json}",
        "Requirements: add missing provisions and strengthen weak sections.",
        "Use only the reference text. No new standards.",
        "Return revised policy text only.",
        "Keep clear headings and concise language.",
    ]
    return "\n".join(lines)


def _build_addendum_prompt(domain, reference_text, gaps_json):
    ref = one_line(reference_text, max_words=900)
    lines = [
        f"You create a policy addendum for domain: {domain}.",
        f"Reference (authoritative): {ref}",
        f"Gaps JSON: {gaps_json}",
        "Requirements: add missing provisions and strengthen weak sections.",
        "Use only the reference text. No new standards.",
        "Output addendum text only, with headings.",
        "Keep concise.",
        "No preamble.",
    ]
    return "\n".join(lines)


def revise_policy(policy_text, reference_text, gaps, domain):
    gaps_json = json.dumps(gaps[:50], ensure_ascii=False)
    if _word_count(policy_text) <= 900:
        prompt = _build_full_prompt(domain, reference_text, policy_text, gaps_json)
        response = safe_generate(prompt, max_tokens=1024)
        return response if response else policy_text

    prompt = _build_addendum_prompt(domain, reference_text, gaps_json)
    response = safe_generate(prompt, max_tokens=512)
    if response:
        return policy_text + "\n\nPolicy Addendum\n" + response.strip()
    return policy_text
