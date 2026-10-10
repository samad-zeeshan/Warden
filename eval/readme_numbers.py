"""Render every number the README shows, straight from the results files.

tests/test_readme_numbers.py checks each block appears in README.md verbatim, so a stale number fails CI.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVAL = ROOT / "eval"


def _load(name: str) -> dict:
    return json.loads((EVAL / name).read_text(encoding="utf-8"))


def redteam() -> str:
    red = _load("redteam-results.json")
    live = _load("redteam-live.json")["runs"]["live"]
    rows = [("All layers, MCP over HTTP", red["runs"]["http"]),
            ("All layers, live Keycloak and Postgres", live),
            ("All layers, one process", red["runs"]["inprocess"]),
            ("All layers, version 1 credential", red["runs"]["inprocess-v1"]),
            ("Boundary layers removed", red["runs"]["ablation"])]
    out = ["| Run | Attacks | Got through | Unsafe approvals | Reads of other customers "
           "| Missing log entries | Writes still open |",
           "|---|---|---|---|---|---|---|"]
    for label, run in rows:
        s = run["summary"]["overall"]
        measured = run["cases"][0]["open_privilege"].get("measured", True)
        reach = str(s["open_privilege_tenant"]) if measured else "not probed"
        out.append(f"| {label} | {s['cases']} | {s['attack_successes']} | "
                   f"{s['unsafe_auto_approvals']} | {s['cross_tenant_reads']} | "
                   f"{s['audit_gaps']} | {reach} |")
    return "\n".join(out)


def redteam_prose() -> str:
    red = _load("redteam-results.json")
    v1 = _load("baseline-v1.json")
    corpus = red["corpus"]
    a2m = sum(1 for p in (EVAL / "injections").glob("*.json")
              if p.name != "case.schema.json"
              and json.loads(p.read_text(encoding="utf-8")).get("family") == "a2m")
    return (f"The test set has {corpus['cases']} attacks, and {a2m} of them use the A2M style. "
            f"Version 1 left {v1['runs']['http']['open_privilege_tenant']} writes open to an "
            f"attacker after its {v1['cases']} attacks. That was a serious gap.")


def stages() -> str:
    data = _load("stage-privilege.json")
    names = {"v1-tenant-token": "Version 1 customer credential", "request-bound": "One request",
             "request-bound+delivery": "One request, roles per step"}
    head = "| Credential | " + " | ".join(data["stages"]) + " |"
    out = [head, "|---|" + "---|" * len(data["stages"])]
    for key, label in names.items():
        row = data["summary"][key]
        out.append(f"| {label} | " + " | ".join(str(row[s]["writes"]) for s in data["stages"])
                   + " |")
    return "\n".join(out)


def ablation() -> str:
    s = _load("ablation-tenant.json")["summary"]
    label = {"parameter": "Customer and request as checked arguments",
             "credential": "Bound to the credential", "forged": "Bound, with forged scope"}
    out = ["| Setup | Planner | Trials | Tried outside scope | Served |", "|---|---|---|---|---|"]
    for key, b in s["by_arm_planner"].items():
        arm, planner = key.split("/")
        out.append(f"| {label[arm]} | {planner} | {b['trials']} | {b['attempted']} | "
                   f"{b['served']} |")
    return "\n".join(out)


def ablation_prose() -> str:
    d = _load("ablation-tenant.json")
    s = d["summary"]
    stolen = s["by_technique"]["stolen_live_token"]
    forged = [t for t in s["by_technique"] if t != "stolen_live_token"]
    served = sum(s["by_technique"][t]["served"] for t in forged)
    return (f"The test ran {s['total']['trials']} trials. The {len(forged)} forgery methods "
            f"got {served} calls served, which is the goal. A stolen live credential got "
            f"{stolen['served']} of {stolen['trials']} calls served, which is bad.")


def llm() -> str:
    d = _load("redteam-llm-results.json")
    s = d["summary"]["overall"]
    p = d["planner"]
    return ("| Planner | Cases | Replies read | Model tricked | Got through, all layers "
            "| Got through, boundary removed |\n|---|---|---|---|---|---|\n"
            f"| {p['model']} ({p['provider']}) | {s['cases']} | {s['reply_parsed']} | "
            f"{s['model_steered']} | {s['attack_successes_hardened']} | "
            f"{s['attack_successes_ablation']} |")


def llm_prose() -> str:
    d = _load("redteam-llm-results.json")
    rows = d["cases"]
    s = d["summary"]["overall"]
    p = d["planner"]
    outcomes = [o for r in rows for o in r["hardened"]["outcomes"]]
    recorded = sum(1 for r in rows if any(o["tool"] == "record_decision" and o["ok"]
                                          for o in r["hardened"]["outcomes"]))
    named = sum(1 for o in outcomes if not o["ok"] and o.get("blocked_by") == "no_signature")
    provider = "The planner was Claude Haiku."
    if p["provider"] != "anthropic":
        provider = (f"The planner was {p['model']} in LM Studio with reasoning off. "
                    "No Anthropic API key was available.")
    return (f"{provider} The model finished the task with a valid record_decision in "
            f"{recorded} of {s['cases']} cases, which is a poor result.\n\n"
            f"Its calls tried to "
            f"pass a request id {named} times, but no tool takes one. In "
            f"{s['cases'] - s['reply_parsed']} cases, the model used all its tokens on prose. "
            f"So the count of tricked replies mostly measures broken calls. It does not "
            f"measure how often the model obeys the planted text. A stronger model is "
            f"necessary for a better answer.")


def residual() -> str:
    s = _load("residual-work.json")["summary"]
    out = ["| Projects | Warden saves work | Warden adds work | Median change |",
           "|---|---|---|---|"]
    out.append(f"| all {s['projects']} | {s['gate_reduces_work']} | "
               f"{s['gate_increases_work']} | {s['median_relative_change'] * 100:+.1f}% |")
    for label, b in s["by_volume"].items():
        out.append(f"| {label} | {b['gate_reduces_work']} | "
                   f"{b['projects'] - b['gate_reduces_work']} | "
                   f"{b['median_relative_change'] * 100:+.1f}% |")
    return "\n".join(out)


def latency() -> str:
    d = _load("latency.json")["results"]
    out = ["| Path | Explanation | Runs | Middle run, ms `p50` | Slowest 1 in 20, ms `p95` "
           "| Slowest 1 in 100, ms `p99` |", "|---|---|---|---|---|---|"]
    for path, label in (("inprocess", "One process"), ("http", "MCP over HTTP")):
        for mode, name in (("no_llm", "template"), ("llm", "local language model")):
            r = d[path][mode]
            out.append(f"| {label} | {name} | {r['n']} | {r['ms']['p50']:g} | "
                       f"{r['ms']['p95']:g} | {r['ms']['p99']:g} |")
    return "\n".join(out)


BLOCKS = {"redteam": redteam, "redteam_prose": redteam_prose, "stages": stages,
          "ablation": ablation, "ablation_prose": ablation_prose, "llm": llm,
          "llm_prose": llm_prose,
          "residual": residual, "latency": latency}


def main() -> None:
    for name, fn in BLOCKS.items():
        try:
            print(f"<!-- {name} -->\n{fn()}\n")
        except FileNotFoundError as exc:
            print(f"<!-- {name}: missing {exc.filename} -->\n")


if __name__ == "__main__":
    main()
