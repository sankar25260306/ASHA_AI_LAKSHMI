# ASHA AI — Final Integration Test Report

Test date: 2026-10-24

## Results from this build

- **35 / 35 automated API smoke/integration tests passed** (`python -m pytest tests -q` from `backend/`).
- Python backend compilation passed (`python -m compileall -q backend`).
- Frontend JavaScript syntax passed (`node --check frontend/app.js`).
- Static duplicate-ID check found no duplicate HTML element IDs.
- FastAPI application imported successfully and registered 38 routes.

## Coverage included

1. Root endpoint responds.
2. Health endpoint responds.
3. Login requires explicit role selection and rejects a selected role that does not match the stored account role.
4. Research dataset has 10,000 rows with 8,000 train / 2,000 test split.
5. Resource snapshot API returns 1,000 rows.
6. Resource row limit is capped at 1,000.
7. Hospital list includes only Lakshmi-labelled placeholders and populated sample fields.
8. Ambulance endpoint returns 90 demo fleet records with branch, vehicle type, status, crew and equipment fields; every record is marked unverified and no GPS/ETA is claimed.
9. Random Forest model status endpoint responds.
10. Random Forest demo prediction returns a bounded probability and human-review note.
11. Invalid ML input is rejected with HTTP 422.
12. Pharmacy stock requires authentication.
13. Pharmacy summary requires authentication.
14. Authenticated pharmacy endpoint returns 1,000 records.
15. Available quantity arithmetic and reserved-stock validity are consistent.
16. Pharmacy summary matches the imported stock count.
17. All 38 district placeholders are marked `DEMO_UNVERIFIED`.
18. Super Admin can read audit logs.
19. Resource summary reports the 1,000 resource snapshots.
20. Resource matching returns only Lakshmi-labelled synthetic hospital options and deliberately provides no unverified ambulance dispatch options.
21. Self-Doubt and cross-verification surface sample data-quality checks.
22. Invalid reserved stock is rejected; branch-scoped pharmacy users are restricted to their assigned branch and cannot create stock for another branch.
23. Multi-agent runtime is authenticated and does not expose API-key configuration.
27. Autonomous monitoring status/run history require authentication; admin can trigger a bounded cycle.
28. Automated monitor persists cycle records and returns synthetic-data alerts plus required human-review flags.
29. Ambulance dispatch, clinical decision/treatment, and pharmacy order/stock mutation are explicitly not performed by autonomous cycles.
30. Only Super Admin can update autonomous scheduling; branch pharmacy roles are rejected.
24. Multi-agent analysis reads all three demo sources, requires human review, and labels output synthetic.
25. Unsupported agent tasks are rejected.
26. Branch-scoped agent requests cannot analyze other districts.

## Test environment and limits

These tests are API integration/smoke checks using FastAPI's TestClient and the bundled synthetic data. The browser was not manually exercised end to end, and this is not a public deployment, formal penetration test, production load test, clinical validation, or accessibility certification. Use `backend/benchmark_api.py` with the backend running to collect a local HTTP latency snapshot; report the machine, iterations and endpoint sizes with any benchmark values.

The 90 ambulance fleet rows are also synthetic; the page includes vehicle-type/status filters and onboard equipment labels, but no real GPS or ETA. All resource and pharmacy rows are synthetic. The 38 district entries do not verify that Lakshmi Hospital has a branch in each district. There is no real hospital feed, live pharmacy system, patient data, ambulance GPS or dispatch connection. The existing legacy APIs have not all been placed behind the newer network-role authorization system; do not expose the prototype publicly before a full security review.


## Multi-agent regression tests

Additional automated checks cover authenticated runtime status, absence of API-key disclosure, an authorized synthetic multi-agent analysis using the resource/pharmacy CSV/SQLite data, required human review, and rejection of unsupported analysis types. These tests do not require the optional LLM to be installed; the deterministic fallback path is intentionally testable offline.


## Autonomous-monitor tests

The current suite verifies authenticated monitoring status and run history, an admin-triggered bounded run, persistence of run/alert data, required synthetic labels and human review, explicit non-execution of dispatch/clinical/pharmacy mutations, and Super Admin-only scheduling controls, plus a background cycle during FastAPI startup/shutdown lifespan. The server's background loop starts on application startup and is expected to run every 300 seconds by default. TestClient's endpoint checks do not replace a separate long-running manual test of scheduler timing under real Uvicorn.
## Login error display fix (2026-10-24)
- Frontend now converts FastAPI validation error arrays/objects into readable messages instead of `[object Object]`.
- Login requires an explicit role selection and backend checks selected role against the stored account role.
- If an old frontend without the role selector is paired with the role-validated backend, the UI now directs the operator to use the current role-based package.
- Frontend JavaScript syntax and backend automated tests were rechecked after this fix.


## Login HTML correction (2026-10-24)
- Removed the duplicated `loginRole` dropdown from the provided HTML and retained one role selector.
- Updated the `app.js` query-string version to force browsers to fetch the corrected login handler instead of using an older cached frontend script.
- Static check confirms `loginRole`, `loginUsername`, and `loginPassword` each appear exactly once in the HTML.
- Re-tested: 35/35 backend tests pass; Python compilation and JavaScript syntax checks pass.
