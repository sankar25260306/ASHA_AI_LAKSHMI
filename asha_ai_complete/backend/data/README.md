# ASHA AI — Lakshmi-only synthetic data inventory

**All records are generated placeholders. They are not verified Lakshmi Hospital franchises or actual stock. Do not use for patient care, dispensing, emergency decisions or dispatch.**

## Active data connected to the UI/API
- `asha_ai_synthetic_dataset_10000.csv` — 10,000 synthetic research/event rows; 8,000/2,000 train/test metadata.
- `asha_lakshmi_pharmacy_1000_demo.csv` — 1,000 synthetic pharmacy records. This is the active first-startup seed used by `backend/app/network_pharmacy.py`.
- `asha_lakshmi_hospital_resources_1000_demo.csv` — 1,000 synthetic resource snapshots used by `/api/resources/snapshots`, summary cards, district resource samples and demo matching.
- `lakshmi_branch_directory_38_demo.csv` — 38 unverified district placeholders, not proof of branch presence.
- `train_8000.csv` and `test_2000.csv` — synthetic research split.

## Older offline archive files
- `lakshmi_pharmacy_inventory_10000_demo.csv` and `asha_ai_lakshmi_network_10000_demo.sqlite` are retained as legacy/offline research artifacts. The current network pharmacy seeder prefers the explicit 1,000-row pharmacy CSV, and the live demo API does not load the legacy 10,000-row inventory file when the 1,000-row file is present.

## Data semantics
- `DEMO_UNVERIFIED`, `SYNTHETIC_DEMO_NOT_REAL` and `NOT_FOR_REAL_PATIENT_CARE` identify fictional data.
- Branch IDs are synthetic. The 38-district sample intentionally does not claim Lakshmi Hospital operates in every district.
- Quantity and expiry values are randomly generated demo values, not current pharmacy stock.
- Replace placeholders only after official branch verification, written authorization and secure data integration.
