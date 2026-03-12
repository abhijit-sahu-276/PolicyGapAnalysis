import io
import json
import os
import re
from flask import Flask, request, jsonify, render_template, send_file
from fpdf import FPDF

from loader import load_policy_text, load_reference_text
from chunker import chunk_text
from gap_analyzer import analyze_gaps
from policy_rewriter import revise_policy
from roadmap_generator import generate_roadmap
from llm_engine import get_llm

ALLOWED_DOMAINS = [
    "ISMS",
    "Data Privacy & Security",
    "Patch Management",
    "Risk Management",
]

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
FRONTEND_DIR = os.path.join(BASE_DIR, "src", "frontend")
TEMPLATE_DIR = os.path.join(FRONTEND_DIR, "templates")
STATIC_DIR = os.path.join(FRONTEND_DIR, "static")
OUTPUT_DIR = os.path.join(BASE_DIR, "data", "outputs")

app = Flask(__name__, template_folder=TEMPLATE_DIR, static_folder=STATIC_DIR)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024


def _safe_pdf_text(text):
    if not text:
        return ""
    return text.encode("latin-1", errors="replace").decode("latin-1")

def _wrap_long_words(text, max_chunk=50):
    if not text:
        return ""
    words = []
    for w in text.split(" "):
        if len(w) <= max_chunk:
            words.append(w)
            continue
        parts = [w[i : i + max_chunk] for i in range(0, len(w), max_chunk)]
        words.extend(parts)
    return " ".join(words)


def _make_pdf_bytes(title, body_text):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", size=16)
    if title:
        pdf.multi_cell(0, 10, _safe_pdf_text(title))
        pdf.ln(2)
    pdf.set_font("Helvetica", size=12)
    for line in (body_text or "").splitlines():
        safe_line = _safe_pdf_text(line).replace("\t", " ")
        safe_line = _wrap_long_words(safe_line, max_chunk=50)
        pdf.multi_cell(0, 8, safe_line)
    raw = pdf.output(dest="S")
    if isinstance(raw, (bytes, bytearray)):
        return bytes(raw)
    return raw.encode("latin-1")


def _slugify(value):
    value = re.sub(r"[^a-zA-Z0-9]+", "-", value or "").strip("-")
    return value.lower() or "policy"


def step_select_domain(domain):
    if domain not in ALLOWED_DOMAINS:
        raise ValueError("Invalid domain selection.")
    return domain


def step_policy_intake(file_storage):
    return load_policy_text(file_storage)


def step_load_reference(domain):
    return load_reference_text(domain)


def step_gap_identification(policy_text, reference_text, domain):
    chunks = chunk_text(policy_text, max_words=500)
    return analyze_gaps(chunks, reference_text, domain)


def step_decision(gaps):
    return bool(gaps)


def step_policy_revision(policy_text, reference_text, gaps, domain):
    if not gaps:
        return policy_text
    return revise_policy(policy_text, reference_text, gaps, domain)


def step_review_validation(revised_policy, reference_text, gaps, domain):
    return generate_roadmap(revised_policy, reference_text, gaps, domain)


def write_outputs(domain, gap_found, gaps, revised_policy, roadmap):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    gaps_path = os.path.join(OUTPUT_DIR, "gaps.json")
    revised_path = os.path.join(OUTPUT_DIR, "revised_policy.txt")
    roadmap_path = os.path.join(OUTPUT_DIR, "roadmap.txt")

    status = "adequate" if not gap_found else "gaps_found"
    with open(gaps_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "gap_found": gap_found,
                "gaps": gaps,
                "domain": domain,
                "status": status,
            },
            f,
            indent=2,
        )

    with open(revised_path, "w", encoding="utf-8") as f:
        f.write(revised_policy.strip() + "\n")

    with open(roadmap_path, "w", encoding="utf-8") as f:
        f.write(roadmap.strip() + "\n")


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
def analyze():
    domain = (request.form.get("domain") or "").strip()
    policy_file = request.files.get("policy_file")

    if not domain or policy_file is None:
        return jsonify({"error": "Domain and policy_file are required."}), 400

    try:
        domain = step_select_domain(domain)
        policy_text = step_policy_intake(policy_file)
        reference_text = step_load_reference(domain)
        gaps = step_gap_identification(policy_text, reference_text, domain)
        gap_found = step_decision(gaps)
        revised_policy = step_policy_revision(policy_text, reference_text, gaps, domain)
        roadmap = step_review_validation(revised_policy, reference_text, gaps, domain)

        write_outputs(domain, gap_found, gaps, revised_policy, roadmap)

        return jsonify(
            {
                "gap_found": gap_found,
                "gaps": gaps,
                "revised_policy": revised_policy,
                "roadmap": roadmap,
            }
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/export_pdf", methods=["POST"])
def export_pdf():
    try:
        payload = request.get_json(silent=True) or {}
        text = (payload.get("text") or "").strip()
        domain = (payload.get("domain") or "").strip()
        if not text:
            return jsonify({"error": "No revised policy text provided."}), 400

        title = "Revised Policy"
        if domain:
            title = f"{domain} - Revised Policy"
        pdf_bytes = _make_pdf_bytes(title, text)
        filename = f"{_slugify(domain)}-revised-policy.pdf"
        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype="application/pdf",
            as_attachment=True,
            download_name=filename,
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    get_llm()
    app.run(host="127.0.0.1", port=5000, debug=False)
