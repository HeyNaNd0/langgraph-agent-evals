"""Roast My YAML: a LangGraph agent that roasts Kubernetes manifests."""

from dotenv import load_dotenv

load_dotenv()  # load API keys + LangSmith settings so every run gets traced

from typing import Literal, TypedDict

import yaml
from langchain.chat_models import init_chat_model
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field


# ---------- State: the clipboard every step reads and writes ----------
class RoastState(TypedDict, total=False):
    manifest: str  # what the user pasted
    error: str | None  # why the input was rejected (None = it's fine)
    findings: list[dict]  # problems the review step finds
    output: str  # the final message the user sees


# ---------- The form the review LLM must fill in ----------
class Finding(BaseModel):
    """One problem in the manifest."""

    issue: str = Field(description="What is wrong, in one sentence")
    severity: Literal["critical", "warning", "nitpick"] = Field(description="How bad it is")
    fix: str = Field(description="How to fix it, in one sentence")


class Review(BaseModel):
    """Every problem found in the manifest."""

    findings: list[Finding]


llm = init_chat_model("openai:gpt-5.4-mini")
reviewer = llm.with_structured_output(Review)

REVIEW_PROMPT = """You are a senior Kubernetes reviewer.
List every real problem in this manifest: security, reliability, and best practices.
Only report problems you can point to in the YAML. If it is solid, return an empty list.

Manifest:
{manifest}"""

ROAST_PROMPT = """You are a witty senior Kubernetes engineer roasting a teammate's manifest.
Write a short, funny roast (3 to 6 lines) based ONLY on the findings below.
Roast the YAML, never the person. After each joke, give the fix in one line.
If the findings say (none), write a one-line grudging compliment instead.

Findings:
{findings}"""


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


# ---------- Step: review (LLM, structured) ----------
def review(state: RoastState) -> dict:
    """LLM lists the problems as structured findings."""
    result = reviewer.invoke(REVIEW_PROMPT.format(manifest=state["manifest"]))
    return {"findings": [f.model_dump() for f in result.findings]}


# ---------- Step: roast (LLM, free text) ----------
def roast(state: RoastState) -> dict:
    """LLM turns the findings into a roast + fixes."""
    findings = state.get("findings", [])
    lines = "\n".join(f"- [{f['severity']}] {f['issue']} Fix: {f['fix']}" for f in findings) or "(none)"
    reply = llm.invoke(ROAST_PROMPT.format(findings=lines))
    return {"output": reply.content}


# ---------- Step: reject (plain Python, no LLM) ----------
def reject(state: RoastState) -> dict:
    """Friendly message for input we can't roast."""
    return {"output": f"🤨 I only roast Kubernetes manifests. {state['error']}"}


# ---------- Conditional edge: read the clipboard, pick the next step ----------
def route_after_parse(state: RoastState) -> str:
    if state["error"]:
        return "reject"
    return "review"


# ---------- Wire the graph ----------
builder = StateGraph(RoastState)
builder.add_node("parse", parse)
builder.add_node("review", review)
builder.add_node("roast", roast)
builder.add_node("reject", reject)
builder.add_edge(START, "parse")
builder.add_conditional_edges("parse", route_after_parse)
builder.add_edge("review", "roast")
builder.add_edge("roast", END)
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
        print(f"\n=== {name} ({len(result.get('findings', []))} findings) ===")
        print(result["output"])