# ASHA AI — Final project handoff

## Included
- Lakshmi-only UI scope; the network-specific sidebar item is **Pharmacy** only.
- Responsive dashboard and 50-row pagination for pharmacy and resource data.
- 1,000 synthetic pharmacy records imported into SQLite on first startup.
- 1,000 synthetic hospital resource snapshots connected to `/api/resources/snapshots`.
- Existing 10,000-row synthetic research dataset (8,000 train / 2,000 test metadata).
- Random Forest shortage-pattern demo panel, Self-Doubt Engine, cross-verification, demo resource matching, low-stock/expiry flags, login/roles and audit trail.
- Project evaluation guide, architecture documentation, demo-video script, test suite and local latency benchmark tool.

## Windows quick start
1. Extract the ZIP.
2. Double-click `start_backend_windows.bat` and leave the server window open.
3. Double-click `start_frontend_windows.bat`.
4. Browse to `http://127.0.0.1:5173`; API docs: `http://127.0.0.1:8000/docs`.
5. Fresh database demo login: `superadmin` / `ASHA-Demo-2026!`; change the password at first login.

## Verified in this build
- 21/21 automated API smoke/integration tests passed.
- Python compile and JavaScript syntax checks passed.
- 1,000 pharmacy rows and 1,000 resource rows validated; no quantity arithmetic inconsistencies found.
- Browser/device manual testing, production load testing, penetration testing and clinical validation are not complete.

## Safety and truth in data
All medicine, staff, equipment, blood, ambulance, bed and resource values are synthetic placeholders. The 38 district entries are not verified Lakshmi Hospital branches. The Ambulance Fleet page now displays 90 clearly labelled synthetic vehicle records, with type/status/equipment details and filters; there is still no live hospital or ambulance feed, GPS or ETA. Not for medicine dispensing, patient care, clinical decisions, real dispatch or operational resource allocation. Legacy APIs still need a full auth/security review before any public deployment.


## Login flow update

The login form now requires the user to select their assigned role first. Username and password fields stay disabled until a role is selected and are never prefilled. The backend requires the selected role and only issues a session if it exactly matches the role stored for that username. Selecting a higher-privilege role does not grant those privileges. Automated test suite: 25 passed.


## Bounded autonomous mode

The final build includes scheduled autonomous monitoring, persisted run logs, data-quality/threshold review alerts, admin pause/resume/interval controls, and explicit restrictions against real dispatch, clinical decisions, medicine orders or stock changes. Default interval: 300 seconds. All monitored data remains synthetic/unverified.
