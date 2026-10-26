"""ASHA AI multi-agent demo service.

Agents use deterministic, inspectable local data tools. An optional LLM (Ollama or
OpenAI-compatible API) synthesizes an explanation only from aggregate synthetic data.
No agent performs clinical diagnosis, real dispatch, or autonomous stock ordering.
"""
from __future__ import annotations

import csv
import json
import os
import sqlite3
import urllib.error
import urllib.request
from collections import Counter
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Optional

APP_DIR = Path(__file__).resolve().parent
DATA_DIR = APP_DIR.parent / "data"
RESOURCE_CSV = DATA_DIR / "asha_lakshmi_hospital_resources_1000_demo.csv"
AMBULANCE_CSV = DATA_DIR / "ambulance_fleet_synthetic.csv"
PHARMACY_DB = DATA_DIR / "asha_network_pharmacy.sqlite"

ANALYSIS_TYPES = {
    "network_readiness": "Overall demo readiness overview",
    "pharmacy_risk": "Pharmacy low-stock and expiry signals",
    "ambulance_readiness": "Ambulance fleet status and equipment readiness",
    "data_quality": "Stale, missing, unknown, and unverified data",
}


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def _district_rows(rows: list[dict[str, str]], district: Optional[str], key: str = "district") -> list[dict[str, str]]:
    if not district:
        return rows
    target = district.casefold().strip()
    return [r for r in rows if (r.get(key) or "").casefold().strip() == target]


def _resource_agent(district: Optional[str]) -> dict[str, Any]:
    rows = _district_rows(_read_csv(RESOURCE_CSV), district)
    def n(row: dict[str, str], col: str) -> int:
        try:
            return max(0, int(float(row.get(col) or 0)))
        except (ValueError, TypeError):
            return 0
    available_beds = sum(n(r, "available_beds") for r in rows)
    available_icu = sum(n(r, "available_icu_beds") for r in rows)
    stale = sum(1 for r in rows if (r.get("data_freshness") or "").upper() == "STALE")
    unknown_oxygen = sum(1 for r in rows if (r.get("oxygen_status") or "").upper() in {"UNKNOWN", ""})
    low_oxygen = sum(1 for r in rows if (r.get("oxygen_status") or "").upper() == "LOW")
    metrics = {
        "resource_snapshots": len(rows),
        "available_beds_demo": available_beds,
        "available_icu_beds_demo": available_icu,
        "stale_snapshots": stale,
        "oxygen_unknown_snapshots": unknown_oxygen,
        "oxygen_low_snapshots": low_oxygen,
    }
    findings = []
    if not rows:
        findings.append("No resource snapshot matched this district in the demo CSV.")
    else:
        findings.append(f"Loaded {len(rows)} synthetic resource snapshot(s).")
        findings.append(f"Sample arithmetic totals: {available_beds} available bed(s) and {available_icu} ICU bed(s); not live capacity.")
        if stale:
            findings.append(f"{stale} snapshot(s) are labelled stale and need verification.")
        if unknown_oxygen:
            findings.append(f"{unknown_oxygen} snapshot(s) have unknown oxygen status.")
        if low_oxygen:
            findings.append(f"{low_oxygen} snapshot(s) are labelled low oxygen in synthetic data.")
    return {"name": "Hospital Resource Agent", "status": "completed", "metrics": metrics, "findings": findings, "source": "asha_lakshmi_hospital_resources_1000_demo.csv", "data_type": "SYNTHETIC_DEMO_NOT_REAL"}


def _ambulance_agent(district: Optional[str]) -> dict[str, Any]:
    rows = _read_csv(AMBULANCE_CSV)
    if district:
        target = district.casefold().strip()
        rows = [r for r in rows if target in (r.get("hospital_name") or "").casefold()]
    statuses = Counter((r.get("status") or "unknown").lower() for r in rows)
    types = Counter((r.get("ambulance_type") or "unknown").upper() for r in rows)
    def truthy(x: str) -> bool:
        return str(x).strip().lower() in {"true", "1", "yes", "available"}
    metrics = {
        "ambulance_records": len(rows),
        "status_counts_demo": dict(statuses),
        "type_counts_demo": dict(types),
        "with_oxygen_demo": sum(truthy(r.get("oxygen", "")) for r in rows),
        "with_stretcher_demo": sum(truthy(r.get("stretcher", "")) for r in rows),
        "with_patient_monitor_demo": sum(truthy(r.get("patient_monitor", "")) for r in rows),
        "with_defibrillator_demo": sum(truthy(r.get("defibrillator", "")) for r in rows),
        "gps_connected": 0,
    }
    findings = [f"Found {len(rows)} synthetic ambulance record(s); do not use this as a live fleet state."]
    if rows:
        findings.append("Status labels: " + ", ".join(f"{k}={v}" for k, v in sorted(statuses.items())) + ".")
        findings.append("GPS and ETA are not connected; actual vehicle location/availability is unknown.")
    else:
        findings.append("No ambulance samples matched this district; fleet information is unverified.")
    return {"name": "Ambulance Operations Agent", "status": "completed", "metrics": metrics, "findings": findings, "source": "ambulance_fleet_synthetic.csv", "data_type": "SYNTHETIC_DEMO_NOT_REAL"}


def _pharmacy_agent(district: Optional[str], branch_id: Optional[str] = None) -> dict[str, Any]:
    metrics: dict[str, Any] = {"medicine_records": 0, "available_units_demo": 0, "low_stock_records": 0, "expiry_within_90_days": 0, "expired_records": 0}
    findings: list[str] = []
    sample_items: list[dict[str, Any]] = []
    if not PHARMACY_DB.exists():
        findings.append("Pharmacy database not found. Start the backend to initialize its demo database.")
        return {"name": "Pharmacy Inventory Agent", "status": "data_unavailable", "metrics": metrics, "findings": findings, "sample_alerts": sample_items, "source": "asha_network_pharmacy.sqlite", "data_type": "SYNTHETIC_DEMO_NOT_REAL"}
    conn = sqlite3.connect(PHARMACY_DB)
    conn.row_factory = sqlite3.Row
    sql = "SELECT p.medicine_name,p.medicine_code,p.stock_quantity,p.reserved_quantity,p.reorder_level,p.expiry_date,p.verification_status,b.district,b.branch_id FROM pharmacy_stock p JOIN branches b ON p.branch_id=b.branch_id WHERE 1=1"
    args: list[Any] = []
    if district:
        sql += " AND lower(b.district)=lower(?)"
        args.append(district)
    if branch_id:
        sql += " AND p.branch_id=?"
        args.append(branch_id)
    rows = [dict(r) for r in conn.execute(sql, args).fetchall()]
    conn.close()
    today = date.today()
    soon = (today + timedelta(days=90)).isoformat()
    total_available = 0
    low_count = expiry_count = expired_count = 0
    alerts = []
    for r in rows:
        stock = max(0, int(r.get("stock_quantity") or 0))
        reserved = max(0, min(stock, int(r.get("reserved_quantity") or 0)))
        available = stock - reserved
        reorder = max(0, int(r.get("reorder_level") or 0))
        expiry = str(r.get("expiry_date") or "")
        total_available += available
        low = available <= reorder
        expired = bool(expiry and expiry < today.isoformat())
        expiring = bool(expiry and today.isoformat() <= expiry <= soon)
        low_count += int(low)
        expiry_count += int(expiring)
        expired_count += int(expired)
        if low or expired or expiring:
            alerts.append({"medicine_name": r.get("medicine_name"), "district": r.get("district"), "available_quantity_demo": available, "reorder_level": reorder, "expiry_date": expiry, "low_stock": low, "expired": expired, "expiry_within_90_days": expiring, "verification_status": r.get("verification_status")})
    alerts.sort(key=lambda x: (not x["expired"], not x["low_stock"], x["expiry_date"] or "9999-12-31"))
    metrics.update({"medicine_records": len(rows), "available_units_demo": total_available, "low_stock_records": low_count, "expiry_within_90_days": expiry_count, "expired_records": expired_count})
    findings.append(f"Analyzed {len(rows)} synthetic pharmacy record(s).")
    findings.append(f"Demo calculations: {low_count} low-stock, {expiry_count} expiring within 90 days, {expired_count} expired record(s). Verify stock and expiry with an authorized pharmacist.")
    return {"name": "Pharmacy Inventory Agent", "status": "completed", "metrics": metrics, "findings": findings, "sample_alerts": alerts[:5], "source": "asha_network_pharmacy.sqlite", "data_type": "SYNTHETIC_DEMO_NOT_REAL"}


def _self_doubt_agent(agents: list[dict[str, Any]]) -> dict[str, Any]:
    flags: list[str] = [
        "All included datasets are synthetic; none establish live Lakshmi Hospital branch affiliation or inventory.",
        "Ambulance GPS/ETA is not connected, so dispatch readiness cannot be confirmed.",
        "Aggregate counts are derived from demo snapshots and must be manually verified before any operational reliance.",
    ]
    for a in agents:
        m = a.get("metrics", {})
        if a["name"] == "Hospital Resource Agent":
            if m.get("stale_snapshots", 0): flags.append(f"Resource data freshness flag: {m['stale_snapshots']} stale snapshot(s).")
            if m.get("oxygen_unknown_snapshots", 0): flags.append(f"Oxygen status is unknown in {m['oxygen_unknown_snapshots']} snapshot(s).")
        if a["name"] == "Pharmacy Inventory Agent" and m.get("expired_records", 0):
            flags.append(f"Pharmacy demo includes {m['expired_records']} expired record(s); not for dispensing.")
    return {"name": "Self-Doubt / Verification Agent", "status": "completed", "metrics": {"verification_flags": len(flags), "human_review_required": True}, "findings": flags, "data_type": "PROTOTYPE_RULES_NOT_CLINICAL_ADVICE"}


def _deterministic_explanation(analysis_type: str, district: Optional[str], agents: list[dict[str, Any]]) -> str:
    by_name = {a["name"]: a for a in agents}
    place = f" for {district}" if district else " across the demo network"
    resource = by_name.get("Hospital Resource Agent", {}).get("metrics", {})
    ambulance = by_name.get("Ambulance Operations Agent", {}).get("metrics", {})
    pharmacy = by_name.get("Pharmacy Inventory Agent", {}).get("metrics", {})
    if analysis_type == "pharmacy_risk":
        focus = f"Pharmacy-only review{place}: {pharmacy.get('low_stock_records', 0)} low-stock, {pharmacy.get('expiry_within_90_days', 0)} expiry-within-90-days, and {pharmacy.get('expired_records', 0)} expired demo record(s)."
    elif analysis_type == "ambulance_readiness":
        focus = f"Ambulance review{place}: {ambulance.get('ambulance_records', 0)} synthetic vehicle record(s) were found. GPS/ETA is not connected, so no live readiness or dispatch conclusion can be made."
    elif analysis_type == "data_quality":
        focus = f"Data-quality review{place}: {resource.get('stale_snapshots', 0)} stale resource snapshot(s), {resource.get('oxygen_unknown_snapshots', 0)} unknown oxygen-status snapshot(s), and {pharmacy.get('expired_records', 0)} expired pharmacy demo record(s) were identified."
    else:
        focus = f"Network overview{place}: {resource.get('resource_snapshots', 0)} resource snapshot(s), {ambulance.get('ambulance_records', 0)} ambulance record(s), and {pharmacy.get('medicine_records', 0)} pharmacy record(s) were analyzed. These are synthetic demo values, not confirmed capacity."
    return focus + " Suggested next step: verify source freshness and branch/resource details with authorized staff. This prototype does not diagnose, dispatch vehicles, prescribe, or order medicines."


def llm_runtime_status() -> dict[str, Any]:
    provider = os.getenv("ASHA_LLM_PROVIDER", "ollama").strip().lower()
    model = os.getenv("ASHA_LLM_MODEL", "qwen2.5:3b").strip()
    if provider in {"none", "off", "disabled"}:
        return {"provider": "none", "model": None, "available": False, "mode": "rules-only", "message": "LLM is disabled; deterministic agents remain available."}
    if provider == "ollama":
        base = os.getenv("ASHA_OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
        try:
            req = urllib.request.Request(base + "/api/tags", headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=1.25) as response:
                data = json.loads(response.read().decode("utf-8"))
            installed = [x.get("name") or x.get("model") for x in data.get("models", [])]
            exact = model in installed or any(str(x).startswith(model + ":") for x in installed if x)
            return {"provider": provider, "model": model, "available": exact, "server_reachable": True, "mode": "local", "message": "Local LLM model is installed." if exact else "Ollama is running, but the configured model is not installed. Run ollama pull " + model + "."}
        except Exception:
            return {"provider": provider, "model": model, "available": False, "server_reachable": False, "mode": "local", "message": "Ollama is not reachable. Start Ollama and install the model, or use deterministic fallback."}
    if provider in {"openai", "openai_compatible"}:
        key = os.getenv("ASHA_LLM_API_KEY", "").strip()
        base = os.getenv("ASHA_LLM_BASE_URL", "https://api.openai.com/v1").strip()
        return {"provider": "openai_compatible", "model": model, "available": bool(key and base and model), "mode": "remote", "message": "Remote LLM configured; requests send aggregate synthetic data only." if key else "Set ASHA_LLM_API_KEY before remote LLM use."}
    return {"provider": provider, "model": model, "available": False, "mode": "unknown", "message": "Unsupported provider. Use ollama, openai_compatible, or none."}


def _call_llm(analysis_type: str, district: Optional[str], agents: list[dict[str, Any]]) -> tuple[Optional[str], dict[str, Any]]:
    status = llm_runtime_status()
    if not status.get("available"):
        return None, {**status, "used": False, "result": "deterministic_fallback"}
    safe_evidence = [{"agent": a["name"], "metrics": a.get("metrics", {}), "findings": a.get("findings", [])[:8]} for a in agents]
    system = (
        "You are the ASHA AI logistics explanation agent for a college research prototype. "
        "Use only the supplied aggregate synthetic evidence. Never invent data, branch affiliations, GPS, ETA, real availability, diagnoses, treatment, medicine dosage, or clinical urgency. "
        "Explain uncertainty and next verification steps. Do not order, dispatch, or make clinical decisions. "
        "State that human verification is mandatory and the dataset is synthetic. Keep the response concise and actionable."
    )
    user_content = json.dumps({"analysis_type": analysis_type, "district": district, "synthetic_evidence": safe_evidence}, ensure_ascii=False)
    provider = status["provider"]
    try:
        if provider == "ollama":
            base = os.getenv("ASHA_OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
            payload = {"model": status["model"], "stream": False, "messages": [{"role": "system", "content": system}, {"role": "user", "content": user_content}], "options": {"temperature": 0.1}}
            req = urllib.request.Request(base + "/api/chat", data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=float(os.getenv("ASHA_LLM_TIMEOUT_SECONDS", "12"))) as response:
                data = json.loads(response.read().decode("utf-8"))
            text = str((data.get("message") or {}).get("content") or "").strip()
        else:
            base = os.getenv("ASHA_LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/")
            url = base if base.endswith("/chat/completions") else base + "/chat/completions"
            payload = {"model": status["model"], "temperature": 0.1, "messages": [{"role": "system", "content": system}, {"role": "user", "content": user_content}]}
            req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json", "Authorization": "Bearer " + os.environ["ASHA_LLM_API_KEY"].strip()}, method="POST")
            with urllib.request.urlopen(req, timeout=float(os.getenv("ASHA_LLM_TIMEOUT_SECONDS", "12"))) as response:
                data = json.loads(response.read().decode("utf-8"))
            text = str(data["choices"][0]["message"]["content"]).strip()
        if not text:
            raise ValueError("The configured LLM returned an empty response")
        return text[:5000], {**status, "used": True, "result": "generated"}
    except Exception as exc:
        # Do not leak keys or response bodies. Continue with tool-generated evidence.
        return None, {**status, "available": False, "used": False, "result": "deterministic_fallback", "message": f"LLM call failed ({type(exc).__name__}); deterministic agents remain available."}


def analyze_network_snapshot(analysis_type: str, district: Optional[str], branch_id: Optional[str] = None) -> dict[str, Any]:
    if analysis_type not in ANALYSIS_TYPES:
        raise ValueError("Unsupported analysis_type")
    # Each specialist agent gathers its own evidence, then the verification agent checks cross-cutting uncertainty.
    specialist_agents = [_resource_agent(district), _ambulance_agent(district), _pharmacy_agent(district, branch_id)]
    verifier = _self_doubt_agent(specialist_agents)
    agents = specialist_agents + [verifier]
    llm_text, llm_meta = _call_llm(analysis_type, district, agents)
    fallback = _deterministic_explanation(analysis_type, district, agents)
    return {
        "analysis_type": analysis_type,
        "analysis_label": ANALYSIS_TYPES[analysis_type],
        "district": district,
        "data_type": "SYNTHETIC_DEMO_NOT_REAL",
        "workflow": [a["name"] for a in agents] + ["LLM Orchestrator / Explanation Layer"],
        "agents": agents,
        "explanation": llm_text or fallback,
        "explanation_source": "llm" if llm_text else "deterministic_fallback",
        "llm": llm_meta,
        "human_review_required": True,
        "notice": "All data are synthetic/unverified. No diagnosis, prescribing, autonomous dispatch, or stock ordering is performed.",
    }
