# ASHA AI — Project Judging Rubric Alignment

This guide maps the provided 100-point evaluation rubric to concrete demo evidence. It separates current prototype features from work still needed for production.

## 1. Technical Execution — 25 points

**Code quality / clean architecture (10):** Demonstrate the frontend/API/data-service split: `frontend/`, `backend/app/main.py`, `backend/app/network_pharmacy.py`, and `backend/data/`. Explain how Pydantic validates input and how the pharmacy import uses a version marker to avoid duplicate imports.

**Performance / latency (10):** Demonstrate 1,000-row API responses and the 50-row frontend paging controls. For any benchmark slide, measure several local requests and report the measured median/p95 with the machine, dataset size and method. Do not claim production latency from local TestClient timing.

**Testing / error handling (5):** Run the smoke suite (instructions in README). It covers health, dataset counts, API limits, Lakshmi-only placeholders, ML bounds, authentication, pharmacy quantity arithmetic, and summaries. Add browser-based regression checks before claiming full UI test coverage. Current automated suite includes multi-agent status, source integration, role scope, task validation, autonomous cycle persistence, protected scheduling controls and a background cycle on FastAPI startup; it does not verify remote/local LLM output unless a model is configured.

## 2. Innovation & Novelty — 25 points

**Core concept (10):** ASHA AI combines emergency logistics coordination with a Self-Doubt Engine that explicitly surfaces missing, stale, or conflicting data rather than silently guessing.

**Creative problem-solving (10):** Explain how data freshness, cross-verification, human review, branch-scoped roles and low-stock/expiry flags reduce unverified assumptions in the prototype workflow.

**Technology integration (5):** Show FastAPI validation/API integration, SQLite pharmacy inventory, the Random Forest model in AI Recommendations, the specialist multi-agent workflow with optional LLM explanations, and the bounded autonomous monitor. The monitor runs on backend startup and every five minutes by default; it records synthetic-data quality/threshold alerts without performing real dispatch, clinical decisions, orders or stock changes. Clearly state that the model was trained on generated labels and is not validated for real resource-shortage forecasting.

## 3. Real-World Impact — 20 points

**Practical user value (10):** Intended users include hospital operations staff, pharmacy staff, dispatch coordinators and auditors. Use synthetic demo data to demonstrate their workflow.

**Impact metrics (5):** Propose pilot measurements rather than inventing results: time to locate an available resource, percentage of stale records flagged, pharmacy low-stock alert precision/recall, update completion time, and number of cross-verification conflicts found. Collect only after authorized pilot approval.

**Deployment / scalability (5):** The current version is a local prototype. Production preparation still requires authorized verified branch data, identity provider/MFA, HTTPS, data-at-rest encryption, rate limiting, monitoring, role review, backups, threat modeling, privacy/legal review and clinical/safety validation.

## 4. Working Demo & Documentation — 20 points

**Working prototype link (10):** This ZIP runs locally. No public live link is included. Deploy only a sandbox with synthetic data after a security review; add the resulting verified URL to the submission yourself.

**README / architecture (5):** Use `README.md` and `docs/ARCHITECTURE.md` for install steps, project structure, API routes and data flows.

**Demo video / walkthrough (5):** Follow `docs/DEMO_WALKTHROUGH.md`; record the app running locally and keep synthetic-data banners visible.

## 5. Audience voting — 10 points

Prepare a short project description, safe demo video, and a reachable sandbox link when the event organizer opens voting. Do not solicit or simulate votes, and do not publish patient data, passwords, or a deployment with unprotected legacy endpoints.
