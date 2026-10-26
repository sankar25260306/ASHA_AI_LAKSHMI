"""Lightweight local HTTP latency sampler for the running ASHA AI demo.

Run from backend/ while the API runs on localhost:8000:
  py benchmark_api.py --iterations 30
The output is a local prototype measurement, not a production load benchmark.
"""
from __future__ import annotations
import argparse
import getpass
import json
import os
import statistics
import time
import urllib.error
import urllib.request

BASE = os.environ.get("ASHA_API_BASE_URL", "http://127.0.0.1:8000")


def request_json(path: str, method: str = "GET", body: dict | None = None, token: str | None = None):
    raw = None if body is None else json.dumps(body).encode("utf-8")
    headers = {"Accept": "application/json"}
    if raw is not None:
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(BASE + path, data=raw, headers=headers, method=method)
    start = time.perf_counter()
    with urllib.request.urlopen(req, timeout=30) as response:
        payload = response.read()
        elapsed_ms = (time.perf_counter() - start) * 1000
        return json.loads(payload.decode("utf-8")), elapsed_ms, len(payload)


def percentile(values: list[float], pct: float) -> float:
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    index = max(0, min(len(ordered) - 1, round((pct / 100) * (len(ordered) - 1))))
    return ordered[index]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=30)
    args = parser.parse_args()
    if not 5 <= args.iterations <= 500:
        parser.error("--iterations must be between 5 and 500")

    try:
        login, _, _ = request_json(
            "/api/network/auth/login", "POST",
            {"role": "super_admin", "username": "superadmin", "password": os.environ.get("ASHA_BENCHMARK_PASSWORD") or getpass.getpass("Local Super Admin password: ")},
        )
        token = login["access_token"]
    except (urllib.error.URLError, urllib.error.HTTPError, KeyError, json.JSONDecodeError) as exc:
        print(f"Cannot log in to {BASE}: {exc}")
        return 1

    endpoints = [
        ("health", "/api/health", None),
        ("resource_snapshots_1000", "/api/resources/snapshots?limit=1000", None),
        ("pharmacy_stock_1000", "/api/network/pharmacy/stock?limit=1000", token),
        ("dashboard_overview", "/api/dashboard/overview", None),
        ("ml_status", "/api/ml/resource-risk/status", None),
    ]
    summary = {"base_url": BASE, "iterations": args.iterations, "note": "Local prototype measurement; not production load test."}
    for name, path, auth in endpoints:
        samples, byte_sizes = [], []
        try:
            for _ in range(args.iterations):
                _, elapsed, size = request_json(path, token=auth)
                samples.append(elapsed)
                byte_sizes.append(size)
        except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError) as exc:
            print(f"Request failed for {name}: {exc}")
            return 1
        summary[name] = {
            "http_samples": len(samples),
            "min_ms": round(min(samples), 2),
            "median_ms": round(statistics.median(samples), 2),
            "p95_ms": round(percentile(samples, 95), 2),
            "max_ms": round(max(samples), 2),
            "response_bytes_avg": round(statistics.mean(byte_sizes)),
        }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
