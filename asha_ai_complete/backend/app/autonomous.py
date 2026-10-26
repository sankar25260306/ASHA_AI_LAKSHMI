"""Bounded autonomous monitoring for ASHA AI's synthetic demo network.

The monitor periodically reviews aggregate demo data, applies deterministic quality/risk
rules, and records alerts and recommendations. It never dispatches ambulances, makes
clinical decisions, changes pharmacy stock, or places orders.
"""
from __future__ import annotations

import asyncio
import json
import os
import sqlite3
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

from .multi_agent import (
    _ambulance_agent,
    _pharmacy_agent,
    _resource_agent,
    _self_doubt_agent,
)

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "asha_network_pharmacy.sqlite"
DEFAULT_INTERVAL = max(60, min(3600, int(os.getenv("ASHA_AUTONOMOUS_INTERVAL_SECONDS", "300"))))
DEFAULT_ENABLED = os.getenv("ASHA_AUTONOMOUS_ENABLED", "true").strip().lower() not in {"0", "false", "no", "off"}
DATA_LABEL = "SYNTHETIC_DEMO_NOT_REAL"


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_tables() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS autonomous_settings (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                enabled INTEGER NOT NULL DEFAULT 1,
                interval_seconds INTEGER NOT NULL DEFAULT 300,
                updated_at TEXT NOT NULL,
                updated_by TEXT NOT NULL DEFAULT 'system'
            );
            CREATE TABLE IF NOT EXISTS autonomous_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TEXT NOT NULL,
                finished_at TEXT NOT NULL,
                status TEXT NOT NULL,
                triggered_by TEXT NOT NULL,
                summary TEXT NOT NULL,
                metrics_json TEXT NOT NULL,
                alerts_json TEXT NOT NULL,
                actions_json TEXT NOT NULL,
                data_type TEXT NOT NULL
            );
            """
        )
        conn.execute(
            "INSERT OR IGNORE INTO autonomous_settings(id, enabled, interval_seconds, updated_at, updated_by) VALUES(1, ?, ?, ?, ?)",
            (int(DEFAULT_ENABLED), DEFAULT_INTERVAL, _now(), "bootstrap"),
        )


def get_settings() -> dict[str, Any]:
    ensure_tables()
    with _conn() as conn:
        row = conn.execute("SELECT enabled, interval_seconds, updated_at, updated_by FROM autonomous_settings WHERE id=1").fetchone()
    if not row:
        return {"enabled": DEFAULT_ENABLED, "interval_seconds": DEFAULT_INTERVAL, "updated_at": _now(), "updated_by": "default"}
    return {"enabled": bool(row["enabled"]), "interval_seconds": int(row["interval_seconds"]), "updated_at": row["updated_at"], "updated_by": row["updated_by"]}


def update_settings(enabled: bool, interval_seconds: int, updated_by: str) -> dict[str, Any]:
    if not 60 <= int(interval_seconds) <= 3600:
        raise ValueError("interval_seconds must be between 60 and 3600")
    ensure_tables()
    with _conn() as conn:
        conn.execute(
            "UPDATE autonomous_settings SET enabled=?, interval_seconds=?, updated_at=?, updated_by=? WHERE id=1",
            (int(enabled), int(interval_seconds), _now(), updated_by),
        )
    return get_settings()


def _build_alerts(resource: dict[str, Any], ambulance: dict[str, Any], pharmacy: dict[str, Any], verifier: dict[str, Any]) -> list[dict[str, Any]]:
    rm = resource.get("metrics", {})
    am = ambulance.get("metrics", {})
    pm = pharmacy.get("metrics", {})
    alerts: list[dict[str, Any]] = []

    def add(code: str, severity: str, title: str, detail: str, next_step: str) -> None:
        alerts.append({
            "code": code,
            "severity": severity,
            "title": title,
            "detail": detail,
            "recommended_next_step": next_step,
            "human_review_required": True,
            "data_type": DATA_LABEL,
        })

    if int(rm.get("stale_snapshots", 0) or 0):
        add("STALE_RESOURCE_DATA", "warning", "Resource snapshots need verification",
            f"{rm['stale_snapshots']} synthetic resource snapshot(s) are marked stale.",
            "Ask an authorized branch staff member to verify current resource values.")
    if int(rm.get("oxygen_unknown_snapshots", 0) or 0):
        add("OXYGEN_STATUS_UNKNOWN", "warning", "Oxygen status is unknown",
            f"{rm['oxygen_unknown_snapshots']} synthetic snapshot(s) have unknown oxygen status.",
            "Confirm oxygen availability directly with authorized staff; do not infer it from this demo.")
    if int(rm.get("oxygen_low_snapshots", 0) or 0):
        add("OXYGEN_LOW_DEMO", "warning", "Low oxygen flags found in demo data",
            f"{rm['oxygen_low_snapshots']} synthetic snapshot(s) are labelled low oxygen.",
            "Verify the inventory using an authorized, current source.")
    if int(pm.get("expired_records", 0) or 0):
        add("EXPIRED_STOCK_DEMO", "high", "Expired medicine records in demo inventory",
            f"{pm['expired_records']} synthetic pharmacy record(s) have an expiry date before today.",
            "Do not dispense based on this dataset. An authorized pharmacist must verify real batch details.")
    if int(pm.get("low_stock_records", 0) or 0):
        add("LOW_STOCK_DEMO", "warning", "Low-stock patterns detected",
            f"{pm['low_stock_records']} synthetic pharmacy record(s) are at or below the reorder threshold.",
            "Ask pharmacy staff to verify physical stock and approve any replenishment manually.")
    if int(pm.get("expiry_within_90_days", 0) or 0):
        add("EXPIRY_SOON_DEMO", "info", "Upcoming-expiry records detected",
            f"{pm['expiry_within_90_days']} synthetic pharmacy record(s) expire within 90 days.",
            "Verify product batch, expiry label and usable stock with a pharmacist.")
    if int(am.get("ambulance_records", 0) or 0):
        add("AMBULANCE_GPS_UNAVAILABLE", "info", "Fleet status is not live",
            f"{am['ambulance_records']} synthetic ambulance record(s) were inspected; GPS connected count is {am.get('gps_connected', 0)}.",
            "Confirm vehicle availability and location by an approved live fleet system before any dispatch.")
    add("SYNTHETIC_DATA_GUARD", "info", "Monitoring uses demo data only",
        "The current files do not establish real Lakshmi Hospital franchise branches, live stock, bed capacity or ambulance availability.",
        "Treat outputs as development alerts only until authorized data feeds are connected and verified.")

    if not alerts:
        add("NO_RULE_ALERTS", "info", "No rule alerts in this snapshot",
            "No selected thresholds were triggered in the current synthetic snapshot.",
            "This is not proof of safety or real-world readiness; continue human verification.")
    # Surface verifier findings as a compact note only when not already covered.
    findings = verifier.get("findings", [])
    if findings:
        add("SELF_DOUBT_REVIEW", "info", "Self-Doubt Engine requests human review",
            " ".join(str(x) for x in findings[:2]),
            "Review source freshness, missing values and branch verification status.")
    return alerts


def run_autonomous_cycle(triggered_by: str = "system_scheduler") -> dict[str, Any]:
    """Run one bounded autonomous cycle. Does not execute operational decisions."""
    ensure_tables()
    started = _now()
    try:
        resource = _resource_agent(None)
        ambulance = _ambulance_agent(None)
        pharmacy = _pharmacy_agent(None)
        verifier = _self_doubt_agent([resource, ambulance, pharmacy])
        agents = [resource, ambulance, pharmacy, verifier]
        alerts = _build_alerts(resource, ambulance, pharmacy, verifier)
        metrics = {a["name"]: a.get("metrics", {}) for a in agents}
        actions = [
            {"action": "collect_aggregate_demo_metrics", "status": "completed"},
            {"action": "check_stale_unknown_and_threshold_flags", "status": "completed"},
            {"action": "record_alerts_and_monitoring_run", "status": "completed"},
            {"action": "ambulance_dispatch", "status": "not_performed_requires_human_approval"},
            {"action": "clinical_decision_or_treatment", "status": "not_performed_requires_qualified_clinician"},
            {"action": "pharmacy_order_or_stock_mutation", "status": "not_performed_requires_authorized_pharmacist"},
        ]
        finished = _now()
        summary = (
            f"Autonomous monitoring inspected {metrics['Hospital Resource Agent'].get('resource_snapshots', 0)} resource snapshot(s), "
            f"{metrics['Ambulance Operations Agent'].get('ambulance_records', 0)} ambulance record(s), and "
            f"{metrics['Pharmacy Inventory Agent'].get('medicine_records', 0)} pharmacy record(s); "
            f"generated {len(alerts)} review alert(s). Synthetic demo data only."
        )
        with _conn() as conn:
            cur = conn.execute(
                "INSERT INTO autonomous_runs(started_at, finished_at, status, triggered_by, summary, metrics_json, alerts_json, actions_json, data_type) VALUES(?,?,?,?,?,?,?,?,?)",
                (started, finished, "completed", str(triggered_by)[:120], summary, json.dumps(metrics), json.dumps(alerts), json.dumps(actions), DATA_LABEL),
            )
            run_id = int(cur.lastrowid)
        return {
            "id": run_id,
            "started_at": started,
            "finished_at": finished,
            "status": "completed",
            "triggered_by": str(triggered_by)[:120],
            "summary": summary,
            "metrics": metrics,
            "alerts": alerts,
            "alert_count": len(alerts),
            "actions": actions,
            "agents": [a["name"] for a in agents],
            "human_review_required": True,
            "data_type": DATA_LABEL,
            "notice": "Bounded autonomy: monitoring, rule checks, alert creation and audit logging only. No real dispatch, diagnosis, treatment, medicine order or stock mutation occurs.",
        }
    except Exception as exc:
        finished = _now()
        summary = f"Autonomous monitoring cycle failed safely ({type(exc).__name__}). No operational action was performed."
        with _conn() as conn:
            cur = conn.execute(
                "INSERT INTO autonomous_runs(started_at, finished_at, status, triggered_by, summary, metrics_json, alerts_json, actions_json, data_type) VALUES(?,?,?,?,?,?,?,?,?)",
                (started, finished, "failed", str(triggered_by)[:120], summary, "{}", "[]", json.dumps([{"action": "operational_change", "status": "not_performed"}]), DATA_LABEL),
            )
            run_id = int(cur.lastrowid)
        return {"id": run_id, "started_at": started, "finished_at": finished, "status": "failed", "triggered_by": str(triggered_by)[:120], "summary": summary, "metrics": {}, "alerts": [], "alert_count": 0, "actions": [{"action": "operational_change", "status": "not_performed"}], "human_review_required": True, "data_type": DATA_LABEL, "notice": "Autonomous cycle failed safely; inspect backend logs. No operational action was performed."}


def list_runs(limit: int = 20) -> list[dict[str, Any]]:
    ensure_tables()
    safe_limit = max(1, min(100, int(limit)))
    with _conn() as conn:
        rows = conn.execute("SELECT * FROM autonomous_runs ORDER BY id DESC LIMIT ?", (safe_limit,)).fetchall()
    result = []
    for row in rows:
        item = dict(row)
        for source, target in (("metrics_json", "metrics"), ("alerts_json", "alerts"), ("actions_json", "actions")):
            try:
                item[target] = json.loads(item.pop(source))
            except Exception:
                item[target] = [] if target != "metrics" else {}
        item["alert_count"] = len(item.get("alerts", []))
        item["human_review_required"] = True
        result.append(item)
    return result


def get_status() -> dict[str, Any]:
    settings = get_settings()
    runs = list_runs(1)
    last_run = runs[0] if runs else None
    next_run_at = None
    if settings["enabled"] and last_run and last_run.get("finished_at"):
        try:
            finished = datetime.fromisoformat(last_run["finished_at"])
            next_run_at = (finished + timedelta(seconds=settings["interval_seconds"])).isoformat()
        except ValueError:
            next_run_at = None
    with _conn() as conn:
        total_runs = int(conn.execute("SELECT COUNT(*) FROM autonomous_runs").fetchone()[0])
    return {
        "autonomous_enabled": settings["enabled"],
        "interval_seconds": settings["interval_seconds"],
        "updated_at": settings["updated_at"],
        "updated_by": settings["updated_by"],
        "last_run": last_run,
        "next_run_at_estimate": next_run_at,
        "total_runs": total_runs,
        "mode": "bounded_autonomy",
        "autonomous_capabilities": ["scheduled data review", "deterministic threshold checks", "self-doubt verification flags", "persisted monitoring logs", "review alerts"],
        "manual_approval_required_for": ["ambulance dispatch", "clinical decisions", "treatment or prescribing", "pharmacy orders", "stock changes"],
        "data_type": DATA_LABEL,
        "notice": "Autonomous cycles use synthetic local data only. This is not connected to live hospitals, GPS, clinical systems, pharmacy feeds or emergency dispatch.",
    }


async def autonomous_monitor_loop() -> None:
    """Background scheduler. It polls settings often so an admin can pause it quickly."""
    ensure_tables()
    last_cycle_monotonic: float | None = None
    while True:
        settings = get_settings()
        interval = settings["interval_seconds"]
        if settings["enabled"] and (last_cycle_monotonic is None or time.monotonic() - last_cycle_monotonic >= interval):
            await asyncio.to_thread(run_autonomous_cycle, "system_scheduler")
            last_cycle_monotonic = time.monotonic()
        await asyncio.sleep(5)
