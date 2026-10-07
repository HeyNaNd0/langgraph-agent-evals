"""Roast My YAML: a LangGraph agent that roasts Kubernetes manifests."""

from dotenv import load_dotenv

load_dotenv()  # load LangSmith settings so every run gets traced

from typing import TypedDict

import yaml
from langgraph.graph import END, START, StateGraph


# ---------- State: the clipboard every step reads and writes ----------
class RoastState(TypedDict, total=False):
    manifest: str  # what the user pasted
    error: str | None  # why the input was rejected (None = it's fine)
    findings: list[dict]  # problems the review step finds (added in 3.4)
    roast: str  # the final message the user sees


# ---------- Step: parse (plain Python, no LLM) ----------
def parse(state: RoastState) -> dict:
    """Check the input is a Kubernetes manifest. No LLM."""
    try:
        doc = yaml.safe_load(state["manifest"])
    except yaml.YAMLError:
        return {"error": "That isn't valid YAML."}
    if not isinstance(doc, dict) or "apiVersion" not in doc or "kind" not in doc:
        return {"error": "That's valid YAML, but not a Kubernetes manifest (no apiVersion/kind)."}
    return {"error": None}


# ---------- Step: reject (plain Python, no LLM) ----------
def reject(state: RoastState) -> dict:
    """Friendly message for input we can't roast."""
    return {"roast": f"🤨 I only roast Kubernetes manifests. {state['error']}"}


# ---------- Conditional edge: read the clipboard, pick the next step ----------
def route_after_parse(state: RoastState) -> str:
    if state["error"]:
        return "reject"
    return END  # 3.4 changes this to "review"


# ---------- Wire the graph ----------
builder = StateGraph(RoastState)
builder.add_node("parse", parse)
builder.add_node("reject", reject)
builder.add_edge(START, "parse")
builder.add_conditional_edges("parse", route_after_parse)
builder.add_edge("reject", END)
graph = builder.compile()


# ---------- Test inputs ----------
SAMPLE_POD = """
apiVersion: v1
kind: Pod
metadata:
  name: web
spec:
  containers:
    - name: web
      image: nginx:latest
"""

SAMPLE_RECIPE = "Mix 2 cups flour, 1 cup sugar, and 2 eggs. Bake at 350F for 12 minutes."

SAMPLE_BROKEN = "apiVersion: v1\nkind: [Pod"


if __name__ == "__main__":
    for name, text in [("pod", SAMPLE_POD), ("recipe", SAMPLE_RECIPE), ("broken", SAMPLE_BROKEN)]:
        result = graph.invoke({"manifest": text})
        print(f"{name:<7}->", result.get("roast", "(valid: review comes in 3.4)"))