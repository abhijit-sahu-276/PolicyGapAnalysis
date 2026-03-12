# POLICYLENS

Offline, lightweight web app to compare an organizational policy document against a CIS/NIST reference and produce:

1. Gap Report
2. Revised Policy
3. NIST CSF Improvement Roadmap

---

## Highlights

* Runs **fully offline** using a local LLM model
* Accepts **PDF or TXT policy documents**
* Performs **domain-specific reference filtering**
* Generates **structured gap reports**
* Produces **revised policies automatically**
* Export the revised policy as **PDF**
* No internet required during runtime

---

## Project Structure

```
policy_gap_analyzer/
│
├── data/
│   ├── inputs/
│   └── outputs/
│
├── models/                       # Local LLM model goes here
│
├── src/
│   └── backend/
│       ├── app.py
│       ├── gap_analyzer.py
│       └── loader.py
│
├── backend.err.log
├── backend.out.log
├── requirements.txt
└── README.md
```

---

## Requirements

* Python **3.10+**
* Required libraries listed in `requirements.txt`
* Local LLM model (TinyLlama)

Install dependencies:

```
pip install -r requirements.txt
```

---

# Model Setup (Important)

This project uses the **TinyLlama 1.1B Chat model** to perform local policy analysis.

Due to **GitHub file size limits (100 MB)**, the model file is **not included in this repository** and must be downloaded manually.

---

## Step 1 — Download the Model

Download the GGUF model file:

```
tinyllama-1.1b-chat.Q4_K_M.gguf
```

You can download it from the official model repository on Hugging Face.

Example source:

https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-GGUF

Download the file:

```
tinyllama-1.1b-chat.Q4_K_M.gguf
```

---

## Step 2 — Place the Model in the Correct Folder

After downloading, place the file in:

```
policy_gap_analyzer/models/
```

Final structure should look like:

```
policy_gap_analyzer/
│
├── models/
│   └── tinyllama-1.1b-chat.Q4_K_M.gguf
```

If the filename differs, rename it to:

```
tinyllama-1.1b-chat.Q4_K_M.gguf
```

---

# Environment Setup (Windows PowerShell)

```
cd c:\Users\subha\Desktop\IITKK\policy_gap_analyzer

python -m venv .venv
.\.venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

---

# Run the Application

Start the backend server:

```
python src\backend\app.py
```

Open in your browser:

```
http://127.0.0.1:5000/
```

---

# How It Works

1. Select a **policy domain**.
2. Upload a **policy document** (PDF or TXT).
3. The application loads a **domain-filtered CIS/NIST reference**.
4. Policy analysis is performed using:

   * LLM-based gap extraction per document chunk
   * Heuristic policy checks
   * Reference coverage scoring
5. If gaps are detected:

   * A **revised policy** is generated.
6. A **NIST CSF improvement roadmap** is generated.
7. All outputs are displayed in the UI and saved locally.

---

# Outputs

Generated files are saved in:

```
data/outputs/
```

Files generated:

```
data/outputs/gaps.json
data/outputs/revised_policy.txt
data/outputs/roadmap.txt
```

---

# Export Revised Policy (PDF)

After analysis:

1. Go to the **Revised Policy panel**
2. Click **Export PDF**
3. The revised policy will download locally

The entire process remains **offline**.

---

# Supported Policy Domains

Available domains in the UI:

* ISMS
* Data Privacy & Security
* Patch Management
* Risk Management

Domain filtering logic is defined in:

```
src/backend/loader.py
```

Look for:

```
DOMAIN_FILTERS
```

---

# Troubleshooting

### Browser shows "127.0.0.1 refused to connect"

The backend server is not running.

Start it using:

```
python src\backend\app.py
```

---

### “Unexpected token '<' … not valid JSON”

This usually means the backend returned an **HTML error page instead of JSON**.

Check the backend terminal for a **500 error**.

---

### PDF export error about horizontal space

This occurs when text tokens exceed PDF width.

Restart the server after applying code updates.

---

### Model Not Found

Ensure the model file exists at:

```
models/tinyllama-1.1b-chat.Q4_K_M.gguf
```

---

# Notes

* The TinyLlama model file is **~600MB**, therefore it is excluded from this repository.
* The application runs **fully offline once the model is downloaded**.
* PDF extraction works best with **selectable text PDFs**.
* Very long policies are **chunked for stable processing**.

---

# Author

**Abhijit Sahu**
B.Tech Computer Science Engineering

---

# License

This project is for **academic and research purposes**.
