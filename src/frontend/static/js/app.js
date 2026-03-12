const form = document.getElementById("analyzeForm");
const statusEl = document.getElementById("status");
const gapSummary = document.getElementById("gapSummary");
const gapList = document.getElementById("gapList");
const revisedPolicy = document.getElementById("revisedPolicy");
const roadmap = document.getElementById("roadmap");
const exportPdfBtn = document.getElementById("exportPdf");

function toggleExportButton() {
  const hasText = revisedPolicy.textContent.trim().length > 0;
  if (exportPdfBtn) exportPdfBtn.disabled = !hasText;
}

async function readErrorMessage(res) {
  const contentType = res.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    try {
      const data = await res.json();
      if (data && data.error) return data.error;
    } catch (err) {
      // fall through to text
    }
  }
  try {
    const text = await res.text();
    if (text && text.trim().startsWith("<")) {
      return `Request failed (${res.status}). Server returned HTML.`;
    }
    if (text) return text;
  } catch (err) {
    // ignore
  }
  return `Request failed (${res.status}).`;
}

function setStatus(message, kind) {
  statusEl.textContent = message;
  statusEl.className = "status";
  if (kind === "ok") statusEl.classList.add("ok");
  if (kind === "err") statusEl.classList.add("err");
}

function renderGaps(data) {
  gapList.innerHTML = "";
  if (!data.gaps || data.gaps.length === 0) {
    gapSummary.textContent = "No gaps detected.";
    return;
  }
  gapSummary.textContent = `Gaps found: ${data.gaps.length}`;
  data.gaps.forEach((g) => {
    const li = document.createElement("li");
    const clause = g.clause || "Unspecified clause";
    const gap = g.gap || "Unspecified gap";
    const sev = g.severity || "low";
    li.textContent = `${clause} - ${gap} (Severity: ${sev})`;
    gapList.appendChild(li);
  });
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  setStatus("Analyzing policy...", "");
  const formData = new FormData(form);

  try {
    const res = await fetch("/analyze", {
      method: "POST",
      body: formData,
    });

    if (!res.ok) {
      throw new Error(await readErrorMessage(res));
    }

    const data = await res.json();
    renderGaps(data);
    revisedPolicy.textContent = data.revised_policy || "";
    roadmap.textContent = data.roadmap || "";
    toggleExportButton();
    setStatus("Analysis complete.", "ok");
  } catch (err) {
    setStatus(err.message, "err");
  }
});

if (exportPdfBtn) {
  exportPdfBtn.addEventListener("click", async () => {
    const text = revisedPolicy.textContent.trim();
    if (!text) return;

    const domainEl = document.querySelector('select[name="domain"]');
    const domain = (domainEl && domainEl.value) ? domainEl.value : "policy";
    const safeName = domain.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "");

    try {
      setStatus("Generating PDF...", "");
      const res = await fetch("/export_pdf", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, domain }),
      });

      if (!res.ok) {
        throw new Error(await readErrorMessage(res));
      }

      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${safeName || "policy"}-revised-policy.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      setStatus("PDF downloaded.", "ok");
    } catch (err) {
      setStatus(err.message, "err");
    }
  });
}

toggleExportButton();
