# SOMA Backend

Health diary REST API — Flask + PostgreSQL + Ollama LLM.

## Development commands

```bash
pip install -r requirements.txt          # install deps
python frontend_endpoints.py             # run dev server (default :5000)
python frontend_endpoints.py --port 8080 # custom port
pytest tests/                            # run tests
```

Requires a `.env` with `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`.
Optional: `STT_URL` for speech-to-text forwarding.

## Architecture

```
frontend_endpoints.py  (Flask routes + CORS)
        │
        ├── models.py          Pydantic v1 models (DiaryEntryModel, PatientProfileModel, HealthAlertModel)
        ├── db.py               psycopg2 CRUD (SimpleConnectionPool, parameterized SQL)
        ├── const.py            env-var config, SQL DDL & DML templates
        └── llm_dispatcher.py   Ollama HTTP API (default model: gemma3:4b)
```

- **No ORM** — raw SQL via `psycopg2`, all queries parameterized (`%s`).
- DB tables: `patients`, `diary_entries`, `health_alerts`. Schema defined in `const.py`.
- `db.init_db()` creates tables + indices on startup.

## Key conventions

- **camelCase JSON** — Pydantic field names match the Flutter frontend (`patientProfileId`, `moodLevel`, `healthComplaints`). Each model has a `to_json_dict()` for serialization.
- **Pydantic v1** — uses `parse_obj`, `validator`, `Field`, `BaseModel.Config`. Do NOT use v2 API.
- **Connection pooling** — `psycopg2.pool.SimpleConnectionPool` (1–10 conns), configured in `const.py`.
- **LLM integration** — `llm_dispatcher.py` sends prompts to Ollama (`/api/generate`), returns parsed JSON. The `/profiles/<id>/recommendation` endpoint calls the LLM and persists results as `HealthAlert` rows.

## REST endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/entries` | Create diary entry |
| GET | `/entries/<id>` | Get diary entry |
| GET | `/profiles/<id>/entries` | List entries for patient |
| POST | `/profiles` | Create patient profile |
| GET | `/profiles` | List all profiles |
| GET | `/profiles/<id>` | Get profile |
| POST | `/alerts` | Create health alert |
| GET | `/alerts` | List all alerts |
| GET | `/alerts/<id>` | Get alert |
| GET | `/profiles/<id>/recommendation` | Generate LLM recommendation |
| POST | `/transcribe` | Forward audio to STT service |

PUT/DELETE endpoints for entries, profiles, and alerts exist but use in-memory stores (not yet wired to DB).

## Testing

Tests in `tests/test_frontend_endpoints.py` use Flask's test client (`app.test_client()`). They currently test the in-memory CRUD flow, not the DB-backed endpoints.
