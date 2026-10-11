"""Run Roast My YAML against the roast-my-yaml dataset and score it."""

from dotenv import load_dotenv

load_dotenv()

from langsmith import Client

from agent import graph

# Words that show review noticed each planted bug (checked in lowercase)
BUG_KEYWORDS = {
    "latest-tag": ["latest", "pin"],
    "no-resources": ["resource", "limit", "request"],
    "no-probes": ["probe", "liveness", "readiness"],
    "privileged": ["privileged"],
    "run-as-root": ["runasuser", "as root", "root user", "uid 0", "runasnonroot"],
    "host-network": ["hostnetwork", "host network"],
    "hostpath": ["hostpath"],
    "plaintext-secret": ["secret", "password", "plaintext", "plain text"],
    "bare-pod": ["deployment", "controller", "bare"],
}


# ---------- Target: what LangSmith runs for each example ----------
def target(inputs: dict) -> dict:
    result = graph.invoke({"manifest": inputs["manifest"]})
    return {
        "error": result.get("error"),
        "findings": result.get("findings", []),
        "output": result.get("output", ""),
    }


# ---------- Evaluators: how each output gets scored ----------
def _findings_text(outputs: dict) -> str:
    return " ".join(f"{f['issue']} {f['fix']}" for f in outputs.get("findings", [])).lower()


def catch_rate(outputs: dict, reference_outputs: dict) -> dict:
    """Share of planted bugs that review mentioned (buggy manifests only)."""
    planted = reference_outputs["planted_bugs"]
    if not planted:
        return {"key": "catch_rate", "score": None, "comment": "No planted bugs"}
    text = _findings_text(outputs)
    caught = [b for b in planted if any(k in text for k in BUG_KEYWORDS[b])]
    missed = [b for b in planted if b not in caught]
    return {
        "key": "catch_rate",
        "score": len(caught) / len(planted),
        "comment": f"caught={caught} missed={missed}",
    }


def false_alarms(outputs: dict, reference_outputs: dict) -> dict:
    """On the clean manifest: count of warning/critical findings (should be 0)."""
    is_clean = not reference_outputs["planted_bugs"] and not reference_outputs["should_reject"]
    if not is_clean:
        return {"key": "false_alarms", "score": None, "comment": "Not the clean manifest"}
    serious = [f for f in outputs.get("findings", []) if f["severity"] in ("critical", "warning")]
    return {
        "key": "false_alarms",
        "score": len(serious),
        "comment": "; ".join(f["issue"] for f in serious) or "none",
    }


def correct_route(outputs: dict, reference_outputs: dict) -> bool:
    """Did the agent reject exactly when it should have?"""
    rejected = bool(outputs.get("error"))
    return rejected == reference_outputs["should_reject"]


# ---------- Run the experiment ----------
def main() -> None:
    client = Client()
    results = client.evaluate(
        target,
        data="roast-my-yaml",
        evaluators=[catch_rate, false_alarms, correct_route],
        experiment_prefix="v2-lint",
        num_repetitions=3,
        max_concurrency=2,
    )
    print(results)

    # ---------- Print only what went wrong ----------
    print("\n=== What went wrong ===")
    for row in results:
        file = row["example"].metadata.get("file", "?")
        for res in row["evaluation_results"]["results"]:
            if res.key == "catch_rate" and res.score is not None and res.score < 1:
                print(f"MISSED       {file}: {res.comment}")
            if res.key == "false_alarms" and res.score:
                print(f"FALSE ALARM  {file}: {res.comment}")
            if res.key == "correct_route" and not res.score:
                print(f"WRONG ROUTE  {file}")


if __name__ == "__main__":
    main()
