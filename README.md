# ST Competitive Intelligence RAG

> **Internal Marketing Tool — STMicroelectronics**  
> AI-powered competitive analysis for STM32 and other ST microcontroller product families.

---

## What This Does

The ST Competitive Intelligence RAG platform lets marketing team members enter any ST product part number and instantly receive a full competitive analysis — comparing ST's product against 3 rival products from NXP, Texas Instruments, and Infineon. The entire report is generated in under 30 seconds with zero manual research.

The tool produces four outputs for every query:

- **Spec Comparison** — side-by-side table of 17 technical parameters (Core, Clock, Flash, RAM, ADC, DAC, CAN-FD, Ethernet, USB, Security, Power modes, Voltage, Temperature, Packages, Price)
- **Gap Analysis** — per-competitor cards showing ST advantages vs competitor advantages, with gap severity ratings (LOW / MEDIUM / HIGH)
- **Strategic Summary** — ST strengths, critical gaps, competitive threat level (LOW to CRITICAL), market positioning statement, and target application tags
- **Marketing Brief** — AI-written narrative formatted with headers and bullet points, ready to paste into campaigns or presentations

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   Desktop Window                    │
│              (PyWebview / System Browser)           │
└────────────────────┬────────────────────────────────┘
                     │ HTTP localhost:8000
┌────────────────────▼────────────────────────────────┐
│                  FastAPI Backend                    │
│   ┌─────────────┐   ┌──────────────────────────┐    │
│   │  app/main.py│   │      app/engine.py       │    │
│   │  REST API   │   │  LangChain + Groq LLM    │    │
│   │  + Static   │   │  Synthetic RAG pipeline  │    │
│   │  File Server│   │  llama-3.3-70b-versatile │    │
│   └─────────────┘   └──────────────────────────┘    │
└─────────────────────────────────────────────────────┘
                     │ serves
┌────────────────────▼────────────────────────────────┐
│              React Frontend (dist/)                 │
│         TypeScript + Tailwind CSS + Vite            │
└─────────────────────────────────────────────────────┘
```

### Tech Stack

| Layer | Technology |
|---|---|
| LLM | Groq API — `llama-3.3-70b-versatile` |
| AI Framework | LangChain + LangChain-Groq |
| Backend | FastAPI + Uvicorn (Python 3.11+) |
| Frontend | React + TypeScript + Tailwind CSS + Vite |
| Markdown Rendering | ReactMarkdown |
| Desktop Distribution | PyInstaller + PyWebview |
| Schema Validation | Pydantic v2 |

---

## Project Structure

```
st-competitor-rag/
├── backend/
│   ├── app/
│   │   ├── main.py        # FastAPI app — all endpoints + static file serving
│   │   ├── engine.py      # LLM core — Synthetic RAG pipeline
│   │   ├── models.py      # Pydantic schemas
│   │   ├── prompts.py     # System prompt + analysis prompt template
│   │   └── utils.py       # JSON parsing + normalization helpers
│   ├── dist/              # React build output (copy here after npm run build)
│   ├── run.py             # App launcher — starts uvicorn + opens window/browser
│   ├── ST_Intelligence.spec  # PyInstaller spec file (optional)
│   ├── .env               # Optional: GROQ_API_KEY for dev use
│   └── requirements.txt
│
└── project/               # React frontend
    ├── src/
    │   ├── App.tsx         # Main app — all UI tabs and state
    │   └── SetupPage.tsx   # First-time API key onboarding screen
    ├── public/
    │   └── image.png       # ST logo
    ├── vite.config.ts      # base: './' set for PyWebview compatibility
    └── package.json
```

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/analyze` | Run competitive analysis for an ST product |
| `POST` | `/analyze/stream` | SSE streaming variant |
| `GET` | `/analyze/sample` | Hardcoded sample — no LLM call |
| `GET` | `/health` | Groq connectivity check |
| `POST` | `/set-key` | Store Groq API key in backend memory |
| `POST` | `/validate-key` | Validate key format + store if valid |
| `POST` | `/clear-key` | Clear stored key (user wants to change it) |
| `GET` | `/docs` | FastAPI auto-generated Swagger UI |

---

## Key Design Decisions

### Synthetic RAG
No external vector database. The LLM's own training knowledge about the semiconductor market is the knowledge base. Prompt engineering structures the output like retrieval — returning structured JSON with specs, advantages, and confidence scores. A `data_confidence` score (0–100) is returned with every response to indicate data reliability.

### Runtime API Key Management
Users enter their own free Groq API key on first launch via the SetupPage. The key is stored in the browser's `localStorage` and automatically synced to the backend via `POST /set-key` on every app start. The backend holds it in memory (`_RUNTIME_KEY` in `engine.py`). Priority order: runtime key → `.env` key.

### Dual Serving Mode
FastAPI serves both the REST API and the React `dist/` folder via `StaticFiles`. This means a single `uvicorn` process handles everything — no separate static server needed.

### API Key Validation
On corporate networks with Zscaler SSL inspection, live Groq API validation calls were blocked. Key validation was changed to **format-only checking** (`gsk_` prefix + minimum length) to bypass outbound SSL inspection, with SSL certificate verification fixed using `truststore` to inject the Windows system certificate store.

---

## Competitors Analyzed

The LLM is instructed to find the 3 most relevant competing products from:

- **Texas Instruments** (TMS320, MSP432, CC series, MSPM0)
- **Infineon Technologies** (XMC, AURIX TC, PSoC, CYW series)

The specific part numbers chosen are dynamic — the LLM selects whichever competing chips are most directly comparable to the queried ST product based on its training knowledge.

---

## Product Families Supported

The platform works with any ST part number. Tested families include:

| Family | Example Parts | Category |
|---|---|---|
| STM32 | STM32G474, STM32H743, STM32U575, STM32WB55 | MCU — all segments |
| STM8 | STM8S003, STM8L151 | 8-bit MCU |
| SPC5 | SPC584B | Automotive MCU |
| STA | STA1295 | Automotive SoC |
| L6x | L6234, L6390 | Gate Drivers |
| L78 / LD | L7805, LD1117 | Voltage Regulators |
| TSV / TSX | TSV911, TSX632 | Op-Amps |
| LM | LM393 | Comparators |
| M95 | M95256 | EEPROM |
| STPMIC | STPMIC1A | PMIC |
| TDA | TDA7388 | Audio Amplifiers |
| STUSB | STUSB4500 | USB Power Delivery |
| STSPIN | STSPIN32F0601, STSPIN250 | Intelligent Power Modules |

---

## Local Development Setup

### Prerequisites
- Python 3.11+
- Node.js 18+
- A free [Groq API key](https://console.groq.com/keys)

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt

# Optional: add your key to .env for dev (skips SetupPage)
echo GROQ_API_KEY=gsk_your_key_here > .env

uvicorn app.main:app --reload --port 8000
```

### Frontend (development with hot reload)

```bash
cd project
npm install
npm run dev
# Open http://localhost:5173
```

### Production build (serve frontend from FastAPI)

```bash
cd project
npm run build
xcopy /E /I /Y dist "..\backend\dist"   # Windows
# Then just run uvicorn — it serves everything from :8000
```

---

## Building the Windows Executable

The app is distributed as a standalone Windows `.exe` using PyInstaller. No Python installation required on the end user's machine.

### Step 1 — Build React frontend

```bash
cd project
npm run build
xcopy /E /I /Y dist "..\backend\dist"
```

### Step 2 — Build exe

```bash
cd backend
pyinstaller run.py --name ST_Intelligence --distpath exe_output --workpath build_work --noconfirm --noconsole --add-data "app;app" --add-data "dist;dist" --hidden-import uvicorn --hidden-import uvicorn.logging --hidden-import uvicorn.loops.auto --hidden-import uvicorn.protocols.http.auto --hidden-import uvicorn.protocols.websockets.auto --hidden-import uvicorn.lifespan.on --hidden-import fastapi --hidden-import fastapi.middleware --hidden-import fastapi.middleware.cors --hidden-import starlette --hidden-import starlette.middleware --hidden-import starlette.middleware.cors --hidden-import starlette.staticfiles --hidden-import starlette.responses --hidden-import starlette.routing --hidden-import groq --hidden-import langchain_groq --hidden-import langchain_core --hidden-import webview --hidden-import webview.platforms.winforms --clean
```

### Step 3 — Test

```bash
# Double-click Launch_ST.bat inside exe_output\ST_Intelligence\
# Or run via PowerShell to see errors:
Start-Process "exe_output\ST_Intelligence\ST_Intelligence.exe" -Wait -NoNewWindow -RedirectStandardOutput "out.txt" -RedirectStandardError "err.txt"
```

### Step 4 — Distribute

Zip the entire `exe_output\ST_Intelligence\` folder and share it. The recipient must keep all files together — the exe will not work without the `_internal\` folder beside it.

```
ST_Intelligence\
├── ST_Intelligence.exe     ← do not double-click directly
├── Launch_ST.bat           ← always use this to open the app
└── _internal\              ← all dependencies, do not delete
```

> **Always open the app using `Launch_ST.bat`**, not the exe directly. The batch file sets the correct working directory before launching.

---

## First-Time Setup (End Users)

1. Double-click **`Launch_ST.bat`**
2. The app opens in your browser at `http://127.0.0.1:8000`
3. The **First-Time Setup** screen appears — follow the steps to get a free Groq API key from [console.groq.com/keys](https://console.groq.com/keys)
4. Paste your key and click **Validate & Start Platform**
5. The key is saved locally — you will never need to enter it again

To change your API key, click the **logout icon** (↪) in the top-right corner of the app.

---

## Known Limitations

- **Price data** — `Price USD @ 1K` values come from the LLM's training data (2023/early 2024) and may not reflect current distributor prices. Always verify against Mouser, DigiKey, or the vendor's official pricing.
- **Data confidence** — The `data_confidence` score indicates how reliable the AI-generated specs are. Scores below 70% should be verified against official datasheets before use in external communications.
- **Corporate networks** — On networks with SSL inspection (e.g. Zscaler), the app uses format-only API key validation and injects the Windows certificate store via `truststore` to handle HTTPS correctly.

---

## UI Features

- **Dark / Light theme** — toggle in top-right, persists across sessions
- **Quick launch buttons** — 6 preset ST parts for one-click analysis
- **Online / Offline indicator** — shows Groq connectivity status in real time
- **Responsive layout** — works on laptop and desktop screen sizes

---

## Internal Use Only

This tool is intended for STMicroelectronics marketing team use only. It is not licensed for external distribution or public deployment. AI-generated competitive data should be verified against official vendor datasheets before inclusion in any external-facing marketing material.
