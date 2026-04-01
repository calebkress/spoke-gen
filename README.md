
# Spoke Generator

A small internal web app for generating MongoDB **Spokes** (Hypothesis, Why MongoDB, Proof Points, 3 Whys, Talk Track, Email) using Anthropic or OpenAI, storing runs in MongoDB Atlas, and exporting a nicely formatted PDF.

## Features

- Simple **web form**: company name, notes, transcript, extra instructions, model choice.  
- **LLM-backed Spoke generation** via Anthropic (Claude) or OpenAI (optional).  
- Structured parsing into a `SpokeContent` schema (hypothesis, why MongoDB, proof points, three whys, etc.).  
- **PDF export** using ReportLab with basic layout and word wrapping.  
- Optional **MongoDB Atlas** persistence for generated spokes.  

---

## Tech Stack

- **Backend**: FastAPI  
- **LLM**: Anthropic Python SDK (Claude Messages API), OpenAI Python SDK (optional)  
- **DB**: MongoDB Atlas via Motor / PyMongo  
- **PDF**: ReportLab  

---

## Project Structure (high level)

```text
spoke-gen/
├── app/
│   ├── main.py                 # FastAPI entrypoint + routes
│   ├── core/
│   │   ├── config.py           # Pydantic Settings (env loading)
│   │   └── pdf.py              # render_spoke_pdf(SpokeContent)
│   ├── db/
│   │   └── mongo.py            # get_spokes_collection(), Mongo client
│   ├── schemas/
│   │   └── spoke.py            # Pydantic SpokeCreateRequest, SpokeContent, SpokeInDB
│   ├── services/
│   │   └── spoke_generator.py  # LLM calls + parsing + DB glue
│   ├── api/
│   │   └── routes_spokes.py    # /api/spokes endpoints (JSON)
│   └── templates/
│       └── index.html          # Web UI for / (form → /generate)
├── .env                        # Local config (NOT committed)
├── README.md
└── requirements.txt or pyproject.toml
```

---

## Setup

### 1. Python env & deps

```bash
python3 -m venv .venv
source .venv/bin/activate        # or .venv\Scripts\activate on Windows

pip install -r requirements.txt  # or:
# pip install fastapi uvicorn motor anthropic openai reportlab python-dotenv jinja2
```

### 2. Environment variables (`.env`)

Create a `.env` file in the project root:

```env
# MongoDB
MONGODB_URI=mongodb+srv://<username>:<password>@<cluster-host>/?retryWrites=true&w=majority
MONGODB_DB_NAME=spoke_service

# Anthropic (Claude)
ANTHROPIC_API_KEY=sk-ant-...

# OpenAI (optional, for provider="openai")
OPENAI_API_KEY=sk-...
```

Notes:

- `MONGODB_URI` should be copied directly from Atlas → **Connect → Drivers**, then update `<username>` / `<password>`.  
- Keep `.env` **out of git** (already covered by `.gitignore`).  

---

## Running the App

From the project root:

```bash
uvicorn app.main:app --reload
```

Then open:

- **Web UI**: http://localhost:8000/  
  - Fill in company / notes / transcript / extra instructions.  
  - Pick provider/model (Anthropic Claude is the default).  
  - Click **Generate Spoke PDF** → browser downloads the PDF.  

- **API docs** (JSON endpoints):  
  - Swagger UI: http://localhost:8000/docs  
  - ReDoc: http://localhost:8000/redoc  

---

## Key Endpoints

Depending on your `routes_spokes.py`, typical JSON endpoints are:

- `POST /api/spokes/generate`  
  Body: `SpokeCreateRequest` (company, notes, transcript, provider, model, extra_instructions)  
  Returns: `SpokeInDB` (SpokeContent + `_id`)  

- `GET /api/spokes/{spoke_id}`  
  Returns a previously saved spoke as JSON.  

- `GET /api/spokes/{spoke_id}/pdf`  
  Returns the spoke as a PDF file (attachment).  

The web form at `/` posts directly to `/generate` and streams the PDF response.

---

## LLM Configuration Notes

- Anthropic is used via:

  ```python
  from anthropic import Anthropic

  client = Anthropic(api_key=settings.anthropic_api_key)
  client.messages.create(model=req.model, ...)
  ```

- The app **does not rely on JSON from the model anymore**; it asks Claude for a structured, labeled plain-text response and parses sections with regex into the `SpokeContent` schema. That avoids brittle JSON parsing and “valid JSON” 500s.  

- Each `/generate` call consumes tokens on your Anthropic/OpenAI account; keep that in mind before wide rollout.  

---

## PDF Layout

- Implemented with **ReportLab**.  
- `render_spoke_pdf(spoke: SpokeContent) -> bytes`:
  - Title: `Spoke – <Company>`  
  - Sections: SPOKE, Hypothesis, Why MongoDB (Pain/Gain), Proof Points, Talk Track, Email Template, 3 Whys.  
  - Uses `simpleSplit` to wrap long lines within margins.  

If you want closer parity to the official SalesDev Spoke template, tweak `render_spoke_pdf` to match headings, ordering, and spacing.

---

## Next Steps / Ideas

- Add **authentication** (SSO or simple auth) if this ever leaves localhost.  
- Add a **history view** (list prior spokes for that account, link to PDFs).  
- Add **per-section length controls** or sliders in the UI.  
- Add basic **logging/metrics** for usage (per account, per rep, per model).  
