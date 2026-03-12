import json
import re
from llm_engine import safe_generate, one_line

CONTROL_RE = re.compile(r"([A-Z]{2}\.[A-Z]{2}-\d{2})\s+")
_STOPWORDS = {
    "the", "and", "that", "with", "for", "from", "are", "this", "their",
    "such", "into", "within", "will", "shall", "must", "may", "can", "should",
    "have", "has", "been", "being", "use", "used", "using", "per", "each", "all",
    "any", "not", "only", "other", "than", "also", "including", "between", "through",
    "across", "upon", "without", "as", "of", "to", "in", "on", "by", "or", "is",
    "be", "it", "its", "an", "a",
}
MAX_GAPS = 60


def _tokenize(text):
    return re.findall(r"[a-z0-9]+", text.lower())


def _extract_controls(reference_text):
    flat = " ".join(reference_text.split())
    matches = list(CONTROL_RE.finditer(flat))
    controls = []
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(flat)
        desc = flat[start:end].strip()
        if not desc:
            continue
        for marker in ("\u2022", "NIST Function:", "NIST Cybersecurity Framework:"):
            if marker in desc:
                desc = desc.split(marker, 1)[0].strip()
        desc = re.sub(r"\s+", " ", desc)
        if not desc:
            continue
        controls.append({"clause": m.group(1), "desc": desc})
    return controls


def _keywords(desc):
    tokens = _tokenize(desc)
    return [t for t in tokens if len(t) >= 4 and t not in _STOPWORDS]


def _required_hits(total):
    if total <= 3:
        return 1
    if total <= 8:
        return 2
    return max(3, int(total * 0.25))


def _severity_from_clause(clause):
    prefix = clause.split(".", 1)[0] if clause else ""
    if prefix in ("PR", "DE", "RS", "RC"):
        return "high"
    if prefix in ("GV", "ID"):
        return "med"
    return "med"


def _shorten(text, max_len=160):
    if len(text) <= max_len:
        return text
    return text[: max_len - 3].rstrip() + "..."


def _reference_based_gaps(policy_text, reference_text):
    controls = _extract_controls(reference_text)
    if not controls:
        return []
    policy_terms = set(_tokenize(policy_text))
    gaps = []
    for c in controls:
        keywords = _keywords(c["desc"])
        if not keywords:
            continue
        hits = sum(1 for k in keywords if k in policy_terms)
        required = _required_hits(len(keywords))
        if hits < required:
            gaps.append(
                {
                    "clause": c["clause"],
                    "gap": _shorten(c["desc"]),
                    "severity": _severity_from_clause(c["clause"]),
                    "chunk_index": -1,
                }
            )
    return gaps


def _severity_weight(sev):
    return {"high": 3, "med": 2, "low": 1}.get(sev, 1)



def _has_any(text, terms):
    t = text.lower()
    for term in terms:
        term_l = term.lower()
        pattern = r"\b" + re.escape(term_l) + r"\b"
        if re.search(pattern, t):
            return True
        if " " in term_l and term_l in t:
            return True
    return False


def _sentence_contains_weak_modal(text, keywords):
    t = text.lower().replace("\n", " ")
    for sentence in t.split("."):
        if any(k in sentence for k in keywords) and any(
            m in sentence for m in ("may", "encouraged", "where possible")
        ):
            return True
    return False


def _reference_has(reference_text, key):
    return key.lower() in reference_text.lower()


def _heuristic_gaps(policy_text, reference_text):
    gaps = []
    ref = reference_text.lower()
    ptxt = policy_text.lower()

    checks = [
        {
            "clause": "GV.RM",
            "gap": "No defined risk appetite or risk tolerance statement.",
            "severity": "high",
            "terms": ["risk appetite", "risk tolerance"],
        },
        {
            "clause": "GV.RR",
            "gap": "No clear accountability structure or named security roles.",
            "severity": "med",
            "terms": ["ciso", "security officer", "accountability", "roles and responsibilities"],
        },
        {
            "clause": "GV.OV",
            "gap": "No cybersecurity oversight mechanism (e.g., governance/board review).",
            "severity": "med",
            "terms": ["oversight", "governance committee", "board", "executive oversight"],
        },
        {
            "clause": "ID.AM",
            "gap": "No asset inventory or asset register requirement.",
            "severity": "high",
            "terms": ["asset inventory", "asset register", "inventory of assets"],
        },
        {
            "clause": "ID.RA",
            "gap": "No defined risk assessment methodology.",
            "severity": "high",
            "terms": ["risk assessment", "risk analysis", "risk register"],
        },
        {
            "clause": "PR.DS",
            "gap": "No data classification levels or handling rules.",
            "severity": "med",
            "terms": ["data classification", "classification levels", "classify data"],
        },
        {
            "clause": "PR.AA",
            "gap": "No strong access control model (e.g., least privilege/MFA/RBAC).",
            "severity": "high",
            "terms": ["least privilege", "mfa", "multi-factor", "role-based", "rbac"],
            "base_terms": ["access control", "access to", "password"],
        },
        {
            "clause": "PR.DS",
            "gap": "No explicit encryption requirements for data at rest or in transit.",
            "severity": "high",
            "terms": ["encrypt", "encryption", "at rest", "in transit"],
        },
        {
            "clause": "PR.AT",
            "gap": "No defined security awareness training structure.",
            "severity": "med",
            "terms": ["security awareness", "awareness training", "training"],
        },
        {
            "clause": "DE.CM",
            "gap": "No monitoring or logging requirements for detection.",
            "severity": "high",
            "terms": ["logging", "log", "continuous monitoring", "security monitoring", "detection"],
        },
        {
            "clause": "RS.MA",
            "gap": "No incident response lifecycle defined.",
            "severity": "high",
            "terms": ["incident response plan", "incident response lifecycle", "containment", "eradication"],
        },
        {
            "clause": "RS.CO",
            "gap": "No escalation or communication plan for incidents.",
            "severity": "med",
            "terms": ["escalation", "communication plan", "notify", "reporting chain"],
        },
        {
            "clause": "RC.RP",
            "gap": "No backup, recovery, or restoration process.",
            "severity": "high",
            "terms": ["backup", "recovery", "restore", "restoration", "disaster recovery"],
        },
    ]

    for item in checks:
        if not _reference_has(ref, item["clause"].lower()):
            continue

        if "base_terms" in item:
            has_base = _has_any(ptxt, item["base_terms"])
            has_strong = _has_any(ptxt, item["terms"])
            if not has_strong:
                gaps.append(
                    {
                        "clause": item["clause"],
                        "gap": item["gap"],
                        "severity": item["severity"],
                        "chunk_index": -1,
                    }
                )
            elif has_base and _sentence_contains_weak_modal(policy_text, ["access control", "password"]):
                gaps.append(
                    {
                        "clause": item["clause"],
                        "gap": "Access control is described as optional or weak.",
                        "severity": "med",
                        "chunk_index": -1,
                    }
                )
            continue

        if item["clause"] == "PR.AT":
            if not _has_any(ptxt, item["terms"]) or _sentence_contains_weak_modal(
                policy_text, ["training", "awareness"]
            ):
                gaps.append(
                    {
                        "clause": item["clause"],
                        "gap": item["gap"],
                        "severity": item["severity"],
                        "chunk_index": -1,
                    }
                )
            continue

        if item["clause"] == "PR.DS" and "encryption" in item["gap"].lower():
            if not _has_any(ptxt, item["terms"]) or _sentence_contains_weak_modal(
                policy_text, ["encrypt", "encryption"]
            ):
                gaps.append(
                    {
                        "clause": item["clause"],
                        "gap": item["gap"],
                        "severity": item["severity"],
                        "chunk_index": -1,
                    }
                )
            continue

        if not _has_any(ptxt, item["terms"]):
            gaps.append(
                {
                    "clause": item["clause"],
                    "gap": item["gap"],
                    "severity": item["severity"],
                    "chunk_index": -1,
                }
            )

    return gaps


def _parse_json_array(text):
    if not text:
        return []
    try:
        data = json.loads(text)
        return data if isinstance(data, list) else []
    except Exception:
        pass

    start = text.find("[")
    end = text.rfind("]")
    if start != -1 and end != -1 and end > start:
        try:
            data = json.loads(text[start : end + 1])
            return data if isinstance(data, list) else []
        except Exception:
            return []
    return []


def _normalize_gap(item, chunk_index):
    if not isinstance(item, dict):
        return None
    clause = str(item.get("clause", "") or item.get("control", "")).strip()
    gap = str(item.get("gap", "") or item.get("issue", "")).strip()
    severity = str(item.get("severity", "low")).strip().lower()
    if severity == "medium":
        severity = "med"
    if severity not in ("low", "med", "high"):
        severity = "low"
    if not clause and not gap:
        return None
    return {
        "clause": clause,
        "gap": gap,
        "severity": severity,
        "chunk_index": chunk_index,
    }


def _build_prompt(domain, reference_text, chunk_text):
    ref = one_line(reference_text, max_words=900)
    chunk = one_line(chunk_text, max_words=500)
    lines = [
        f"You are a policy gap checker for domain: {domain}.",
        f"Reference (authoritative): {ref}",
        f"Policy chunk: {chunk}",
        "Task: list missing or weak controls vs the reference.",
        "Use only the reference text. No new standards.",
        "Output JSON array of objects with fields clause, gap, severity.",
        "Severity must be low, med, or high.",
        "If none, output [] only.",
    ]
    return "\n".join(lines)


def analyze_gaps(chunks, reference_text, domain):
    gaps = []
    if not chunks:
        return gaps

    for idx, chunk in enumerate(chunks):
        prompt = _build_prompt(domain, reference_text, chunk)
        response = safe_generate(prompt, max_tokens=256)
        items = _parse_json_array(response)
        for item in items:
            norm = _normalize_gap(item, idx)
            if norm:
                gaps.append(norm)

    full_policy = " ".join(chunks)
    heuristic = _heuristic_gaps(full_policy, reference_text)
    gaps.extend(heuristic)

    ref_based = _reference_based_gaps(full_policy, reference_text)
    gaps.extend(ref_based)

    seen = set()
    deduped = []
    for g in gaps:
        key = (
            g.get("clause", ""),
            g.get("gap", ""),
            g.get("severity", ""),
            g.get("chunk_index", -1),
        )
        if key not in seen:
            seen.add(key)
            deduped.append(g)
    if len(deduped) > MAX_GAPS:
        deduped.sort(key=lambda g: (-_severity_weight(g.get("severity")), g.get("clause", "")))
        deduped = deduped[:MAX_GAPS]
    return deduped
