# Bulk Certificate Generator

A FastAPI backend (plus a small React dashboard) that turns **one request with many recipients** into **individual PDF certificates**, tracks progress, and keeps going when a single certificate fails.

## Features

- `POST /api/jobs` accepts a whole list of recipients in one request and returns a job ID immediately (202).
- Certificates are generated in the background with FastAPI `BackgroundTasks`.
- Live progress: total, successful, failed, completed and a progress percentage.
- One failed certificate never stops the others. Each failure stores its own error message.
- Job ends as `COMPLETED`, `COMPLETED_WITH_ERRORS` or `FAILED`.
- One professional landscape A4 PDF template made with ReportLab.
- Download any ready certificate; failed or pending ones return a clear `409`.
- Pydantic validation, structured JSON errors, no stack traces in responses.
- Safe file handling: files are named `certificate_<id>.pdf`, paths are checked against the certificate folder.
- 39 pytest tests using an isolated SQLite database.
- Optional React + Vite dashboard: create a batch with a live certificate preview, watch progress, download PDFs.

## Tech stack

Python 3.11+, FastAPI, SQLAlchemy 2, SQLite, Pydantic v2, ReportLab, Uvicorn, pytest. Frontend: React 18 + Vite.
`python-dotenv` (reads `.env`) and `email-validator` (via `pydantic[email]`) are the only extras, each for one clear job.

## Architecture

```
Client (browser / curl / React app)
        ↓
FastAPI app (app/main.py)           CORS, error handlers, router wiring
        ↓
API layer (app/api/routes)          HTTP only: parse request, call service, shape response
        ↓
Service layer (app/services)        job_processor.py: business rules, certificate_generator.py: PDFs
        ↓                    ↘
Database (SQLAlchemy/SQLite)   Background processing (BackgroundTasks → process_job)
                                      ↓
                              PDF generation (ReportLab)
                                      ↓
                              Generated files (generated_certificates/certificate_<id>.pdf)
```

Request flow: validate → create job + PENDING certificate rows → return `202` → background task sets the job to `PROCESSING` → for each certificate: generate PDF, mark `SUCCESS` or `FAILED`, bump counters, **commit** → set final job status.

## Project structure

```
app/
  main.py                      app creation, middleware, routers
  api/routes/                  jobs.py, certificates.py, health.py
  core/config.py               settings from environment (.env)
  core/errors.py               AppError + structured error handlers
  db/database.py, models.py    engine/session, GenerationJob + Certificate
  schemas/                     Pydantic request/response models
  services/
    certificate_generator.py   pure PDF logic, no DB or HTTP
    job_processor.py           create_job() and process_job()
  utils/                       filename sanitizing, safe path resolving, UTC helper
tests/                         conftest + test_jobs / test_certificates / test_generation
samples/                       demo requests (valid batch with one failing name, invalid request)
frontend/                      optional React + Vite dashboard
```

Why this shape: routes stay thin, the rules live in services, and the PDF code can be tested without a database. It matches the suggested layout; additions are `core/errors.py`, `utils/` helpers and `samples/`.

## Setup

```bash
git clone <your-repo-url> && cd bulk-certificate-generator
python -m venv venv
# macOS/Linux
source venv/bin/activate
# Windows
venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

API docs: http://localhost:8000/docs. Optional: `cp .env.example .env`.

Frontend (second terminal):

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173, proxies /api to port 8000
```

## API usage

Create a job (the sample has 6 recipients; the last name contains characters the PDF font can't draw, so it fails on purpose):

```bash
curl -X POST http://localhost:8000/api/jobs \
  -H "Content-Type: application/json" \
  -d @samples/sample_request.json
```
```json
{ "job_id": 1, "status": "PENDING", "total": 6 }
```

Check progress:

```bash
curl http://localhost:8000/api/jobs/1
```
```json
{ "job_id": 1, "status": "COMPLETED_WITH_ERRORS", "total": 6, "successful": 5,
  "failed": 1, "completed": 6, "progress_percentage": 100, "...": "..." }
```

List certificates and download:

```bash
curl http://localhost:8000/api/jobs/1/certificates
curl -o certificate.pdf http://localhost:8000/api/certificates/1
```

Other: `GET /api/jobs` (recent jobs, used by the dashboard), `GET /api/health`.
See a validation error: `curl -X POST localhost:8000/api/jobs -H "Content-Type: application/json" -d @samples/sample_invalid_request.json` returns `422`.

Errors always look like `{"error": {"code": "...", "message": "...", "details": [...]}}`.
Status codes: `202` created, `404` job/certificate missing, `409` certificate pending or failed, `422` invalid input.

## Testing

```bash
pytest
```
Tests use a temporary SQLite file and a temporary certificate folder, so they never touch real data and don't need a running server. Most tests replace PDF rendering with a tiny fake for speed; `test_generation.py` also renders real PDFs.

## Design decisions

- **FastAPI**: type hints drive validation, docs and tests with very little code.
- **SQLite**: zero setup, one file, plenty for local development. SQLAlchemy lets you switch to PostgreSQL by changing `DATABASE_URL`.
- **SQLAlchemy**: models, relationships and indexes in plain Python; the ORM prevents SQL injection by default.
- **BackgroundTasks**: the request returns instantly and the work continues in the same process. No broker to install or explain.
- **ReportLab**: pure Python PDF drawing with no browser or system dependencies.
- **Individual failures**: each certificate is wrapped in its own `try/except`. On error it is marked `FAILED` with a safe message, the failure counter goes up, and the loop continues. Counters are committed after every certificate, so progress is live.
- **One template**: the brief asks for one. Keeping it in one module makes it easy to read and later replace.
- **Stored file name only**: the database holds `certificate_7.pdf`, never an absolute path, and downloads re-check the path stays inside the certificate folder.

## Limitations

- Background tasks run inside the web process: a server restart mid-job leaves that job in `PROCESSING`, and there is no retry.
- Built-in PDF fonts support Western (Latin-1/cp1252) characters only. Names in other scripts fail with a clear message instead of printing wrong glyphs.
- No authentication, rate limiting, or per-user ownership of jobs.
- PDFs live on local disk; there is no cleanup or cloud storage.
- Polling (not websockets) is used for live progress.

## Future improvements

Redis + Celery/RQ for durable distributed jobs, a Unicode font (e.g. Noto) for all scripts, cloud storage, authentication, multiple templates, email delivery, ZIP download of a whole job, rate limiting, Alembic migrations.

## Common interview questions

**Why BackgroundTasks and not Celery?** The brief wants simple and explainable. BackgroundTasks keeps the request fast without extra infrastructure. For very large or critical workloads I'd move to Celery/RQ + Redis for persistence, retries and multiple workers.

**What happens if the server restarts during a job?** The job stays `PROCESSING` and unfinished certificates stay `PENDING`. A queue with retries (or a startup task that resumes `PENDING` rows) would fix this; it's listed as a limitation.

**How do you make sure one failure doesn't stop the batch?** `_generate_one` catches every exception, records it on that certificate, and the loop moves on. A last-resort guard around the whole job prevents it from sticking in `PROCESSING`.

**Why does `process_job` open its own database session?** The request's session is closed when the response is sent, and sessions aren't thread-safe. The background task creates and closes its own.

**How is progress calculated?** `(success + failed) * 100 // total`, rounded down so 199/200 shows 99%, not 100%. It's stored as counters updated after each certificate.

**How do you prevent path traversal?** Filenames come only from the numeric ID (`certificate_<id>.pdf`). Download names use a sanitized slug of the recipient name. Before serving, the resolved path must sit directly inside the certificate folder.

**Why return 202 from POST /api/jobs?** The work isn't finished yet, only accepted. 202 says that precisely.

**Why 409 for a certificate that isn't ready?** The certificate exists, but its current state conflicts with the request, so it is neither 404 nor 400.

**How would you scale this?** Queue + workers, PostgreSQL, object storage for PDFs, batch commits, and pagination on certificate lists.

**How do tests avoid a running server and real data?** `TestClient` calls the app in-process, and `conftest.py` points the database and output folder to a temp directory before the app is imported. Starlette runs background tasks before `client.post()` returns, so tests can assert on final results directly.
