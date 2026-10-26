# ASHA AI — 2-minute demo walkthrough script

Use only the bundled synthetic records. Keep the “LAKSHMI-ONLY NETWORK” and “DEMO DATA” warnings visible while recording.

1. **Opening (0:00–0:15):** “ASHA AI is a research prototype for uncertainty-aware emergency resource coordination. All displayed data is synthetic.”
2. **Dashboard (0:15–0:35):** Show the resource summary and explain that 38 district entries are placeholders, not verified Lakshmi Hospital branches.
3. **Pharmacy (0:35–1:00):** Sign in with the local demo account, change the bootstrap password, open Pharmacy, show 1,000 records, page controls, search, low-stock filter and expiry labels.
4. **Ambulance Fleet (1:00–1:20):** Show the 90 demo vehicle records, BLS/ALS type, availability/maintenance statuses, crew labels, oxygen/stretcher/monitor/defibrillator fields and search filters. Emphasize that GPS/ETA is not connected and no dispatch option is returned.
5. **Self-Doubt Engine (1:20–1:40):** Submit a sample-only emergency case with missing measurements. Show the missing information and human verification actions.
6. **AI/ML (1:40–1:55):** Open AI Recommendations and run the Random Forest demo analysis. State that it predicts generated synthetic labels and is not a clinically validated or operational forecast.
7. **API/docs (1:55–2:10):** Briefly show `/docs`, the 1,000-row resource snapshot endpoint, and the 10,000-row research dataset summary.

Closing: “The next steps are authorized branch verification, historical data validation, and a security/clinical review before any real-world pilot.”


## Multi-Agent AI addition (30–45 seconds)

1. Open **Multi-Agent AI** and show whether the configured local LLM is available; explain that the rule-based specialists remain usable if the LLM is offline.
2. Choose `Network readiness overview` and `Coimbatore`, then run the workflow.
3. Show each specialist card, aggregate metrics, verification findings, and whether the final explanation came from the LLM or deterministic fallback.
4. Point out the audit log, synthetic-data banner, and human-review rule. Do not describe demo snapshots as confirmed Lakshmi Hospital operations.


## Autonomous Monitor walkthrough (30–45 seconds)

1. Open **Multi-Agent AI** and show the **Autonomous Watch** panel. Explain the background monitor runs on startup, then every five minutes by default, even if an LLM is unavailable.
2. Click **Run monitoring now** as Super Admin or Network Admin. Show the cycle ID, resource/pharmacy/fleet metrics, threshold alerts, and persisted run log.
3. As Super Admin, pause and resume monitoring to demonstrate safe scheduling controls. The interval can be configured between 60 and 3,600 seconds.
4. Highlight the boundary: it creates local review alerts only; it does not dispatch ambulances, make clinical decisions, place pharmacy orders or update stock. All inputs are synthetic demo data, not real hospital feeds.
