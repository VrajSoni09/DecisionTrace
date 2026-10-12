# DecisionTrace

DecisionTrace is a local NLP application that detects decision reversals in meeting notes and similar decision records. It uses the five required NLP topics: POS tagging, NER, syntactic parsing, semantic similarity, and text categorization.

## Key features
- Validate and sort meeting records chronologically
- Extract decision candidates from free text
- Classify statements as finalized, proposed, rejected, temporary, confirmed, or unknown
- Match related decisions semantically
- Detect reversals, confirmations, rejections, and temporary changes
- Inspect a Decision Evidence Explorer with exact source snippets, timeline, metadata, and NLP signals
- Export analysis results as JSON/CSV
- Import JSON, CSV, or TXT meeting records
- Run a small labeled evaluation dataset
- Ship as a Docker-ready FastAPI + React app without a database

## Local setup

```bash
cd D:/NLP_MPR
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
python -m spacy download en_core_web_sm
```

Start backend:

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Start frontend:

```bash
cd frontend
npm install
npm run dev
```

## API
- GET /api/health
- GET /api/analysis/sample
- POST /api/analysis/run
- POST /api/analysis/import
- POST /api/evaluation/run
- GET /api/evaluation
- POST /api/analysis/export

The analysis response includes evidence-backed reversal objects. Each object retains the original and
latest decision candidates, intermediate updates, chronological source spans, speaker/timestamp metadata
when supplied, entity/POS/syntax signals, similarity, classification status, and explicit limitations.
An approved-to-approved option change is the only transition treated as a confirmed reversal; proposals,
rejections, refinements, repeated confirmations, unrelated contexts, and ambiguous outcomes remain
non-reversals.

## Docker

```bash
docker compose up --build
```

## Notes
This initial release intentionally keeps analysis state in memory only, consistent with the PRD requirement to avoid a database in the first version.
