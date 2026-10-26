
from datetime import datetime, timezone
from typing import Optional
from pathlib import Path
import asyncio
from contextlib import asynccontextmanager
import joblib
import pandas as pd
from fastapi import HTTPException
from pydantic import BaseModel, Field
from fastapi import FastAPI
from pydantic import BaseModel, Field
from fastapi.middleware.cors import CORSMiddleware

@asynccontextmanager
async def app_lifespan(application):
    """Run bounded synthetic-data monitoring while the API server is alive."""
    from .autonomous import autonomous_monitor_loop, ensure_tables
    ensure_tables()
    monitor_task = asyncio.create_task(autonomous_monitor_loop(), name="asha-ai-bounded-autonomous-monitor")
    application.state.autonomous_monitor_task = monitor_task
    try:
        yield
    finally:
        monitor_task.cancel()
        try:
            await monitor_task
        except asyncio.CancelledError:
            pass

app = FastAPI(
    title="ASHA AI API",
    description=(
        "Hackathon prototype for uncertainty-aware emergency "
        "coordination. Simulated data only; not clinical advice."
    ),
    version="0.3.0",
    lifespan=app_lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------------------------------------
# SIMULATED DATA ONLY — NOT LIVE AVAILABILITY
# --------------------------------------------------

AMBULANCES = [
    {
        "id": "AMB-001",
        "area": "Dindigul",
        "available": True,
        "eta_minutes": 8,
        "equipment": ["oxygen", "first_aid"],
    },
    {
        "id": "AMB-002",
        "area": "Natham",
        "available": True,
        "eta_minutes": 12,
        "equipment": ["oxygen", "stretcher"],
    },
    {
        "id": "AMB-003",
        "area": "Madurai",
        "available": False,
        "eta_minutes": None,
        "equipment": ["oxygen", "ventilator"],
    },
]

# No generic/non-Lakshmi hospitals are part of the Lakshmi-only network.
HOSPITALS = []

# --------------------------------------------------
# REQUEST MODEL
# --------------------------------------------------

class EmergencyCase(BaseModel):
    area: str = Field(min_length=1, max_length=100)
    age: Optional[int] = Field(default=None, ge=0, le=120)
    symptoms: list[str] = Field(default_factory=list)
    heart_rate: Optional[int] = Field(
        default=None, ge=0, le=300
    )
    spo2: Optional[float] = Field(
        default=None, ge=0, le=100
    )
    temperature_c: Optional[float] = Field(
        default=None, ge=25, le=45
    )
    needs_icu: bool = False


# --------------------------------------------------
# SELF-DOUBT ENGINE
# --------------------------------------------------

def analyze_uncertainty(case: EmergencyCase) -> dict:
    issues = []
    verification_actions = []

    # 1. Missing information
    if not case.area.strip():
        issues.append("The location is blank.")
        verification_actions.append(
            "Confirm the location."
        )

    if case.age is None:
        issues.append("Age is missing.")
        verification_actions.append(
            "Confirm age if possible."
        )

    if not case.symptoms or not any(
        symptom.strip() for symptom in case.symptoms
    ):
        issues.append("Symptoms are missing.")
        verification_actions.append(
            "Ask for symptom information if possible."
        )

    if case.heart_rate is None:
        issues.append("Heart-rate reading is missing.")
        verification_actions.append(
            "Verify the measurement or mark it unavailable."
        )

    if case.spo2 is None:
        issues.append("SpO2 reading is missing.")
        verification_actions.append(
            "Verify the measurement or mark it unavailable."
        )

    if case.temperature_c is None:
        issues.append("Temperature reading is missing.")
        verification_actions.append(
            "Verify the measurement or mark it unavailable."
        )

    # 2. Potentially implausible measurements.
    # These are data-quality flags, not diagnostic thresholds.
    if case.heart_rate is not None:
        if case.heart_rate == 0:
            issues.append(
                "Heart-rate value is zero; verify the device and reading."
            )
            verification_actions.append(
                "Check the heart-rate device and measurement."
            )
        elif case.heart_rate < 20 or case.heart_rate > 250:
            issues.append(
                "Heart-rate value is outside the prototype's "
                "plausibility-check range."
            )
            verification_actions.append(
                "Urgently request qualified human assessment "
                "and verify the reading."
            )

    if case.spo2 is not None:
        if case.spo2 == 0:
            issues.append(
                "SpO2 value is zero; verify the device and reading."
            )
            verification_actions.append(
                "Check the sensor and obtain qualified assessment."
            )

    if case.temperature_c is not None:
        if case.temperature_c < 30 or case.temperature_c > 43:
            issues.append(
                "Temperature value is outside the prototype's "
                "plausibility-check range."
            )
            verification_actions.append(
                "Verify the measurement and request qualified "
                "human assessment."
            )

    # 3. Check for duplicate or blank symptom entries.
    cleaned_symptoms = [
        symptom.strip().lower()
        for symptom in case.symptoms
        if symptom.strip()
    ]

    if len(cleaned_symptoms) != len(set(cleaned_symptoms)):
        issues.append("Duplicate symptom entries were found.")
        verification_actions.append(
            "Review the symptom list for duplicates."
        )

    if any(not symptom.strip() for symptom in case.symptoms):
        issues.append("A blank symptom entry was found.")
        verification_actions.append(
            "Remove blank symptom entries."
        )

    # 4. Check freshness/unknown oxygen against the bundled synthetic snapshots.
    # These findings are demo quality signals, not claims about real hospital branches.
    stale_samples, unknown_oxygen_samples = sample_resource_quality_signals()

    if stale_samples:
        issues.append(
            "Some synthetic district resource snapshots are stale (over 30 minutes): "
            + ", ".join(stale_samples[:8])
            + (" and others." if len(stale_samples) > 8 else ".")
        )
        verification_actions.append(
            "Verify current resource status with an authorized hospital contact."
        )

    if unknown_oxygen_samples:
        issues.append(
            "Oxygen status is unknown in synthetic samples for: "
            + ", ".join(unknown_oxygen_samples[:8])
            + (" and others." if len(unknown_oxygen_samples) > 8 else ".")
        )
        verification_actions.append(
            "Verify oxygen availability with an authorized source before relying on it."
        )

    # Avoid duplicate action messages.
    verification_actions = list(dict.fromkeys(
        verification_actions
    ))

    return {
        "engine": "ASHA_SELF_DOUBT_ENGINE",
        "data_type": "PROTOTYPE_RULES_NOT_CLINICAL_ADVICE",
        "uncertainty_detected": bool(issues),
        "uncertainty_count": len(issues),
        "uncertainties": issues,
        "verification_actions": verification_actions,
        "human_review_required": True,
        "clinical_confidence_score": None,
        "message": (
            "Uncertainty detected. Verify information and request "
            "qualified human review."
            if issues
            else
            "No issues detected by these limited checks. "
            "This does not establish clinical safety."
        ),
    }


# Keep the original verification function available.
def verify_case(case: EmergencyCase) -> list[str]:
    result = analyze_uncertainty(case)
    return result["uncertainties"]


# --------------------------------------------------
# DATASET-BACKED SYNTHETIC RESOURCE VIEWS
# --------------------------------------------------
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATASET_PATH = DATA_DIR / "asha_ai_synthetic_dataset_10000.csv"
HOSPITAL_DIRECTORY_PATH = DATA_DIR / "hospital_directory_30_synthetic.csv"
RESOURCE_FILES = {
    "doctors": "doctors_synthetic.csv", "nurses": "nurses_synthetic.csv",
    "beds": "beds_synthetic.csv", "blood": "blood_inventory_synthetic.csv",
    "ambulances": "ambulance_fleet_synthetic.csv", "equipment": "medical_equipment_synthetic.csv",
    "medicines": "medicine_inventory_synthetic.csv",
    "snapshots": "asha_lakshmi_hospital_resources_1000_demo.csv",
}

def _canonical_lakshmi_branch_ids(frame: pd.DataFrame) -> pd.DataFrame:
    """Normalize snapshot rows to the demo branch IDs used by the network module."""
    if "district" not in frame.columns:
        return frame
    from .network_pharmacy import DISTRICTS
    district_to_id = {district: f"LHN-TN-{i:02d}" for i, district in enumerate(DISTRICTS, 1)}
    district_aliases = {"Villupuram": "Viluppuram"}
    frame["district"] = frame["district"].replace(district_aliases)
    if "branch_id" in frame.columns:
        frame["source_branch_id_demo"] = frame["branch_id"].astype(str)
        frame["branch_id"] = frame["district"].map(district_to_id).fillna("UNMAPPED_DEMO")
        frame["hospital_id"] = frame["branch_id"]
    if "hospital_name" not in frame.columns:
        frame["hospital_name"] = frame["district"].astype(str).map(lambda d: f"Lakshmi Hospital — {d} District (DEMO PLACEHOLDER; NOT VERIFIED)")
    frame["branch_verification_status"] = "DEMO_UNVERIFIED"
    return frame

def load_resource_file(key: str):
    filename = RESOURCE_FILES.get(key)
    if not filename:
        raise HTTPException(status_code=404, detail="Unknown resource type")
    path = DATA_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=503, detail=f"Synthetic resource file missing: {filename}")
    frame = pd.read_csv(path).fillna("")
    # Strict Lakshmi-only filter: generic/other-network rows are never returned.
    if "hospital_id" in frame.columns:
        frame = frame[frame["hospital_id"].astype(str).str.startswith("LHN-")]
    if "branch_id" in frame.columns:
        frame = frame[frame["branch_id"].astype(str).str.startswith("LHN-") | frame["branch_id"].astype(str).str.startswith("LHN-TN-DEMO-")]
    if key == "snapshots":
        frame = _canonical_lakshmi_branch_ids(frame)
    if "hospital_name" in frame.columns:
        frame = frame[frame["hospital_name"].astype(str).str.contains("Lakshmi Hospital", case=False, na=False)]
    return frame.reset_index(drop=True)

def resource_payload(key: str, limit: int = 100, hospital_id: Optional[str] = None, district: Optional[str] = None):
    frame = load_resource_file(key)
    if hospital_id:
        if "hospital_id" in frame.columns:
            frame = frame[frame["hospital_id"].astype(str) == hospital_id]
        elif "branch_id" in frame.columns:
            frame = frame[frame["branch_id"].astype(str) == hospital_id]
    if district and "district" in frame.columns:
        frame = frame[frame["district"].astype(str).str.casefold() == district.casefold()]
    total = len(frame)
    frame = frame.head(max(1, min(limit, 1000)))
    return {"data_type": "SYNTHETIC_LAKSHMI_PLACEHOLDERS_NOT_REAL", "total": total, "items": frame.to_dict(orient="records"), "notice": "All records are synthetic Lakshmi-network placeholders; branch affiliation and resource availability are unverified."}


def sample_resource_quality_signals() -> tuple[list[str], list[str]]:
    """Return district-level warnings derived only from synthetic snapshots."""
    try:
        frame = load_resource_file("snapshots")
    except HTTPException:
        return [], []
    if frame.empty or "district" not in frame.columns:
        return [], []
    district_values = frame["district"].astype(str)
    stale = set()
    unknown_oxygen = set()
    if "last_updated_minutes_ago" in frame.columns:
        ages = pd.to_numeric(frame["last_updated_minutes_ago"], errors="coerce")
        stale = set(district_values[ages > 30].tolist())
    if "oxygen_status" in frame.columns:
        oxygen = frame["oxygen_status"].astype(str).str.upper()
        unknown_oxygen = set(district_values[oxygen == "UNKNOWN"].tolist())
    return sorted(stale), sorted(unknown_oxygen)


def load_synthetic_dataset():
    if not DATASET_PATH.exists():
        raise HTTPException(status_code=503, detail="Synthetic dataset missing from backend/data.")
    return pd.read_csv(DATASET_PATH)

def dataset_hospitals():
    frame = load_synthetic_dataset()
    directory = pd.read_csv(HOSPITAL_DIRECTORY_PATH).set_index("hospital_id")
    frame["hospital_name"] = frame["hospital_id"].map(directory["hospital_name"]).fillna("Synthetic Hospital")
    # Most recent generated snapshot per fictional hospital. Values remain synthetic.
    frame = frame.sort_values("event_timestamp_utc", ascending=False).drop_duplicates("hospital_id")
    items = []
    for _, r in frame.iterrows():
        age = int(r.get("data_age_minutes", 0))
        oxygen = "available (synthetic)" if int(r.get("oxygen_level_pct", 0)) >= 20 else "low (verify)"
        items.append({
            "id": str(r["hospital_id"]),
            "name": str(r.get("hospital_name", "Synthetic Hospital")),
            "area": str(r["district"]),
            "beds": int(r["available_beds"]),
            "icu_beds": int(r["available_icu_beds"]),
            "oxygen": oxygen,
            "updated_minutes_ago": age,
            "total_beds": int(r["total_beds"]),
            "total_icu_beds": int(r["total_icu_beds"]),
            "verification_status": str(r["verification_status"]),
            "data_label": "SYNTHETIC_DEMO_NOT_REAL",
        })
    return items

def dataset_ambulances(limit=30):
    frame = load_synthetic_dataset().sort_values("event_timestamp_utc", ascending=False).head(limit)
    items = []
    for i, (_, r) in enumerate(frame.iterrows(), start=1):
        available = int(r.get("ambulances_available", 0)) > 0
        items.append({
            "id": f"SYN-AMB-SNAPSHOT-{i:03d}",
            "area": str(r["district"]),
            "available": available,
            "eta_minutes": None,
            "equipment": ["synthetic resource snapshot"],
            "status_sample": str(r["ambulance_status_sample"]),
            "data_label": "SYNTHETIC_DEMO_NOT_REAL",
        })
    return items

# --------------------------------------------------
# EXISTING API ENDPOINTS
# --------------------------------------------------

@app.get("/")
def root():
    return {
        "project": "ASHA AI",
        "status": "running",
        "notice": (
            "Prototype only. All resource records are simulated."
        ),
        "docs": "/docs",
    }


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "timestamp_utc": datetime.now(
            timezone.utc
        ).isoformat(),
    }


@app.get("/api/ambulances")
def list_ambulances():
    """Return the fictional Lakshmi-only demo fleet with explicit verification labels.

    The records are useful for UI/testing only. They do not represent confirmed
    Lakshmi Hospital vehicles, GPS positions, live availability, or dispatch ETA.
    """
    frame = load_resource_file("ambulances")
    items = []

    def as_bool(value):
        if isinstance(value, bool):
            return value
        return str(value).strip().casefold() in {"true", "1", "yes", "y"}

    for _, row in frame.iterrows():
        status = str(row.get("status", "unknown")).strip().casefold()
        hospital_name = str(row.get("hospital_name", "Lakshmi Hospital (DEMO PLACEHOLDER)"))
        area = hospital_name.split("—", 1)[-1].split(" District", 1)[0].strip() if "—" in hospital_name else "Unverified demo area"
        equipment = {
            "oxygen": as_bool(row.get("oxygen", False)),
            "stretcher": as_bool(row.get("stretcher", False)),
            "patient_monitor": as_bool(row.get("patient_monitor", False)),
            "defibrillator": as_bool(row.get("defibrillator", False)),
        }
        items.append({
            "id": str(row.get("ambulance_id", "SYN-AMB-UNKNOWN")),
            "hospital_id": str(row.get("hospital_id", "")),
            "hospital_name": hospital_name,
            "area": area,
            "ambulance_type": str(row.get("ambulance_type", "UNKNOWN")),
            "status": status,
            "available": status == "available",
            "crew_demo": str(row.get("crew_demo", "Unspecified demo crew")),
            "equipment": equipment,
            "gps_status": str(row.get("gps_demo", "Not connected")),
            "location_verified": False,
            "eta_minutes": None,
            "branch_verification_status": "DEMO_UNVERIFIED",
            "data_label": "SYNTHETIC_DEMO_NOT_REAL",
        })

    return {
        "network": "Lakshmi Hospital Network (DEMO ONLY)",
        "data_type": "SYNTHETIC_LAKSHMI_PLACEHOLDERS_NOT_REAL",
        "count": len(items),
        "items": items,
        "notice": (
            "These are fictional Lakshmi-network placeholder records. Branch affiliation, vehicles, "
            "crew, equipment, status and location are unverified; GPS is not connected and no live ETA "
            "is available. Do not use for actual emergency dispatch."
        ),
    }


@app.get("/api/hospitals")
def list_hospitals():
    # Enrich branch placeholders with sample resource snapshots for a usable demo table.
    # Every resource value remains synthetic and is explicitly labelled as such.
    from . import network_pharmacy as lhn
    c = lhn.db()
    rows = [dict(r) for r in c.execute(
        "SELECT branch_id AS id, display_name AS name, district AS area, verification_status, active, updated_at FROM branches ORDER BY district"
    )]
    c.close()
    snapshots = load_resource_file("snapshots")
    if not snapshots.empty:
        for row in rows:
            subset = snapshots[snapshots["district"].astype(str).str.casefold() == str(row["area"]).casefold()]
            if subset.empty:
                row.update({"beds": 0, "icu_beds": 0, "oxygen": "unknown", "updated_minutes_ago": None})
                continue
            def mean_int(column):
                if column not in subset.columns:
                    return 0
                return int(round(pd.to_numeric(subset[column], errors="coerce").fillna(0).mean()))
            row["beds"] = mean_int("available_beds")
            row["total_beds"] = mean_int("total_beds")
            row["icu_beds"] = mean_int("available_icu_beds")
            row["total_icu_beds"] = mean_int("total_icu_beds")
            if "oxygen_status" in subset.columns:
                mode = subset["oxygen_status"].astype(str).mode()
                row["oxygen"] = str(mode.iloc[0]) if not mode.empty else "unknown"
            else:
                row["oxygen"] = "unknown"
            if "last_updated_minutes_ago" in subset.columns:
                row["updated_minutes_ago"] = int(round(pd.to_numeric(subset["last_updated_minutes_ago"], errors="coerce").fillna(0).median()))
            else:
                row["updated_minutes_ago"] = None
            row["data_label"] = "SYNTHETIC_DEMO_NOT_REAL"
    return {
        "network": "Lakshmi Hospital Network",
        "data_type": "DEMO_UNVERIFIED",
        "items": rows,
        "count": len(rows),
        "notice": "Lakshmi-only district placeholders enriched with illustrative sample averages. Branch affiliations and resource availability are unverified; not live hospital data.",
    }


@app.post("/api/verify-case")
def verify_emergency_case(case: EmergencyCase):
    result = analyze_uncertainty(case)
    result["verification_status"] = (
        "needs_review"
        if result["uncertainty_detected"]
        else "basic_checks_passed"
    )
    return result


# New dedicated Self-Doubt Engine endpoint
@app.post("/api/self-doubt")
def self_doubt(case: EmergencyCase):
    return analyze_uncertainty(case)


@app.post("/api/match-resources")
def match_resources(case: EmergencyCase):
    """Rank district resource snapshots for a sandbox demonstration only."""
    frame = load_resource_file("snapshots")
    options = []
    if not frame.empty:
        for district, group in frame.groupby("district", dropna=False):
            def avg_int(column):
                if column not in group.columns:
                    return 0
                return int(round(pd.to_numeric(group[column], errors="coerce").fillna(0).mean()))
            age = avg_int("last_updated_minutes_ago")
            oxygen_values = group.get("oxygen_status", pd.Series(dtype=str)).astype(str).str.upper().mode()
            oxygen = str(oxygen_values.iloc[0]) if not oxygen_values.empty else "UNKNOWN"
            beds = avg_int("available_beds")
            icu_beds = avg_int("available_icu_beds")
            suitable = icu_beds > 0 if case.needs_icu else beds > 0
            fresh = age <= 30
            same_area = str(district).casefold() == case.area.strip().casefold()
            options.append({
                "id": f"LHN-DEMO-{str(district).upper().replace(' ', '-')}",
                "name": f"Lakshmi Hospital — {district} District (DEMO PLACEHOLDER; NOT VERIFIED)",
                "area": str(district),
                "beds": beds,
                "icu_beds": icu_beds,
                "oxygen": oxygen,
                "updated_minutes_ago": age,
                "freshness_status": "RECENT_SAMPLE_VERIFY" if fresh else "STALE_SAMPLE_VERIFY",
                "suitability_for_requested_resource": suitable,
                "rank_eligible": bool(fresh and suitable and oxygen == "AVAILABLE"),
                "branch_verification_status": "DEMO_UNVERIFIED",
                "same_area_as_request": same_area,
                "data_label": "SYNTHETIC_DEMO_NOT_REAL",
            })
    options.sort(key=lambda row: (
        not row["same_area_as_request"],
        not row["rank_eligible"],
        not row["suitability_for_requested_resource"],
        row["updated_minutes_ago"],
    ))
    return {
        "data_type": "SYNTHETIC_LAKSHMI_PLACEHOLDERS_NOT_REAL",
        "requested_area": case.area,
        "ambulance_options": [],
        "hospital_options": options[:10],
        "human_confirmation_required": True,
        "notice": (
            "Options are ranked from synthetic district snapshots only. No Lakshmi Hospital branch or resource status is verified. "
            "No ambulance fleet is verified or connected, so no ambulance option is returned. This is not for real dispatch or clinical use."
        ),
    }

# --------------------------------------------------
# MULTI-AGENT CROSS-VERIFICATION
# --------------------------------------------------

@app.post("/api/cross-verify")
def cross_verify(case: EmergencyCase):
    # Agent 1: Patient data checks
    patient_issues = []

    if case.age is None:
        patient_issues.append("Age is missing.")

    if not case.symptoms or not any(
        symptom.strip() for symptom in case.symptoms
    ):
        patient_issues.append("Symptoms are missing.")

    if case.heart_rate is None:
        patient_issues.append("Heart-rate reading is missing.")

    if case.spo2 is None:
        patient_issues.append("SpO2 reading is missing.")

    if case.temperature_c is None:
        patient_issues.append("Temperature reading is missing.")

    # Agent 2: synthetic resource snapshot quality checks
    resource_issues = []
    stale_samples, unknown_oxygen_samples = sample_resource_quality_signals()
    resource_issues.extend(
        f"{district}: synthetic resource snapshot is stale." for district in stale_samples[:12]
    )
    resource_issues.extend(
        f"{district}: oxygen status is unknown in synthetic snapshots." for district in unknown_oxygen_samples[:12]
    )

    # Agent 3: Safety and consensus
    all_issues = list(dict.fromkeys(
        patient_issues + resource_issues
    ))

    return {
        "engine": "ASHA_MULTI_AGENT_CROSS_VERIFICATION",
        "data_type": "SIMULATED_RULES_ONLY",
        "agents": [
            {
                "agent": "patient_data_agent",
                "status": (
                    "needs_review" if patient_issues
                    else "basic_checks_passed"
                ),
                "findings": patient_issues,
            },
            {
                "agent": "hospital_resource_agent",
                "status": (
                    "needs_review" if resource_issues
                    else "basic_checks_passed"
                ),
                "findings": resource_issues,
            },
            {
                "agent": "safety_agent",
                "status": (
                    "needs_review" if all_issues
                    else "basic_checks_passed"
                ),
                "findings": all_issues,
            },
        ],
        "total_findings": len(all_issues),
        "human_review_required": True,
        "message": (
            "Uncertainty found. Verify information with "
            "appropriate human staff."
            if all_issues
            else
            "Basic checks passed; human confirmation is still required."
        ),
        "notice": (
            "Prototype only. This is not clinical advice and "
            "resource records are simulated."
        ),
    }

CLINICAL_MODEL_PATH = (
    Path(__file__).resolve().parent / "clinical_baseline.joblib"
)


class ResearchPredictionRequest(BaseModel):
    features: dict[str, float] = Field(
        ...,
        description="Numeric feature values from the trained dataset",
    )


@app.post("/api/research/clinical-baseline")
def clinical_baseline_prediction(request: ResearchPredictionRequest):
    if not CLINICAL_MODEL_PATH.exists():
        raise HTTPException(
            status_code=503,
            detail="Train the clinical baseline model first.",
        )

    bundle = joblib.load(CLINICAL_MODEL_PATH)
    model = bundle["model"]
    feature_names = bundle["features"]

    missing = [
        name for name in feature_names
        if name not in request.features
    ]
    extra = [
        name for name in request.features
        if name not in feature_names
    ]

    if missing or extra:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Feature names must match the trained model.",
                "missing_features": missing,
                "unexpected_features": extra,
            },
        )

    row = pd.DataFrame(
        [[request.features[name] for name in feature_names]],
        columns=feature_names,
    )

    probability = float(model.predict_proba(row)[0][1])
    prediction = int(model.predict(row)[0])

    return {
        "engine": "ASHA_RESEARCH_BASELINE",
        "dataset": "UCI Heart Disease",
        "predicted_dataset_label": prediction,
        "model_estimated_probability_for_positive_dataset_label": round(
            probability, 4
        ),
        "human_review_required": True,
        "research_only": True,
        "clinical_interpretation": None,
        "notice": (
            "Research experiment only. This is not an emergency severity "
            "prediction, diagnosis, or treatment recommendation."
        ),
    }


# --------------------------------------------------
# RESEARCH-ONLY ML RESOURCE SHORTAGE RISK MODEL
# --------------------------------------------------
RESOURCE_MODEL_PATH = (
    Path(__file__).resolve().parent / "resource_risk_model.joblib"
)

class ResourceRiskRequest(BaseModel):
    current_occupancy_pct: float = Field(ge=0, le=100)
    ed_arrivals_last_hour: int = Field(ge=0, le=200)
    available_ambulances: int = Field(ge=0, le=500)
    available_icu_beds: int = Field(ge=0, le=500)
    staffing_pct: float = Field(ge=0, le=100)
    weather_disruption_index: float = Field(ge=0, le=1)
    public_event_index: float = Field(ge=0, le=1)

@app.get("/api/ml/resource-risk/status")
def resource_risk_status():
    return {
        "model_available": RESOURCE_MODEL_PATH.exists(),
        "model_type": "RandomForestClassifier",
        "dataset_type": "synthetic generated demonstration data",
        "research_only": True,
        "notice": "Not validated for real-world emergency planning or dispatch."
    }

@app.post("/api/ml/resource-risk/predict")
def predict_resource_risk(request: ResourceRiskRequest):
    if not RESOURCE_MODEL_PATH.exists():
        raise HTTPException(503, detail="ML model not trained yet. Run backend/train_resource_risk_model.py first.")
    bundle = joblib.load(RESOURCE_MODEL_PATH)
    features = bundle["features"]
    row = pd.DataFrame([[getattr(request, name) for name in features]], columns=features)
    model = bundle["model"]
    prediction = int(model.predict(row)[0])
    probability = float(model.predict_proba(row)[0][1])
    band = "elevated demo risk" if probability >= 0.65 else ("moderate demo risk" if probability >= 0.35 else "lower demo risk")
    return {
        "model": "RandomForestClassifier",
        "dataset_type": "synthetic generated demonstration data",
        "predicted_label": "shortage-risk pattern" if prediction else "no-shortage-risk pattern",
        "estimated_probability": round(probability, 4),
        "demo_risk_band": band,
        "human_review_required": True,
        "research_only": True,
        "notice": "Educational ML demonstration only. Synthetic labels and metrics do not establish real-world validity. Do not use for clinical triage, dispatch, or resource allocation."
    }


# --------------------------------------------------
# ASHA AI 10,000-ROW SYNTHETIC DATASET API
# --------------------------------------------------
# This CSV contains generated demo scenarios only, not live hospital data.
@app.get("/api/dashboard/overview")
def dashboard_overview():
    """Dashboard summaries from synthetic Lakshmi-labelled sample records only."""
    from . import network_pharmacy as lhn
    c = lhn.db()
    branch_count = int(c.execute("SELECT count(*) FROM branches WHERE active=1").fetchone()[0])
    pharmacy_count = int(c.execute("SELECT count(*) FROM pharmacy_stock").fetchone()[0])
    c.close()
    snapshots = load_resource_file("snapshots")
    # Use each district's mean sample, summed across the 38 district placeholders.
    # This is an illustration only; it is not the network's actual capacity.
    metrics = ["total_beds", "available_beds", "total_icu_beds", "available_icu_beds", "doctors_on_duty", "nurses_on_duty", "total_ventilators", "available_ventilators", "ambulances_total", "ambulances_available"]
    for col in metrics:
        if col in snapshots.columns:
            snapshots[col] = pd.to_numeric(snapshots[col], errors="coerce").fillna(0)
    per_district = snapshots.groupby("district", dropna=False)[[c for c in metrics if c in snapshots.columns]].mean() if not snapshots.empty else pd.DataFrame()
    summary = {col: int(round(per_district[col].sum())) if col in per_district.columns else 0 for col in metrics}
    blood = load_resource_file("blood")
    blood_units = int(pd.to_numeric(blood.get("units_available_demo", pd.Series(dtype=float)), errors="coerce").fillna(0).sum())
    base = load_synthetic_dataset()
    statuses = base["verification_status"].value_counts(dropna=False).to_dict() if "verification_status" in base.columns else {}
    return {
        "network": "Lakshmi Hospital Network",
        "data_label": "SYNTHETIC_DEMO_NOT_REAL",
        "data_type": "LAKSHMI_ONLY_UNVERIFIED_PLACEHOLDERS",
        "dataset_rows": int(len(snapshots)),
        "resource_snapshot_rows": int(len(snapshots)),
        "hospitals_monitored": branch_count,
        "available_beds": summary.get("available_beds", 0), "total_beds": summary.get("total_beds", 0),
        "available_icu_beds": summary.get("available_icu_beds", 0), "total_icu_beds": summary.get("total_icu_beds", 0),
        "doctors_on_duty": summary.get("doctors_on_duty", 0), "nurses_on_duty": summary.get("nurses_on_duty", 0),
        "blood_units_demo_only": blood_units,
        "oxygen_average_pct": int(round(snapshots["oxygen_status"].astype(str).str.upper().eq("AVAILABLE").mean() * 100)) if (not snapshots.empty and "oxygen_status" in snapshots.columns) else 0,
        "ventilators_available": summary.get("available_ventilators", 0), "ventilators_total": summary.get("total_ventilators", 0),
        "ambulances_available_snapshots": summary.get("ambulances_available", 0), "ambulances_total_snapshots": summary.get("ambulances_total", 0),
        "verification_status_counts": {str(k): int(v) for k, v in statuses.items()},
        "high_resource_pressure_records": 0,
        "pharmacy_records": pharmacy_count,
        "human_review_required": True,
        "notice": "All figures are illustrative synthetic sample summaries across district placeholders; they are not actual Lakshmi Hospital capacity or live availability.",
    }

@app.get("/api/dataset/summary")
def dataset_summary():
    """Summary of the bundled 10,000-row research dataset, explicitly marked synthetic."""
    frame = load_synthetic_dataset()
    status_counts = frame["verification_status"].value_counts(dropna=False).to_dict() if "verification_status" in frame.columns else {}
    split_counts = frame["ml_split"].value_counts(dropna=False).to_dict() if "ml_split" in frame.columns else {}
    return {
        "data_label": "SYNTHETIC_DEMO_NOT_REAL",
        "data_type": "LAKSHMI_LABELLED_DISTRICT_PLACEHOLDER_RESEARCH_DATA",
        "rows": int(len(frame)),
        "districts": int(frame["district"].nunique()) if "district" in frame.columns else 0,
        "fictional_hospitals": int(frame["hospital_id"].nunique()) if "hospital_id" in frame.columns else 0,
        "verification_status_counts": {str(k): int(v) for k, v in status_counts.items()},
        "ml_split_counts": {str(k): int(v) for k, v in split_counts.items()},
        "pharmacy_import_rows": 1000,
        "hospital_resource_snapshot_rows": int(len(load_resource_file("snapshots"))),
        "human_review_required": True,
        "notice": "Research and demo data only. All hospital IDs are unverified placeholders, not verified Lakshmi franchise branches or live resource availability.",
    }

@app.get("/api/resources/summary")
def resource_summary():
    doctors = load_resource_file("doctors")
    nurses = load_resource_file("nurses")
    beds = load_resource_file("beds")
    blood = load_resource_file("blood")
    ambulances = load_resource_file("ambulances")
    equipment = load_resource_file("equipment")
    snapshots = load_resource_file("snapshots")
    count_available = lambda frame: int(frame["status"].astype(str).str.casefold().isin(["available", "on_call"]).sum()) if "status" in frame.columns else 0
    numeric_sum = lambda frame, col: int(pd.to_numeric(frame[col], errors="coerce").fillna(0).sum()) if col in frame.columns else 0
    return {
        "data_type": "SYNTHETIC_LAKSHMI_PLACEHOLDERS_NOT_REAL",
        "hospital_count": int(snapshots["district"].nunique()) if "district" in snapshots.columns else 0,
        "snapshot_records": int(len(snapshots)),
        "counts": {"doctors": len(doctors), "nurses": len(nurses), "beds": len(beds), "blood": len(blood), "ambulances": len(ambulances), "equipment": len(equipment), "medicines": len(load_resource_file("medicines")), "snapshots": len(snapshots)},
        "doctors_available_demo": count_available(doctors),
        "nurses_available_demo": count_available(nurses),
        "beds_available_demo": int(beds["status"].astype(str).str.casefold().eq("available").sum()) if "status" in beds.columns else 0,
        "blood_units_available_demo": numeric_sum(blood, "units_available_demo"),
        "ambulances_available_demo": count_available(ambulances),
        "equipment_working_demo": numeric_sum(equipment, "quantity_working_demo"),
        "notice": "Counts are synthetic sample records labelled for Lakshmi placeholders; they are not verified branch stock or capacity.",
    }

@app.get("/api/resources/{resource_type}")
def list_resource_type(resource_type: str, limit: int = 100, hospital_id: Optional[str] = None, district: Optional[str] = None):
    aliases = {"blood_inventory":"blood", "medical_equipment":"equipment", "ambulance_fleet":"ambulances", "medicine_inventory":"medicines", "hospital_snapshots":"snapshots", "resource_snapshots":"snapshots"}
    key = aliases.get(resource_type, resource_type)
    if key not in RESOURCE_FILES:
        raise HTTPException(status_code=404, detail="Unknown resource type")
    return resource_payload(key, limit=limit, hospital_id=hospital_id, district=district)

@app.get("/api/hospitals/{hospital_id}/resources")
def hospital_resources(hospital_id: str):
    from . import network_pharmacy as lhn
    c = lhn.db()
    branch = c.execute("SELECT branch_id, display_name, district, verification_status, active FROM branches WHERE branch_id=?", (hospital_id,)).fetchone()
    if not branch:
        c.close()
        raise HTTPException(status_code=404, detail="This ID is not a Lakshmi Hospital Network branch")
    stock = [dict(r) for r in c.execute("SELECT medicine_code, medicine_name, dosage, form, stock_quantity, reserved_quantity, reorder_level, expiry_date, verification_status, updated_at FROM pharmacy_stock WHERE branch_id=? ORDER BY medicine_name", (hospital_id,))]
    c.close()
    for item in stock:
        item["available_quantity"] = max(0, item["stock_quantity"] - item["reserved_quantity"])
    return {"data_type":"DEMO_UNVERIFIED", "hospital":dict(branch), "resources":{"pharmacy":stock}, "notice":"Lakshmi-only branch placeholder. Pharmacy quantities are synthetic and must not be used for dispensing."}


# Network and pharmacy module: branch-scoped roles, password hashing, signed demo sessions, audit trail.
from .network_pharmacy import router as network_pharmacy_router
app.include_router(network_pharmacy_router)

