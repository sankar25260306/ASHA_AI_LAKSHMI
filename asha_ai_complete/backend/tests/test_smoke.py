"""Smoke/integration tests for the ASHA AI synthetic demo.

Run from backend/:  python -m pytest tests -q
These tests use only synthetic records and the local demo database.
"""
import os
import json
from pathlib import Path
import sys

import pytest
from fastapi.testclient import TestClient

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from app.main import app  # noqa: E402

client = TestClient(app)
DEMO_PASSWORD = os.environ.get("ASHA_TEST_PASSWORD", "ASHA-Demo-2026!")


@pytest.fixture(scope="module")
def admin_headers():
    response = client.post(
        "/api/network/auth/login",
        json={"role": "super_admin", "username": "superadmin", "password": DEMO_PASSWORD},
    )
    if response.status_code != 200:
        pytest.skip(
            "Default demo password was changed. Set ASHA_TEST_PASSWORD to the current local Super Admin password."
        )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_root_and_health():
    assert client.get("/").status_code == 200
    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"


def test_login_requires_role_selection():
    response = client.post("/api/network/auth/login", json={"username": "superadmin", "password": DEMO_PASSWORD})
    assert response.status_code == 422


def test_login_rejects_wrong_selected_role():
    response = client.post("/api/network/auth/login", json={
        "role": "pharmacy_staff", "username": "superadmin", "password": DEMO_PASSWORD
    })
    # No login token is issued when the selected role differs from the account role.
    assert response.status_code == 401
    assert "selected role" in response.json()["detail"].lower()


def test_login_accepts_matching_role(admin_headers):
    assert "Authorization" in admin_headers


def test_10k_research_dataset_shape():
    response = client.get("/api/dataset/summary")
    assert response.status_code == 200
    result = response.json()
    assert result["rows"] == 10_000
    assert result["ml_split_counts"]["train"] == 8_000
    assert result["ml_split_counts"]["test"] == 2_000
    assert result["human_review_required"] is True


def test_1000_resource_snapshots():
    response = client.get("/api/resources/snapshots?limit=1000")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1_000
    assert len(data["items"]) == 1_000
    assert "SYNTHETIC" in data["data_type"]


def test_resource_limit_validation():
    assert client.get("/api/resources/snapshots?limit=0").status_code == 200  # endpoint clamps to 1
    response = client.get("/api/resources/snapshots?limit=5000")
    assert response.status_code == 200
    assert len(response.json()["items"]) <= 1_000


def test_hospital_list_is_lakshmi_placeholders_only():
    data = client.get("/api/hospitals").json()
    assert data["count"] == 38
    assert all("Lakshmi Hospital" in item["name"] for item in data["items"])
    assert all("beds" in item and "icu_beds" in item for item in data["items"])
    assert "unverified" in data["notice"].lower()


def test_ambulance_fleet_details_are_available_as_demo_only():
    data = client.get("/api/ambulances").json()
    assert data["data_type"] == "SYNTHETIC_LAKSHMI_PLACEHOLDERS_NOT_REAL"
    assert data["count"] == 90
    assert len(data["items"]) == 90
    assert all(item["data_label"] == "SYNTHETIC_DEMO_NOT_REAL" for item in data["items"])
    assert all(item["branch_verification_status"] == "DEMO_UNVERIFIED" for item in data["items"])
    assert all(item["gps_status"] == "Not connected" for item in data["items"])
    assert all(item["eta_minutes"] is None for item in data["items"])
    assert all("hospital_id" in item and "ambulance_type" in item and "equipment" in item for item in data["items"])
    assert "not use for actual emergency dispatch" in data["notice"].lower()


def test_ambulance_resource_endpoint_includes_equipment_fields():
    response = client.get("/api/resources/ambulances?limit=1000")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 90
    assert len(data["items"]) == 90
    assert all("ambulance_id" in item for item in data["items"])


def test_ml_model_available_and_research_only():
    status = client.get("/api/ml/resource-risk/status")
    assert status.status_code == 200
    assert status.json()["model_available"] is True
    assert status.json()["research_only"] is True


def test_ml_prediction_returns_human_review_notice():
    payload = {
        "current_occupancy_pct": 82,
        "ed_arrivals_last_hour": 12,
        "available_ambulances": 3,
        "available_icu_beds": 2,
        "staffing_pct": 65,
        "weather_disruption_index": 0.4,
        "public_event_index": 0.2,
    }
    response = client.post("/api/ml/resource-risk/predict", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["model"] == "RandomForestClassifier"
    assert data["research_only"] is True
    assert data["human_review_required"] is True
    assert 0 <= data["estimated_probability"] <= 1


def test_ml_rejects_out_of_range_input():
    payload = {
        "current_occupancy_pct": 120,
        "ed_arrivals_last_hour": 12,
        "available_ambulances": 3,
        "available_icu_beds": 2,
        "staffing_pct": 65,
        "weather_disruption_index": 0.4,
        "public_event_index": 0.2,
    }
    assert client.post("/api/ml/resource-risk/predict", json=payload).status_code == 422


def test_pharmacy_api_requires_authentication():
    assert client.get("/api/network/pharmacy/stock?limit=1000").status_code == 401
    assert client.get("/api/network/pharmacy/summary").status_code == 401


def test_pharmacy_import_has_1000_records(admin_headers):
    response = client.get("/api/network/pharmacy/stock?limit=1000", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 1_000
    assert len(data["items"]) == 1_000
    assert data["data_type"] == "DEMO_UNVERIFIED"
    assert "synthetic" in data["notice"].lower()


def test_pharmacy_available_quantity_arithmetic(admin_headers):
    response = client.get("/api/network/pharmacy/stock?limit=1000", headers=admin_headers)
    assert response.status_code == 200
    for item in response.json()["items"]:
        assert item["available_quantity"] == max(0, item["stock_quantity"] - item["reserved_quantity"])
        assert item["reserved_quantity"] <= item["stock_quantity"]


def test_pharmacy_summary_matches_import(admin_headers):
    response = client.get("/api/network/pharmacy/summary", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["medicine_records"] == 1_000
    assert data["branches_covered"] <= 38


def test_38_district_placeholders_are_marked_demo(admin_headers):
    response = client.get("/api/network/branches", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 38
    assert all(item["verification_status"] == "DEMO_UNVERIFIED" for item in data["items"])


def test_audit_logs_are_available_to_super_admin(admin_headers):
    response = client.get("/api/network/audit-logs?limit=50", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["read_only"] is True


def test_resource_summary_exposes_snapshot_count():
    response = client.get("/api/resources/summary")
    assert response.status_code == 200
    assert response.json()["snapshot_records"] == 1_000


def test_resource_matching_uses_only_lakshmi_demo_snapshots():
    payload = {"area": "Chennai", "needs_icu": True, "age": 45, "symptoms": ["demo"], "heart_rate": 80, "spo2": 98, "temperature_c": 36.7}
    response = client.post("/api/match-resources", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["data_type"] == "SYNTHETIC_LAKSHMI_PLACEHOLDERS_NOT_REAL"
    assert data["ambulance_options"] == []
    assert all("Lakshmi Hospital" in item["name"] for item in data["hospital_options"])
    assert data["human_confirmation_required"] is True


def test_self_doubt_surfaces_synthetic_data_quality_warnings():
    payload = {"area": "Chennai", "age": None, "symptoms": [], "heart_rate": None, "spo2": None, "temperature_c": None, "needs_icu": False}
    response = client.post("/api/self-doubt", json=payload)
    assert response.status_code == 200
    text = json.dumps(response.json()).lower()
    assert "missing" in text or "stale" in text or "unknown" in text


def test_cross_verification_marks_sample_data_as_demo():
    payload = {"area": "Chennai", "age": 45, "symptoms": ["demo"], "heart_rate": 80, "spo2": 98, "temperature_c": 36.7, "needs_icu": False}
    response = client.post("/api/cross-verify", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["data_type"] == "SIMULATED_RULES_ONLY"
    assert data["engine"] == "ASHA_MULTI_AGENT_CROSS_VERIFICATION"


def test_pharmacy_rejects_reserved_quantity_above_stock(admin_headers):
    payload = {
        "branch_id": "LHN-TN-03",
        "medicine_code": "TEST-INVALID",
        "medicine_name": "Demo validation item",
        "dosage": "demo",
        "form": "tablet",
        "stock_quantity": 1,
        "reserved_quantity": 2,
        "reorder_level": 1,
        "expiry_date": "2027-12-31",
        "prescription_type": "SYNTHETIC_DEMO",
        "verification_status": "DEMO_UNVERIFIED",
    }
    response = client.post("/api/network/pharmacy/stock", json=payload, headers=admin_headers)
    assert response.status_code == 422


def test_branch_scoped_user_cannot_read_other_branch(admin_headers):
    import uuid
    username = "scope_" + uuid.uuid4().hex[:10]
    create = client.post("/api/network/users", json={
        "username": username,
        "temporary_password": "Scope-Test-2026!",
        "role": "pharmacy_staff",
        "organization": "ASHA Demo Test",
        "branch_id": "LHN-TN-03",
    }, headers=admin_headers)
    assert create.status_code == 201
    login = client.post("/api/network/auth/login", json={"role": "pharmacy_staff", "username": username, "password": "Scope-Test-2026!"})
    assert login.status_code == 200
    staff_headers = {"Authorization": "Bearer " + login.json()["access_token"]}
    response = client.get("/api/network/pharmacy/stock?limit=1000", headers=staff_headers)
    assert response.status_code == 200
    rows = response.json()["items"]
    assert rows
    assert {row["branch_id"] for row in rows} == {"LHN-TN-03"}
    cross_branch = client.post("/api/network/pharmacy/stock", json={
        "branch_id": "LHN-TN-04",
        "medicine_code": "TEST-SCOPE",
        "medicine_name": "Demo scope test item",
        "dosage": "demo",
        "form": "tablet",
        "stock_quantity": 1,
        "reserved_quantity": 0,
        "reorder_level": 1,
        "expiry_date": "2027-12-31",
        "prescription_type": "SYNTHETIC_DEMO",
        "verification_status": "DEMO_UNVERIFIED",
    }, headers=staff_headers)
    assert cross_branch.status_code == 403
    deactivate = client.patch(f"/api/network/users/{username}/active?active=false", headers=admin_headers)
    assert deactivate.status_code == 200


def test_multi_agent_status_requires_login():
    assert client.get('/api/network/agents/status').status_code == 401


def test_multi_agent_status_reports_safe_configuration(admin_headers):
    response = client.get('/api/network/agents/status', headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert data['multi_agent_enabled'] is True
    assert len(data['agents']) == 5
    assert data['data_type'] == 'SYNTHETIC_DEMO_NOT_REAL'
    assert 'api_key' not in json.dumps(data).lower()


def test_multi_agent_analysis_uses_existing_demo_data(admin_headers):
    response = client.post('/api/network/agents/analyze', headers=admin_headers, json={
        'analysis_type': 'network_readiness', 'district': 'Coimbatore'
    })
    assert response.status_code == 200, response.text
    data = response.json()
    assert data['data_type'] == 'SYNTHETIC_DEMO_NOT_REAL'
    assert data['human_review_required'] is True
    assert len(data['agents']) == 4
    names = [item['name'] for item in data['agents']]
    assert 'Hospital Resource Agent' in names
    assert 'Ambulance Operations Agent' in names
    assert 'Pharmacy Inventory Agent' in names
    assert 'Self-Doubt / Verification Agent' in names
    assert data['agents'][0]['metrics']['resource_snapshots'] > 0
    assert data['agents'][2]['metrics']['medicine_records'] > 0
    assert data['explanation_source'] in {'llm', 'deterministic_fallback'}


def test_multi_agent_analysis_rejects_unknown_analysis(admin_headers):
    response = client.post('/api/network/agents/analyze', headers=admin_headers, json={
        'analysis_type': 'make_clinical_decision', 'district': 'Coimbatore'
    })
    assert response.status_code == 422


def test_multi_agent_branch_scope_restricts_district(admin_headers):
    import uuid
    username = 'agent_scope_' + uuid.uuid4().hex[:8]
    created = client.post('/api/network/users', headers=admin_headers, json={
        'username': username,
        'temporary_password': 'Agent-Scope-2026!',
        'role': 'pharmacy_staff',
        'organization': 'ASHA Demo Test',
        'branch_id': 'LHN-TN-03',
    })
    assert created.status_code == 201
    login = client.post('/api/network/auth/login', json={
        'role': 'pharmacy_staff', 'username': username, 'password': 'Agent-Scope-2026!'
    })
    assert login.status_code == 200
    headers = {'Authorization': 'Bearer ' + login.json()['access_token']}
    denied = client.post('/api/network/agents/analyze', headers=headers, json={
        'analysis_type': 'network_readiness', 'district': 'Coimbatore'
    })
    assert denied.status_code == 403
    own_scope = client.post('/api/network/agents/analyze', headers=headers, json={
        'analysis_type': 'pharmacy_risk'
    })
    assert own_scope.status_code == 200
    assert own_scope.json()['district'] == 'Chennai'
    client.patch(f'/api/network/users/{username}/active?active=false', headers=admin_headers)


def test_autonomous_monitor_status_requires_login():
    assert client.get('/api/network/autonomous/status').status_code == 401
    assert client.get('/api/network/autonomous/runs').status_code == 401


def test_autonomous_monitor_can_run_bounded_cycle(admin_headers):
    response = client.post('/api/network/autonomous/run', headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert data['status'] == 'completed'
    assert data['data_type'] == 'SYNTHETIC_DEMO_NOT_REAL'
    assert data['human_review_required'] is True
    assert data['alert_count'] >= 1
    actions = {a['action']: a['status'] for a in data['actions']}
    assert actions['collect_aggregate_demo_metrics'] == 'completed'
    assert actions['ambulance_dispatch'] == 'not_performed_requires_human_approval'
    assert actions['clinical_decision_or_treatment'] == 'not_performed_requires_qualified_clinician'
    assert actions['pharmacy_order_or_stock_mutation'] == 'not_performed_requires_authorized_pharmacist'


def test_autonomous_cycle_is_recorded_and_readable(admin_headers):
    before = client.get('/api/network/autonomous/status', headers=admin_headers)
    assert before.status_code == 200
    run = client.post('/api/network/autonomous/run', headers=admin_headers)
    assert run.status_code == 200
    status = client.get('/api/network/autonomous/status', headers=admin_headers).json()
    assert status['total_runs'] >= 1
    assert status['last_run'] is not None
    assert status['mode'] == 'bounded_autonomy'
    logs = client.get('/api/network/autonomous/runs?limit=5', headers=admin_headers)
    assert logs.status_code == 200
    assert logs.json()['count'] >= 1
    assert logs.json()['items'][0]['data_type'] == 'SYNTHETIC_DEMO_NOT_REAL'


def test_autonomous_toggle_is_super_admin_only(admin_headers):
    import uuid
    username = 'auto_staff_' + uuid.uuid4().hex[:8]
    created = client.post('/api/network/users', headers=admin_headers, json={
        'username': username,
        'temporary_password': 'Auto-Test-2026-Secret!',
        'role': 'pharmacy_staff',
        'organization': 'ASHA test',
        'branch_id': 'LHN-TN-03',
    })
    assert created.status_code == 201
    logged = client.post('/api/network/auth/login', json={
        'role': 'pharmacy_staff', 'username': username, 'password': 'Auto-Test-2026-Secret!'
    })
    assert logged.status_code == 200
    staff_headers = {'Authorization': 'Bearer ' + logged.json()['access_token']}
    blocked = client.patch('/api/network/autonomous/settings', headers=staff_headers, json={
        'enabled': False, 'interval_seconds': 300
    })
    assert blocked.status_code == 403
    # Keep the persistent demo monitor enabled after the test suite.
    resumed = client.patch('/api/network/autonomous/settings', headers=admin_headers, json={
        'enabled': True, 'interval_seconds': 300
    })
    assert resumed.status_code == 200
    assert resumed.json()['enabled'] is True


def test_autonomous_monitor_runs_during_fastapi_lifespan():
    import time
    from app.autonomous import get_status
    before = get_status()['total_runs']
    with TestClient(app) as lifespan_client:
        deadline = time.time() + 5
        observed = before
        while time.time() < deadline:
            observed = get_status()['total_runs']
            if observed > before:
                break
            time.sleep(0.1)
        assert observed > before, 'Background autonomous monitor did not create a startup cycle'
        health = lifespan_client.get('/api/health')
        assert health.status_code == 200
