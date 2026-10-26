# ASHA AI — Autonomous Emergency Care Logistics Agent

ASHA AI is a **local research / college prototype** that demonstrates uncertainty-aware emergency resource coordination, pharmacy stock monitoring, access roles, and an educational Random Forest model. It is configured to display a **Lakshmi Hospital-only demo scope**; the 38 district entries are placeholders and are **not verified Lakshmi Hospital branches**.

> **Safety notice:** Every bundled stock, hospital resource, staff, ambulance and branch record is synthetic. No real Lakshmi Hospital, pharmacy, patient, ambulance GPS, blood bank or dispatch data feed is connected. Do not use it for patient care, medicine dispensing, triage, real dispatch or operational resource allocation. Do not enter real patient data.

## Included data

| File / dataset | Rows | Purpose |
|---|---:|---|
| `backend/data/asha_ai_synthetic_dataset_10000.csv` | 10,000 | Research scenarios used for dataset summary and uncertainty-pattern examples; 8,000 train / 2,000 test split metadata |
| `backend/data/asha_lakshmi_pharmacy_1000_demo.csv` | 1,000 | Pharmacy demo inventory imported into SQLite on first startup |
| `backend/data/asha_lakshmi_hospital_resources_1000_demo.csv` | 1,000 | Resource snapshots exposed through `/api/resources/snapshots` |
| `backend/data/doctors_synthetic.csv`, `nurses_synthetic.csv`, `beds_synthetic.csv`, `blood_inventory_synthetic.csv`, `ambulance_fleet_synthetic.csv`, `medical_equipment_synthetic.csv`, `medicine_inventory_synthetic.csv` | Varies; ambulance file has 90 rows | Synthetic staff/facility category examples |

All rows are marked demo/synthetic and must never be represented as real branch coverage or actual availability. The pharmacy database import uses a version marker to avoid duplicating the 1,000-row seed on every restart.

## Run on Windows

1. Extract the ZIP into a new folder.
2. Install **Python 3.10+**. The backend starter creates `.venv` and installs required packages on first run; internet access is needed for package installation.
3. Double-click `start_backend_windows.bat`; keep its terminal open until Uvicorn starts.
4. Double-click `start_frontend_windows.bat` in a second terminal.
5. Open `http://127.0.0.1:5173`.
6. API health: `http://127.0.0.1:8000/api/health`; interactive API docs: `http://127.0.0.1:8000/docs`.

### Role-based local demo login

1. On the login screen, select the role assigned to your account (Super Admin, Network Admin, Hospital Admin, Doctor / Triage, Ambulance Dispatcher, Ambulance Driver, Pharmacy Staff, or Auditor).
2. Type your own username and password; the form does not prefill a username or disclose a password.
3. The backend checks that the selected role exactly matches the role stored on that user account. Choosing Super Admin does not grant Super Admin permissions to another account.
4. On a fresh local demo database, the initial bootstrap account is username `superadmin`, initial password `ASHA-Demo-2026!`, and role **Super Admin**. This is documented here for local setup only; the login form does not show it. Set a new password of at least 12 characters on first login.
5. Other users must be created by an authorized Super Admin and sign in using their assigned role and individually issued credentials.

If you have run an older copy, its existing database may have a different password or existing accounts. Do not delete an existing database without making a backup.

The initial credentials and fallback token secret are for a local prototype only. Never use them on a public deployment. Production use requires secrets managed outside source code and a complete security review.

## AI/ML demonstration

Open **AI Recommendations** → **AI/ML Resource Shortage Pattern Analysis**. It calls:

- `GET /api/ml/resource-risk/status`
- `POST /api/ml/resource-risk/predict`

The Random Forest model is trained by `backend/train_resource_risk_model.py` on generated synthetic labels. The bundled evaluation metrics measure fit to artificial labels only; they do not establish real-world resource-shortage prediction accuracy. Keep a human reviewer in the loop and do not use output for live emergency decisions.

The **Self-Doubt Engine** and cross-verification endpoints also highlight missing, stale or conflicting information instead of silently assuming that a value is correct.

## LLM multi-agent demo

Open **Multi-Agent AI** after signing in. The workflow runs four specialist data agents—Hospital Resource, Ambulance Operations, Pharmacy Inventory, and Self-Doubt / Verification—then uses an optional LLM orchestrator to explain the aggregate evidence. The analysis endpoint is `POST /api/network/agents/analyze`; runtime status is `GET /api/network/agents/status`. Analysis actions are audited and branch-scoped roles are restricted to their assigned branch/district.

**Local LLM option (recommended for a no-cloud demo):** install Ollama separately, then run `ollama pull qwen2.5:3b`. Leave Ollama running and restart the ASHA backend. The app defaults to provider `ollama`, model `qwen2.5:3b`, URL `http://127.0.0.1:11434`. The app does not install Ollama automatically or bundle model weights. If Ollama/model is unavailable, the specialist data agents still work and a clearly labelled deterministic explanation is returned.

**Optional OpenAI-compatible provider:** set environment variables before starting the backend: `ASHA_LLM_PROVIDER=openai_compatible`, `ASHA_LLM_MODEL=<your model>`, `ASHA_LLM_API_KEY=<your secret>`, and optionally `ASHA_LLM_BASE_URL=https://api.openai.com/v1`. This can incur provider charges. Never commit secrets to source control. Only synthetic aggregate agent evidence is sent to the model; no patient case input is collected by this module.

Analysis types are `network_readiness`, `pharmacy_risk`, `ambulance_readiness`, and `data_quality`. The LLM is an explanation layer, not the source of inventory/resource facts; it cannot diagnose, prescribe, order stock, or dispatch ambulances. All outputs require human review and remain synthetic demo results.

## Bounded autonomous monitoring

The app now starts a **bounded autonomous monitor** with the backend by default. It runs a deterministic cycle on startup and then every 5 minutes (configurable from 60 to 3,600 seconds). It reads aggregate synthetic resource, ambulance and pharmacy data; checks stale/unknown fields and threshold flags; generates review alerts; and persists the run summary and alerts in SQLite. It continues to work without Ollama or an external LLM. No patient-level data is sent to the LLM through the scheduled monitor.

On the **Multi-Agent AI** page, the Autonomous Watch panel shows status, the last/next expected run, alerts, and recent cycle results. Super Admin can pause/resume the schedule and set its interval; Super Admin or Network Admin can run a monitoring cycle immediately. Authenticated users can inspect status and run history. API endpoints are `GET /api/network/autonomous/status`, `GET /api/network/autonomous/runs`, `POST /api/network/autonomous/run`, and `PATCH /api/network/autonomous/settings`.

Autonomous actions are intentionally bounded to aggregate monitoring, deterministic checks, alert creation, and local log writing. Ambulance dispatch, clinical decisions, diagnosis, treatment/prescribing, medicine ordering and stock updates are **not** autonomously executed; they require authorized human review/approval. The monitor uses only synthetic demo data and does not connect to live systems. The initial interval can be set with `ASHA_AUTONOMOUS_INTERVAL_SECONDS` before the first database initialization; after startup, use the Super Admin controls to pause/resume and configure the persisted interval.

## Ambulance Fleet details

Open **Ambulances** in the sidebar. The fleet page reads 90 sample rows from `backend/data/ambulance_fleet_synthetic.csv` and displays vehicle ID, BLS/ALS sample type, status label, sample branch/district, crew label, oxygen, stretcher, patient monitor and defibrillator fields. Search, status and type filters are available. All records are `SYNTHETIC_DEMO_NOT_REAL`; branch affiliation is unverified, GPS is not connected and ETA is not available. The UI must not be used for dispatch. `GET /api/ambulances` returns these explicitly labelled sample records, while resource matching deliberately returns no unverified ambulance dispatch options.

## Pharmacy and resources

- Pharmacy is the only network-specific sidebar section; there is no separate district-directory section in that menu.
- Pharmacy shows available quantity (= stock quantity − reserved quantity), low-stock and expiry alerts, search, and 50-row table paging.
- Staff & Facilities has resource-category selection and 50-row paging. The resource snapshot API returns up to 1,000 sample rows.
- The hospital table shows synthetic sample averages per district placeholder. It is not a live capacity view.

## API overview

- `GET /`, `GET /api/health`
- `GET /api/hospitals`, `GET /api/ambulances`
- `GET /api/dashboard/overview`, `GET /api/dataset/summary`
- `GET /api/resources/summary`, `GET /api/resources/{resource_type}?limit=1000`
- `POST /api/self-doubt`, `POST /api/verify-case`, `POST /api/cross-verify`, `POST /api/match-resources`
- `GET /api/ml/resource-risk/status`, `POST /api/ml/resource-risk/predict`
- `POST /api/network/auth/login`, `POST /api/network/auth/change-password`, `POST /api/network/auth/logout`, `GET /api/network/me`
- `GET/POST /api/network/users` (Super Admin), `PATCH /api/network/users/{username}/active`
- `GET/POST /api/network/branches`, `PATCH /api/network/branches/{branch_id}/verification`
- `GET/POST /api/network/pharmacy/stock`, `PUT /api/network/pharmacy/stock/{stock_id}`, `GET /api/network/pharmacy/summary`
- `GET /api/network/audit-logs`, `GET /api/network/overview`
- `GET /api/network/agents/status`, `POST /api/network/agents/analyze` (authenticated multi-agent demo workflow)
- `GET /api/network/autonomous/status`, `GET /api/network/autonomous/runs`, `POST /api/network/autonomous/run`, `PATCH /api/network/autonomous/settings` (bounded autonomous monitor; admin-controlled)

The login API requires a selected role and rejects any mismatch with the user record. The existing network/pharmacy endpoints enforce role and branch-scope rules. Not all legacy prototype endpoints share this same authorization middleware, so the application must not be exposed publicly until a security review closes that gap.

## Test the prototype

Run the API integration suite from the `backend` folder in a fresh local demo setup:

```powershell
py -m pip install -r requirements-dev.txt
py -m pytest tests -q
```

The suite checks role-required login and rejects role mismatches, health, 10,000-row dataset shape, 1,000 resource snapshots, Lakshmi-only placeholder labelling, 90 ambulance demo rows and equipment fields without claiming live availability, Random Forest behavior/input validation, pharmacy auth/stock count/quantity arithmetic, branch placeholders, audit access, Self-Doubt/cross-verification, invalid stock validation, branch-scoped access, autonomous monitor authentication, persisted cycles, protected schedule controls, and monitor startup under the FastAPI lifespan. If you change the initial Super Admin password, set `ASHA_TEST_PASSWORD` to the current local password before running the suite.

For a small local HTTP latency sample, start the backend and run `py benchmark_api.py --iterations 30` from `backend/`; it prompts for the local Super Admin password unless `ASHA_BENCHMARK_PASSWORD` is set. The output reports median and p95 for selected endpoints, but is not a production load test. Static/API checks do not replace full browser/accessibility tests, penetration testing, clinical validation or production load testing. See `TEST_REPORT.md` for limits.

## Evaluation materials

- `docs/ARCHITECTURE.md` — component boundaries, data flow and trust boundaries
- `docs/EVALUATION_GUIDE.md` — evidence mapped to the supplied 100-point rubric
- `docs/DEMO_WALKTHROUGH.md` — suggested 2-minute screen-recording script
- `TEST_REPORT.md` — automated checks and limitations

A public live prototype URL is not included in this ZIP. For any submission link or audience vote, deploy only a synthetic-data sandbox after security review and provide the actual hosted URL yourself; do not publish credentials or real patient information.

## Required before a real-world pilot

1. Verify each real Lakshmi Hospital branch and obtain written authorization before loading any branch into the network.
2. Integrate only approved, documented hospital/pharmacy feeds; retain source, verification status and last-updated timestamps.
3. Complete authentication/authorization review for every endpoint, MFA, HTTPS, data-at-rest/backups encryption, rate limiting, monitoring, secure recovery, and incident response.
4. Obtain privacy, legal, hospital IT and clinical/safety review. Validate any model on authorized representative data and monitor bias/drift with qualified domain reviewers.
5. Benchmark with representative workloads, test restore procedures, and run browser/device accessibility and security tests.

This is a demo and a starting point for research—not a production hospital information system.
## Login troubleshooting

The login form must show an **assigned role** dropdown before username/password. Select the role tied to the account, then enter credentials. The backend validates the selected role against the actual account role. If an error occurs, the UI displays readable API validation details instead of `[object Object]`. If the role dropdown is missing, close the old frontend window and run the `start_frontend_windows.bat` from this extracted project folder, then hard-refresh the browser (Ctrl+Shift+R).


## Login troubleshooting (role selection / HTTP 422)

- The login form contains exactly one `select#loginRole`.
- The browser request to `/api/network/auth/login` must send JSON with `role`, `username`, and `password`.
- If the server responds with HTTP 422, inspect the response JSON in DevTools → Network → `auth/login` → Response. A missing `role` field is a request-validation error; a wrong role for a valid account should be rejected by authorization.
- After updating the frontend, hard-refresh the browser with `Ctrl+Shift+R`, and make sure the frontend server runs from this extracted project folder.
