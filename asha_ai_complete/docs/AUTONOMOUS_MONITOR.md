# ASHA AI — Bounded Autonomous Monitoring

## What becomes autonomous?

When the FastAPI backend starts, the monitor makes an initial cycle and then repeats on the configured interval. The default is 300 seconds (5 minutes). It independently reads aggregate local demo data from the hospital-resource CSV, ambulance fleet CSV, and pharmacy SQLite database. It calculates threshold and data-quality flags, creates review alerts, and persists a run summary/metrics/alerts in the SQLite `autonomous_runs` table.

The scheduler does not need an LLM to do its monitoring. `Multi-Agent AI` manual analysis can still use the optional Ollama/OpenAI-compatible LLM explanation path. If the LLM is unavailable, the autonomous monitoring still works with deterministic rules.

## UI controls

Open **Multi-Agent AI → Autonomous Watch**.

- **Status** shows enabled/paused, interval, total cycles, last cycle, and approximate next run.
- **Run monitoring now** is available to Super Admin and Network Admin.
- **Pause / Resume monitoring** and schedule control are available only to Super Admin.
- **Refresh status** reloads persisted status and run information.

The interval can be set between 60 and 3,600 seconds. The monitor checks for updated settings every 5 seconds, so pause/resume changes are picked up without waiting for the whole interval.

## API endpoints

All endpoints require an active authenticated session.

| Method | Endpoint | Permission | Purpose |
|---|---|---|---|
| `GET` | `/api/network/autonomous/status` | Any authenticated role | Monitor settings, last run, total runs |
| `GET` | `/api/network/autonomous/runs?limit=20` | Any authenticated role | Recent persisted cycle summaries and alerts |
| `POST` | `/api/network/autonomous/run` | Super Admin, Network Admin | Execute a one-off monitoring cycle |
| `PATCH` | `/api/network/autonomous/settings` | Super Admin only | Pause/resume and set interval |

Example settings body:

```json
{"enabled": true, "interval_seconds": 300}
```

## Bounded-autonomy safety boundary

Allowed autonomous activities: aggregate file/database reads, deterministic threshold calculations, stale/unknown/expiry/low-stock demo alerts, creation of review recommendations, and local run-log persistence.

Explicitly not performed: ambulance dispatch, clinical diagnosis, clinical triage decisions, treatment or prescribing, pharmacy purchase orders, dispensing, stock mutation, or external messages. Each run describes these restricted actions as not performed and flags human review. The scheduler operates only on synthetic, unverified demo data; it is not a live hospital monitoring connection.

## How to verify

From the `backend/` folder:

```powershell
python -m pytest tests -q
```

The suite validates manual cycle execution, persisted run history, authentication, role restrictions, explicit non-execution of operational actions, and a background cycle started during FastAPI lifespan. A separate long-running staging check should be conducted before claiming scheduler timing under real Uvicorn; the automated suite is not a production reliability or security test.
