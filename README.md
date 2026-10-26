# BrandPrint AI 🛡️✨

> **Enterprise Brand Governance, Multi-Modal Compliance & Real-Time What-If Sandbox**

BrandPrint AI is an enterprise-grade brand compliance, consistency auditing, and governance automation platform. It empowers global marketing, legal, and engineering teams to ingest complex brand guidelines from diverse document formats, verify brand adherence across multi-channel content, detect internal contradictions autonomously, and simulate copy revisions with real-time editorial suggestions and strategic impact scores.

---

## 🌟 Key Platform Capabilities

### 1. Multi-Format & Multi-Modal Document Ingestion
- **Document Handbooks:** Native ingestion and chunking for `.pdf`, `.docx`, `.pptx`, and `.txt` files.
- **SSRF-Protected Web Scraper:** Ingests live company brand wikis, Notion public handbooks, and public guideline URLs with strict domain validation and IPv4/IPv6 private IP filtering.
- **Automated Rule Extraction:** Converts dense corporate policy PDFs into structured, atomic, vector-indexed compliance rules.

### 2. Autonomous Contradiction Detection Engine
- Cross-references hundreds of guideline rules across departments (Legal, Marketing, Engineering, Design).
- Identifies internal policy conflicts, SLA paradoxes, and licensing mismatches.
- Resolves conflicts via a one-click **AI Rule Harmonizer** that drafts compromise rules and updates the knowledge base.

### 3. Multi-Dimensional Inconsistency Detection Engine
Evaluates submitted copy in a holistic secondary audit pass covering 6 critical dimensions:
1. **🎭 Tone & Voice Inconsistency (`tone_inconsistency`):** Catches jarring shifts between enterprise B2B governance and colloquial internet slang.
2. **🌐 Language & Dialect Shift (`language_style_shift`):** Detects regional spelling discrepancies (e.g., mixing UK `optimise` with US `color`), jargon overuse, and passive voice spikes.
3. **📊 Factual & Numerical Drift (`factual_drift`):** Identifies conflicting SLA metrics (e.g., claiming 99.9% uptime on page 1 vs. 99.999% on page 3) with dual-excerpt comparison boxes.
4. **⚠️ Contradictory Claims (`claim_conflict`):** Surfaces incompatible assertions (e.g., "100% open-source" combined with "proprietary vendor lock-in").
5. **🎨 Visual Usage & Media Mentions (`visual_guideline_breach`):** Flags unapproved brand color hex codes (`neon green`, `#39FF14`) and improper typography rules.
6. **♿ Accessibility & Readability (`accessibility_issue`):** Audits against WCAG 2.1 standards, highlighting extreme linguistic complexity (Flesch-Kincaid > Grade 16) and non-inclusive terminology.

### 4. Interactive Pre-Flight "What-If" Simulator
- Allows copywriters and compliance officers to test live edits and proposed rephrasing before production deployment.
- Delivers real-time delta scorecards (Net Score, Resolved Violations, Remaining Hurdles, New Violations).
- Computes projected **Strategic Business Benefits** (Brand Credibility, Regulatory Safety, Procurement Velocity, Accessibility Reach).

### 5. Executive Governance Dashboard
- Real-time audit readiness score and compliance adherence telemetry.
- Categorical distribution charts, broken rule frequency heatmaps, and downloadable compliance certificates.

---

## 🎨 Enterprise Design System

BrandPrint AI utilizes a curated, executive design palette crafted for deep contrast, legibility, and visual polish:

| Token Name | Hex Code | Purpose |
|---|---|---|
| **Deep Ocean Teal** | `#0B3C49` | Primary brand identity, headers, navigation, active states |
| **Ocean Dark** | `#072831` | Deep background containers, high-contrast modal backdrops |
| **Warm Amber** | `#F4A321` | Call-to-actions, primary highlights, warning indicators |
| **Amber Hover** | `#E09218` | Interactive button hover states |
| **Warm Cream** | `#FBF9F4` | Canvas surfaces, secondary badge fills, input buffer zones |
| **Sand Neutral** | `#E5E0D8` | Structural dividing borders and subtle card rings |
| **Charcoal Dark** | `#1C2526` | High-readability editorial typography |

---

## 🛠️ Technology Stack

- **Backend Architecture:**
  - **Framework:** FastAPI (Python 3.11+)
  - **Database & ORM:** PostgreSQL (Supabase pooler) via SQLAlchemy & Psycopg2
  - **Vector Semantic Search:** Meta FAISS (Facebook AI Similarity Search) with `all-MiniLM-L6-v2` embeddings
  - **Generative AI:** Google Gemini 2.5 Flash (`generativelanguage.googleapis.com`) with automated local Ollama (`llama3.2`) and deterministic regex failover
  - **Document Parsing:** `PyMuPDF` (PDFs), `python-docx` (Word), `python-pptx` (PowerPoint), `BeautifulSoup4` + `httpx` (Web Scraper)
- **Frontend Architecture:**
  - **Framework:** Vite + React (TypeScript)
  - **Styling:** Vanilla Tailwind CSS with custom theme tokens
  - **Icons:** Lucide React
  - **State Management & Routing:** React Context API & React Router DOM 6

---

## 🚀 Quickstart & Local Setup

### Prerequisites
- Python 3.11+
- Node.js 18+ and `npm`
- (Optional) Local [Ollama](https://ollama.ai/) instance for offline LLM fallback

### 1. Backend Setup

```bash
# Navigate to backend directory
cd backend

# Create and activate virtual environment
python -m venv .venv

# Windows Powershell:
.venv\Scripts\Activate.ps1
# macOS / Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env with your Supabase DB URL and Gemini API Key
```

Run the FastAPI backend server (Port `8001`):
```bash
uvicorn app.main:app --reload --port 8001
```

Backend API Docs will be available at: `http://localhost:8001/docs`  
Health check endpoint: `http://localhost:8001/health`

### 2. Frontend Setup

```bash
# Navigate to frontend directory
cd frontend

# Install Node dependencies
npm install

# Configure environment variables
cp .env.example .env
# Verify VITE_API_BASE_URL=http://localhost:8001
```

Run the Vite frontend dev server (Port `5173` or `5174`):
```bash
npm run dev
```

Open your browser at `http://localhost:5173` (or `http://localhost:5174`).

---

## 🧪 Verification & Default Credentials

### Default Development User
- **Email:** `admin@brandprint.ai` (or `tester@brandprint.ai`)
- **Default Role:** Compliance Manager / Brand Lead

### Live Verification Endpoints
- **Run Content Review:** `POST /api/reviews`
- **Audit Contradictions:** `GET /api/guidelines/contradictions/check?brand_id=1`
- **Automated Rule Extraction:** `POST /api/guidelines/ingest-document`
- **What-If Simulation:** `POST /api/reviews/{id}/what-if-simulate`
- **Health Check:** `GET /health`

---

## 📁 Repository Structure

```
codex48/
├── backend/
│   ├── app/
│   │   ├── core/           # Security, JWT, DB engine, and App Settings
│   │   ├── models/         # SQLAlchemy ORM models (Brand, Guideline, Finding, etc.)
│   │   ├── routes/         # FastAPI endpoints (Reviews, Guidelines, Contradictions)
│   │   ├── schemas/        # Pydantic request/response validation schemas
│   │   └── services/       # AI Service, FAISS Retriever, Web Scraper, Ingestion Engine
│   ├── requirements.txt    # Python dependencies
│   ├── .env.example        # Backend environment template
│   └── test_all_inconsistencies.py # Automated regression suite
├── frontend/
│   ├── src/
│   │   ├── api/            # Typed Axios clients for Backend API
│   │   ├── components/     # FindingCard, WhatIfSimulator, AddRuleModal, Sidebar
│   │   ├── pages/          # ReviewStudio, Guidelines, Dashboard, AuditPage
│   │   ├── types/          # TypeScript domain interfaces
│   │   └── App.tsx         # Main application routes and theme provider
│   ├── package.json        # Frontend dependencies and scripts
│   ├── tailwind.config.js  # Theme palette and styling tokens
│   └── .env.example        # Frontend environment template
├── .gitignore              # Strict secret and build output exclusion list
└── README.md               # Enterprise platform documentation
```

---

## 🔒 Security & Compliance

- **No Secrets in Repo:** All database connection strings, JWT signing keys, and Gemini API keys are isolated in local `.env` files and excluded via `.gitignore`.
- **SSRF Protection:** Web scraping pipeline utilizes private subnet lookups and IP blacklisting to protect against unauthorized internal server access.
- **Fail-Safe Fallbacks:** Deterministic regex engines and local Ollama ensure high availability even when external AI API quotas are exhausted.

---

## 📄 License
Enterprise Commercial — All Rights Reserved © BrandPrint AI.
