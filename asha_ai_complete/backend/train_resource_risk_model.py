"""Train an educational resource-shortage model on synthetic demo data.

This is a software prototype, not a validated operational forecasting model.
The generated data are artificial and must never be used for real emergency decisions.
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
from sklearn.model_selection import train_test_split

ROOT = Path(__file__).resolve().parent
ARTIFACT = ROOT / "app" / "resource_risk_model.joblib"
REPORT = ROOT / "resource_risk_metrics.json"
FEATURES = [
    "current_occupancy_pct",
    "ed_arrivals_last_hour",
    "available_ambulances",
    "available_icu_beds",
    "staffing_pct",
    "weather_disruption_index",
    "public_event_index",
]


def main():
    rng = np.random.default_rng(42)
    n = 5000
    df = pd.DataFrame({
        "current_occupancy_pct": rng.uniform(20, 100, n),
        "ed_arrivals_last_hour": rng.poisson(7, n).clip(0, 30),
        "available_ambulances": rng.integers(0, 16, n),
        "available_icu_beds": rng.integers(0, 21, n),
        "staffing_pct": rng.uniform(35, 100, n),
        "weather_disruption_index": rng.uniform(0, 1, n),
        "public_event_index": rng.uniform(0, 1, n),
    })
    # Synthetic label-generation rule creates a learnable demonstration target.
    score = (
        0.035 * (df.current_occupancy_pct - 60)
        + 0.22 * (df.ed_arrivals_last_hour - 7)
        - 0.20 * (df.available_ambulances - 5)
        - 0.13 * (df.available_icu_beds - 6)
        - 0.045 * (df.staffing_pct - 70)
        + 2.0 * df.weather_disruption_index
        + 1.4 * df.public_event_index
        + rng.normal(0, 1.2, n)
    )
    probability = 1 / (1 + np.exp(-score / 2.5))
    df["shortage_risk"] = (rng.random(n) < probability).astype(int)
    X_train, X_test, y_train, y_test = train_test_split(
        df[FEATURES], df["shortage_risk"], test_size=0.2,
        random_state=42, stratify=df["shortage_risk"]
    )
    model = RandomForestClassifier(
        n_estimators=180, max_depth=10, min_samples_leaf=4,
        class_weight="balanced", random_state=42, n_jobs=-1
    )
    model.fit(X_train, y_train)
    pred = model.predict(X_test)
    prob = model.predict_proba(X_test)[:, 1]
    metrics = {
        "dataset": "synthetic_generated_demo_data",
        "rows": int(n),
        "train_rows": int(len(X_train)),
        "test_rows": int(len(X_test)),
        "accuracy": round(float(accuracy_score(y_test, pred)), 4),
        "precision": round(float(precision_score(y_test, pred, zero_division=0)), 4),
        "recall": round(float(recall_score(y_test, pred, zero_division=0)), 4),
        "f1": round(float(f1_score(y_test, pred, zero_division=0)), 4),
        "roc_auc": round(float(roc_auc_score(y_test, prob)), 4),
        "warning": "Metrics only measure fit to artificial labels; not real-world validity.",
    }
    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": model, "features": FEATURES, "dataset_type": "synthetic_demo"}, ARTIFACT)
    REPORT.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    df.to_csv(ROOT / "synthetic_resource_risk_dataset.csv", index=False)
    print(json.dumps(metrics, indent=2))
    print(f"Saved model: {ARTIFACT}")
    print(f"Saved dataset: {ROOT / 'synthetic_resource_risk_dataset.csv'}")

if __name__ == "__main__":
    main()
