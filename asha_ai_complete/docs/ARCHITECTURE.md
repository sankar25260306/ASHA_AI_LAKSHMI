# ASHA AI — Architecture

## Components

- **Frontend:** Vanilla HTML/CSS/JavaScript; responsive dashboard, district resource samples, pharmacy inventory, emergency case sandbox, Self-Doubt Engine, AI/ML panel, reports.
- **API:** FastAPI routes in `backend/app/main.py` for health, dataset/resource summaries, resource snapshots, self-doubt/cross-verification, matching, and the Random Forest demo prediction.
- **Pharmacy service:** `backend/app/network_pharmacy.py` owns the SQLite tables for users, branches, pharmacy stock, sessions, metadata, and audit events. Access is role checked and branch scoped for the pharmacy module.
- **Data:** 10,000-row synthetic research dataset; 1,000-row pharmacy CSV; 1,000-row resource snapshot CSV; and synthetic staff/facility CSVs.
- **ML:** RandomForestClassifier trained on generated synthetic labels by `backend/train_resource_risk_model.py`; artifact is `backend/app/resource_risk_model.joblib`.

## Data flow

```text
CSV demo datasets -> FastAPI resource loaders -> summary/resource APIs -> browser tables/cards
CSV pharmacy inventory -> versioned seed import -> SQLite pharmacy_stock -> authenticated pharmacy APIs -> paginated pharmacy table
User-supplied demo metrics -> Pydantic validation -> Random Forest model -> research-only result + human-review notice
Emergency sample case -> Self-Doubt Engine -> missing/stale/conflict alerts -> manual verification prompt
```

## Trust boundaries

- A user's role and branch scope are checked by network/pharmacy routes.
- The older prototype routes are not all covered by the network authorization system. Do not expose this package publicly or enter real patient data.
- All bundled branches/resources/stock values are synthetic placeholders. The 38 districts do **not** establish that any real Lakshmi Hospital franchise exists there.
- `GET /api/ambulances` reads 90 synthetic Lakshmi-placeholder records from `backend/data/ambulance_fleet_synthetic.csv` and returns vehicle ID, placeholder branch/district, type, status, crew label and equipment flags. All records are explicitly marked `SYNTHETIC_DEMO_NOT_REAL`; GPS and ETA are unavailable.
- The Ambulance Fleet UI supports search, status and type filters and shows sample onboard equipment; it is informational only and cannot dispatch a real vehicle. Resource matching deliberately returns no ambulance options until verified/authorized fleet data is connected.
- No live hospital, pharmacy, ambulance GPS, blood bank, or patient feed is connected.

## Performance notes

- Resource endpoints cap API row limits at 1,000.
- Frontend renders resource/pharmacy tables in 50-row pages to avoid rendering all rows at once.
- Pharmacy data uses indexed query filters only as currently defined; for production-sized inventories, add indexes on branch, medicine code/name, expiry date and stock update time, then benchmark with authorized representative volumes.


## Multi-agent LLM orchestration

`backend/app/multi_agent.py` implements isolated specialist tools: Hospital Resource Agent reads aggregate resource snapshots; Ambulance Operations Agent summarizes fleet status/equipment; Pharmacy Inventory Agent reads aggregate stock/expiry flags from the demo SQLite database; Self-Doubt / Verification Agent flags synthetic provenance and stale/unknown data. The orchestrator can pass these aggregate outputs to a locally running Ollama model or configured OpenAI-compatible chat endpoint for concise explanation. If LLM access is not available, deterministic fallback output remains available and is labelled in the UI/API.

The LLM receives aggregate synthetic metrics/findings only, not clinical case records or credentials. Its response is explanatory text; API-derived metrics remain the authoritative tool outputs. Analysis requires an authenticated allowed role, branch-scoped roles are constrained to the assigned branch/district, and each run creates an audit entry. No agent performs diagnosis, prescribing, autonomous dispatch, or stock ordering.


## Bounded autonomous monitoring

`backend/app/autonomous.py` runs a deterministic monitor as a FastAPI background task. It executes on startup and then at the configured interval (default 300 seconds). Each cycle calls the local aggregate resource, ambulance, pharmacy and Self-Doubt agents, creates threshold/data-quality review alerts, and stores a compact record in the existing SQLite database (`autonomous_settings` and `autonomous_runs`). It does not invoke an LLM during scheduled cycles.

Controls are exposed through authenticated routes in `backend/app/network_pharmacy.py`: all authenticated roles can view status/run history; Super Admin or Network Admin can launch a one-off cycle; only Super Admin can pause/resume and configure the schedule. The browser controls are in the Multi-Agent AI page. A monitor cycle can only read synthetic aggregate data, calculate flags, persist alerts and write audit events. There is no automatic vehicle dispatch, clinical recommendation execution, treatment, prescription, pharmacy purchase order, or stock mutation. Those operational actions are explicitly reported as not performed and require human authorization.
