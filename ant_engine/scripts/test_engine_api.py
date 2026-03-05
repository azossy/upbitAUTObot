#!/usr/bin/env python3
"""개미엔진(AntEngine) HTTP API 검증: /health, /version, POST /signal (입출력 가이드 준수)."""
import json
import sys
import time
import urllib.request
import urllib.error

BASE = "http://127.0.0.1:9100"

def req(method, path, body=None):
    url = BASE + path
    data = json.dumps(body).encode() if body else None
    r = urllib.request.Request(url, data=data, method=method)
    if data:
        r.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(r, timeout=5) as res:
        return res.status, json.loads(res.read().decode())

def main():
    ok = 0
    # 1. GET /health
    try:
        status, out = req("GET", "/health")
        assert status == 200 and out.get("status") == "ok", out
        print("[PASS] GET /health")
        ok += 1
    except Exception as e:
        print("[FAIL] GET /health:", e)
        return 1

    # 2. GET /version
    try:
        status, out = req("GET", "/version")
        assert status == 200, out
        assert out.get("engine") == "AntEngine" and "version" in out and out.get("schema_version") == "1.0", out
        print("[PASS] GET /version", out)
        ok += 1
    except Exception as e:
        print("[FAIL] GET /version:", e)
        return 1

    # 3. POST /signal — 최소 유효 body (입출력 가이드 §2)
    body = {
        "request_id": "test-req-1",
        "timestamp_utc": "2026-03-05T12:00:00Z",
        "market": "KRW-BTC",
        "mode": "both",
        "candles_1h": [],
        "candles_4h": [],
        "current_price": 95000000,
        "positions": [],
        "balance_krw": 10000000,
        "config": {
            "max_positions": 7,
            "stop_loss_pct": 2.5,
            "take_profit_pct": 7.0,
            "max_investment_ratio": 0.5,
            "event_window_active": False,
        },
    }
    try:
        status, out = req("POST", "/signal", body)
        assert status == 200, out
        assert out.get("status") == "ok" and out.get("request_id") == "test-req-1", out
        assert out.get("signal") in ("hold", "buy", "sell") and "reason_code" in out, out
        print("[PASS] POST /signal (valid) ->", out.get("signal"), out.get("reason_code"))
        ok += 1
    except Exception as e:
        print("[FAIL] POST /signal:", e)
        return 1

    # 4. POST /signal — 잘못된 JSON → 400 + error
    try:
        url = BASE + "/signal"
        r = urllib.request.Request(url, data=b"{ invalid }", method="POST")
        r.add_header("Content-Type", "application/json")
        urllib.request.urlopen(r, timeout=5)
        print("[FAIL] POST /signal invalid JSON: expected 400")
        return 1
    except urllib.error.HTTPError as e:
        if e.code == 400:
            print("[PASS] POST /signal (invalid JSON) -> 400")
            ok += 1
        else:
            print("[FAIL] POST /signal invalid JSON: status", e.code)
            return 1
    except Exception as e:
        print("[FAIL] POST /signal invalid:", e)
        return 1

    print("\n엔진 API 검증 통과:", ok, "/ 4")
    return 0

if __name__ == "__main__":
    sys.exit(main())
