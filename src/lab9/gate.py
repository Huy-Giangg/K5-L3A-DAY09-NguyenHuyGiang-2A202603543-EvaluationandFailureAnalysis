"""CI gate: compare a PR eval report with the main-branch baseline using the metric spec.

    python -m lab9.gate --pr reports/eval_workflow.json --baseline reports/baseline_v1.json

exit 0 = merge, exit 1 = blocked. Safety metrics: max 0, no averaging away.
Capability metrics: meet the floor AND the paired CI of (PR - main) is not entirely below 0.
Thresholds may only get stricter on the same eval-set version (ratchet).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from lab8.console import utf8_stdio
from lab9 import stats
from lab9.eval import SPEC, load_spec, per_item


def integrity_check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> list[str]:
    """M7 (Expert): refuse to compare reports that cannot be trusted. Return a list of problems
    (empty = trustworthy). A gate that passes a broken report is worse than no gate."""
    problems = []
    import math

    for k, v in pr.get("metrics", {}).items():
        if v is not None and isinstance(v, (int, float)):
            if math.isnan(v) or math.isinf(v):
                problems.append(f"metric {k} is NaN or inf")

    manifest = pr.get("manifest", {})
    expected_rows = manifest.get("items", 0) * len(manifest.get("seeds", []))
    if len(pr.get("rows", [])) != expected_rows:
        problems.append(f"row count {len(pr.get('rows', []))} != manifest {expected_rows}")

    pr_set = {(r.get("item_id"), r.get("seed")) for r in pr.get("rows", [])}
    base_set = {(r.get("item_id"), r.get("seed")) for r in base.get("rows", [])}
    if pr_set != base_set:
        problems.append("PR (item_id, seed) set differs from baseline")
    if len(pr.get("rows", [])) != len(pr_set):
        problems.append("PR contains duplicate (item_id, seed) rows")

    if pr.get("evaluator_failures"):
        problems.append("pr has evaluator failures")

    spec_metrics = [m["id"] for m in spec.get("metrics", [])]
    for r in pr.get("rows", []):
        for m in spec_metrics:
            if m in r and r[m] is None:
                problems.append(f"row {r.get('item_id')}@{r.get('seed')} has None for graded metric {m}")
                break
        if problems and problems[-1].startswith("row "):
            break

    if base_spec and spec.get("eval_set_version") == base_spec.get("eval_set_version"):
        base_metrics = {m["id"]: m for m in base_spec.get("metrics", [])}
        for mid, bm in base_metrics.items():
            pm = next((m for m in spec.get("metrics", []) if m["id"] == mid), None)
            if pm is None:
                problems.append(f"metric {mid} dropped from spec")
                continue
            if bm.get("blocking") and not pm.get("blocking"):
                problems.append(f"metric {mid} was blocking, now non-blocking")
            b_th = bm.get("threshold", {})
            p_th = pm.get("threshold", {})
            if "min" in b_th and ("min" not in p_th or p_th["min"] < b_th["min"]):
                problems.append(f"metric {mid} threshold min loosened from {b_th['min']} to {p_th.get('min')}")
            if "max" in b_th and ("max" not in p_th or p_th["max"] > b_th["max"]):
                problems.append(f"metric {mid} threshold max loosened from {b_th['max']} to {p_th.get('max')}")
            if "max_increase" in b_th and ("max_increase" not in p_th or p_th["max_increase"] > b_th["max_increase"]):
                problems.append(f"metric {mid} threshold max_increase loosened")
            if b_th.get("no_significant_drop") and not p_th.get("no_significant_drop"):
                problems.append(f"metric {mid} dropped no_significant_drop")

        base_slices = {s["name"]: s for s in base_spec.get("slices", [])}
        pr_slices = {s["name"]: s for s in spec.get("slices", [])}
        for sname, bs in base_slices.items():
            if sname not in pr_slices:
                problems.append(f"slice {sname} dropped from spec")
                continue
            ps = pr_slices[sname]
            if bs.get("blocking") and not ps.get("blocking"):
                problems.append(f"slice {sname} was blocking, now non-blocking")
            if "min" in bs and ("min" not in ps or ps["min"] < bs["min"]):
                problems.append(f"slice {sname} min loosened")
            if bs.get("no_significant_drop") and not ps.get("no_significant_drop"):
                problems.append(f"slice {sname} dropped no_significant_drop")

    base_slices_by_item = {r.get("item_id"): tuple(sorted(r.get("slices") or [])) for r in base.get("rows", [])}
    for r in pr.get("rows", []):
        iid = r.get("item_id")
        if iid in base_slices_by_item:
            pr_slices = tuple(sorted(r.get("slices") or []))
            if pr_slices != base_slices_by_item[iid]:
                problems.append(f"item {iid} slice tags changed from {base_slices_by_item[iid]} to {pr_slices}")
                break

    return problems


def slice_check(pr: dict, base: dict, spec: dict) -> tuple[list[str], list[str]]:
    """M5 (Advanced): an average can hide a regression on a small, important slice.
    For each entry of spec["slices"] ({"name", "metric", "min"?, "no_significant_drop"?, "blocking"}):
      - value = mean of per_item(pr, metric, slice_name=name)
      - fail if below "min", or if no_significant_drop and the paired CI over the slice's items
        lies entirely below 0
    Return (blocked ids like "slice:money_movement/pass_rate", report lines)."""
    blocked, lines = [], []
    bs = spec.get("bootstrap", {})
    for s in spec.get("slices", []):
        name = s["name"]
        metric = s.get("metric", "pass_rate")
        blocking = s.get("blocking", False)
        sid = f"slice:{name}/{metric}"

        pr_items = per_item(pr, metric, slice_name=name)
        if not pr_items:
            continue
        val = round(sum(pr_items.values()) / len(pr_items), 4)
        verdict = "ok"
        note = ""

        if "min" in s and val < s["min"]:
            verdict = "fail"

        if s.get("no_significant_drop"):
            base_items = per_item(base, metric, slice_name=name)
            keys = sorted(set(pr_items) & set(base_items))
            if keys:
                d, lo, hi = stats.paired_bootstrap(
                    [pr_items[k] for k in keys],
                    [base_items[k] for k in keys],
                    n_resamples=bs.get("n_resamples", 1000),
                    rng=bs.get("rng", 2027),
                )
                note = f"Δ {d:+.3f} CI [{lo:+.3f}, {hi:+.3f}]"
                if hi < 0:
                    verdict = "fail"

        if verdict != "ok" and blocking:
            blocked.append(sid)
        label = "BLOCK" if (verdict != "ok" and blocking) else ("warn" if verdict != "ok" else "ok")
        th_dict = {k: v for k, v in s.items() if k not in ("name", "metric", "blocking")}
        lines.append(f"  {sid:<22} {val!s:<8} {json.dumps(th_dict):<40} {note:<28} {label}")
    return blocked, lines


def check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> tuple[list[str], list[str]]:
    if pr["manifest"]["eval_set_sha"] != base["manifest"]["eval_set_sha"]:
        return ["eval_set_sha"], ["  EVAL SET differs from the baseline's: re-run the baseline on the same eval set"]
    problems = integrity_check(pr, base, spec, base_spec)
    if problems:
        return ["integrity"], [f"  INTEGRITY {p}" for p in problems]
    blocked, lines = [], []
    bs = spec.get("bootstrap", {})
    for m in spec["metrics"]:
        mid, th, val = m["id"], m.get("threshold", {}), pr["metrics"].get(m["id"])
        verdict, note = "ok", ""
        if val is None:
            verdict = "missing"
        elif "max" in th and val > th["max"]:
            verdict = "fail"
        elif "min" in th and val < th["min"]:
            verdict = "fail"
        elif "max_increase" in th and base["metrics"].get(mid):
            if val > base["metrics"][mid] * (1 + th["max_increase"]):
                verdict = "fail"
        if th.get("no_significant_drop") and val is not None:
            a, b = per_item(pr, mid), per_item(base, mid)
            keys = sorted(set(a) & set(b))
            d, lo, hi = stats.paired_bootstrap([a[k] for k in keys], [b[k] for k in keys],
                                               n_resamples=bs.get("n_resamples", 1000), rng=bs.get("rng", 2027))
            note = f"Δ {d:+.3f} CI [{lo:+.3f}, {hi:+.3f}]"
            if hi < 0:
                verdict = "fail"
        if verdict != "ok" and m.get("blocking"):
            blocked.append(mid)
        label = {"ok": "ok", "missing": "MISSING"}.get(verdict, "BLOCK" if m.get("blocking") else "warn")
        lines.append(f"  {mid:<22} {val!s:<8} {json.dumps(th):<40} {note:<28} {label}")
    if spec.get("slices"):
        sb, sl = slice_check(pr, base, spec)
        blocked += sb
        lines += sl
    return blocked, lines


def main(argv: list[str] | None = None) -> int:
    utf8_stdio()
    ap = argparse.ArgumentParser(prog="lab9.gate")
    ap.add_argument("--pr", required=True)
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--spec", default=str(SPEC))
    ap.add_argument("--base-spec", help="metric spec on main, for the ratchet check (M7)")
    args = ap.parse_args(argv)
    pr = json.loads(Path(args.pr).read_text(encoding="utf-8"))
    base = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
    base_spec = load_spec(Path(args.base_spec)) if args.base_spec else None
    blocked, lines = check(pr, base, load_spec(Path(args.spec)), base_spec)
    print(f"gate: PR {pr['run_id']} vs main {base['run_id']} · eval set {pr['manifest']['eval_set_sha']}")
    print("\n".join(lines))
    if blocked:
        print(f"exit 1 — blocked: {', '.join(blocked)}")
        return 1
    print("exit 0 — merge")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
