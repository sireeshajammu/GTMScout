"""GTMScout evaluation harness.

Runs the eval cases against the agent and prints pass/fail + reasoning, plus
aggregate metrics (pass rate, tool-call success, self-correction rate, latency, cost).

Usage:
    # against the deployed backend (default localhost, override with the env var):
    GTMSCOUT_API_BASE=https://gtm-scout-api.vercel.app python -m evals.run_eval

    # against a local backend:
    python run_local.py           # in one terminal
    python -m evals.run_eval      # in another (defaults to http://localhost:8000)

"correct" is defined per case in eval_cases.py as deterministic checks on the
STRUCTURED output (verdict/citations/budget/routing), not fuzzy text grading.
"""
import os
import sys
import time

import requests

# Windows consoles default to cp1252; force UTF-8 so arrows/em-dashes print anywhere.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

try:
    from evals.eval_cases import CASES
except ImportError:  # allow `python evals/run_eval.py`
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from evals.eval_cases import CASES

API = os.getenv("GTMSCOUT_API_BASE", "http://localhost:8000").rstrip("/")


def _call(payload):
    r = requests.post(f"{API}/api/research", json=payload, timeout=200)
    r.raise_for_status()
    return r.json()


def run():
    print(f"GTMScout evaluation — {len(CASES)} cases against {API}\n" + "=" * 72)
    passed = 0
    lat, cost, reports = [], 0.0, 0
    wb_live, self_corrected, tool_findings = 0, 0, 0

    for c in CASES:
        t0 = time.time()
        try:
            m = _call(c["input"])
        except Exception as e:  # noqa: BLE001
            m = {"kind": "error", "text": f"request failed: {e}"}
        dt = time.time() - t0
        lat.append(dt)

        results = [chk(m) for chk in c["checks"]]
        ok = all(r[0] for r in results)
        passed += ok

        # metrics from report cases
        rep = m.get("report")
        if rep:
            reports += 1
            cost += rep.get("cost", {}).get("usd", 0.0)
            if (rep.get("iterations") or 1) > 1:
                self_corrected += 1
            if any("World Bank" == c2.get("source") for c2 in rep.get("citations", [])):
                wb_live += 1
            if rep.get("research_findings"):
                tool_findings += 1

        status = "PASS" if ok else "FAIL"
        print(f"\n[{status}] {c['id']}  ({c['category']}, {dt:0.1f}s)")
        print(f"       why: {c['rationale']}")
        for (p, detail), chk in zip(results, c["checks"]):
            print(f"        {'ok ' if p else 'XX '} {getattr(chk, '__name__', 'check')}: {detail}")

    n = len(CASES)
    print("\n" + "=" * 72)
    print(f"RESULT: {passed}/{n} passed  ({passed / n * 100:0.0f}%)")
    print(f"Latency: avg {sum(lat)/n:0.1f}s, max {max(lat):0.1f}s")
    if reports:
        print(f"Report cases: {reports} | cost ${cost:0.4f} total (${cost/reports:0.4f}/report)")
        print(f"Tool-call success: World Bank live {wb_live}/{reports}, web findings {tool_findings}/{reports}")
        print(f"Self-correction rate: {self_corrected}/{reports} reports revised via the reflection loop")
    return passed == n


if __name__ == "__main__":
    import sys
    sys.exit(0 if run() else 1)
