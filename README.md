# POLICYLENS

Offline, lightweight web app to compare a policy document against a CIS/NIST reference and produce:
1. Gap report
2. Revised policy
3. NIST CSF improvement roadmap

**Highlights**
- Runs fully offline with a local TinyLlama model
- Accepts PDF or TXT policy files
- Domain-specific reference filtering for more relevant gaps
- Export revised policy as PDF

**Requirements**
- Python 3.10+
- Model file: `models/tinyllama-1.1b-chat.Q4_K_M.gguf`
- No internet required during runtime

**Environment Setup (Windows PowerShell)**
```powershell
cd c:\Users\subha\Desktop\IITKK\policy_gap_analyzer
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**Model Setup**
1. Place the model file at:
   `policy_gap_analyzer\models\tinyllama-1.1b-chat.Q4_K_M.gguf`
2. If the filename differs, rename it to match.

**Run**
```powershell
python src\backend\app.py
```
Open in browser:
```text
http://127.0.0.1:5000/
```

**How It Works**
1. Select a policy domain.
2. Upload a policy file (PDF or TXT).
3. The app loads a domain-filtered CIS/NIST reference.
4. Gaps are identified using:
   - LLM gap extraction per chunk
   - Heuristic gap checks
   - Reference-based coverage scoring
5. If gaps exist, the policy is revised.
6. A NIST CSF roadmap is generated.
7. Outputs are shown in the UI and saved to disk.

**Outputs**
- `data/outputs/gaps.json`
- `data/outputs/revised_policy.txt`
- `data/outputs/roadmap.txt`

**Export Revised Policy (PDF)**
- After analysis, click **Export PDF** in the Revised Policy panel.
- The download happens locally and stays offline.

**Domains**
Available domains (from the UI):
- ISMS
- Data Privacy & Security
- Patch Management
- Risk Management

Domain filtering is controlled in:
`src/backend/loader.py` (`DOMAIN_FILTERS`)

**Troubleshooting**
- **Browser says “127.0.0.1 refused to connect”**
  - The server is not running. Start it with `python src\backend\app.py`.
- **“Unexpected token '<' … not valid JSON”**
  - The backend returned HTML due to a 500 error. Check the server console.
- **PDF export error about horizontal space**
  - Fixed by wrapping long tokens. Restart the server if you updated code.
- **Model not found**
  - Ensure the model file exists at `models/tinyllama-1.1b-chat.Q4_K_M.gguf`.

**Notes**
- PDF extraction works best with selectable text.
- Very long policies are chunked; outputs are capped for stability.
