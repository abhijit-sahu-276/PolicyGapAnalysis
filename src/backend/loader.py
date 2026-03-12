import os
import re
from PyPDF2 import PdfReader

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
REFERENCE_PATH = os.path.join(
    BASE_DIR, "data", "reference", "cis_nist_policy_template.txt"
)

CONTROL_RE = re.compile(r"([A-Z]{2}\.[A-Z]{2}-\d{2})\s+")
DOMAIN_FILTERS = {
    "ISMS": {
        "functions": {"GV", "ID", "PR", "DE", "RS", "RC"},
        "categories": set(),
        "keywords": [],
    },
    "Data Privacy & Security": {
        "functions": set(),
        "categories": {"PR.DS", "PR.AA", "PR.AT", "ID.AM", "ID.RA", "RS.CO"},
        "keywords": [],
    },
    "Patch Management": {
        "functions": set(),
        "categories": {"PR.PS", "PR.IR", "DE.CM", "ID.AM", "ID.RA"},
        "keywords": [],
    },
    "Risk Management": {
        "functions": set(),
        "categories": {"GV.OC", "GV.RM", "GV.RR", "GV.OV", "GV.PO", "ID.RA", "ID.IM"},
        "keywords": [],
    },
}


def _normalize_text(text):
    return " ".join(text.split())


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


def _clause_parts(clause):
    func = clause.split(".", 1)[0] if clause else ""
    category = clause.split("-", 1)[0] if clause else ""
    return func, category


def _domain_match(control, domain):
    cfg = DOMAIN_FILTERS.get(domain)
    if not cfg:
        return True
    func, category = _clause_parts(control["clause"])
    desc = control["desc"].lower()
    if category in cfg["categories"]:
        return True
    if any(k in desc for k in cfg["keywords"]):
        return True
    return func in cfg["functions"]


def filter_reference_text(reference_text, domain):
    cfg = DOMAIN_FILTERS.get(domain)
    if not cfg:
        return reference_text
    controls = _extract_controls(reference_text)
    if not controls:
        return reference_text
    selected = [c for c in controls if _domain_match(c, domain)]
    if not selected:
        return reference_text
    return "\n".join(f"{c['clause']} {c['desc']}" for c in selected)


def load_reference_text(domain=None):
    with open(REFERENCE_PATH, "r", encoding="utf-8") as f:
        text = f.read()
    text = filter_reference_text(text, domain)
    return _normalize_text(text)


def load_policy_text(file_storage):
    filename = (file_storage.filename or "").lower()
    if filename.endswith(".txt"):
        data = file_storage.read()
        text = data.decode("utf-8", errors="ignore")
        return _normalize_text(text)

    if filename.endswith(".pdf"):
        file_storage.stream.seek(0)
        reader = PdfReader(file_storage.stream)
        parts = []
        for page in reader.pages:
            parts.append(page.extract_text() or "")
        return _normalize_text(" ".join(parts))

    raise ValueError("Unsupported file type. Use PDF or TXT.")
