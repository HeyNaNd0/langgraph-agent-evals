# Roast My YAML 🔥

A LangGraph agent that reviews Kubernetes manifests and roasts every mistake, with a fix for each one. Evaluated with LangSmith, both offline (experiments on a labeled dataset) and online (judges on every new trace).

Built for the LangChain Technical Support Engineer take-home.

## What it does

| Input | Output |
|---|---|
| A Kubernetes manifest | A short, funny roast with a fix after each joke |
| Anything else (a recipe, broken YAML) | A polite refusal, with no LLM call and no cost |

## How it works (v2)

```mermaid
graph LR
    START([START]) --> parse["parse<br/>Python"]
    parse -->|"valid manifest"| lint["lint<br/>Python rules"]
    parse -->|"not YAML, or no apiVersion/kind"| reject["reject<br/>Python"]
    lint --> review["review<br/>LLM, structured output"]
    review --> roast["roast<br/>LLM"]
    roast --> END([END])
    reject --> END

    classDef python fill:#dbeafe,stroke:#2563eb,color:#1e3a8a
    classDef llm fill:#fef3c7,stroke:#d97706,color:#78350f
    class parse,lint,reject python
    class review,roast llm
```

Blue nodes are plain Python: free, instant, and the same on every run. Amber nodes call the LLM (`gpt-5.4-mini`): they cost tokens and can vary between runs.

### The nodes

| Node | Type | Reads | Writes | What it does |
|---|---|---|---|---|
| `parse` | Python | `manifest` | `error` | Loads the input as YAML. Sets `error` if it isn't valid YAML, or if it has no `apiVersion` and `kind`; otherwise sets `error` to `None`. |
| `lint` | Python rules | `manifest` | `findings` | Flags what's *missing*, which the LLM alone caught inconsistently: a bare Pod with no controller, a container with no CPU/memory `resources`, and a container with neither a liveness nor a readiness probe. |
| `review` | LLM, structured output | `manifest`, `findings` | `findings` | Sends the manifest to the model, which must answer as a list of `{issue, severity, fix}`, and appends those to lint's findings. It doesn't see lint's findings, so the same problem can appear twice. |
| `roast` | LLM | `findings` | `output` | Turns the findings into a short roast with a fix after each joke. With no findings, it writes a one-line grudging compliment. |
| `reject` | Python | `error` | `output` | Returns "🤨 I only roast Kubernetes manifests." plus the reason. No LLM call, no cost. |

**Routing:** after `parse`, `route_after_parse` reads `error`. If it's set, the graph goes to `reject`; otherwise it goes to `lint`. The function's `Literal["reject", "lint"]` return type is what lets LangGraph Studio draw both branches (see [`FRICTION_LOG.md`](FRICTION_LOG.md) #4).

### The state

Steps never call each other; they only read and write this shared state:

| Key | Type | Written by | Meaning |
|---|---|---|---|
| `manifest` | `str` | The caller | The input to roast |
| `error` | `str` or `None` | `parse` | Why the input was rejected; `None` means it's a manifest |
| `findings` | list of `{issue, severity, fix}` | `lint`, then `review` | Problems found; severity is `critical`, `warning`, or `nitpick` |
| `output` | `str` | `roast` or `reject` | The final message the user sees |

### Example: two inputs, step by step

| Node | `07_privileged_hostnetwork_no_resources.yaml` | A cookie recipe |
|---|---|---|
| `parse` | `error: None`, so it goes to `lint` | `error: "That's valid YAML, but not a Kubernetes manifest…"`, so it goes to `reject` |
| `lint` | +1 finding: container `frontend` has no resources | Skipped |
| `review` | +`privileged: true`, +`hostNetwork: true`, sometimes more | Skipped |
| `roast` | A joke and a fix for each finding | Skipped |
| `reject` | Skipped | Polite refusal: 0 tokens, about 0.01 s |

## Evaluation

I evaluate in two places, because they answer different questions:

| | Offline | Online |
|---|---|---|
| Runs on | A labeled dataset of 10 test cases | Every new trace in the `langgraph-agent-evals` project |
| Answers | "Is v2 better than v1 before I ship?" | "Is it still good on real traffic?" |
| Needs an answer key | Yes | No |

### Offline: experiments on a labeled dataset

Dataset: `dataset/` has 10 hand-labeled cases: 7 manifests with 1–3 planted bugs, 1 clean manifest, and 2 invalid inputs. The answer key is `dataset/answer_key.json`.

| Evaluator | Runs in | Measures |
|---|---|---|
| `catch_rate` | SDK (code) | Share of planted bugs mentioned in the findings |
| `false_alarms` | SDK (code) | Warning/critical findings on the clean manifest (lower is better) |
| `correct_route` | SDK (code) | Rejects exactly the inputs that aren't manifests |
| `roast_tone` | LangSmith UI (LLM-as-judge, bound to the dataset) | Funny, kind to the person, every joke has a fix |

#### Results (3 repetitions per example)

| Metric | v1 (LLM only) | v2 (+ lint rules) |
|---|---|---|
| catch_rate | 0.85 | **1.00** |
| correct_route | 1.00 | 1.00 |
| false_alarms (lower is better) | 2.33 | 1.33* |
| roast_tone | n/a (judge added later) | 1.00 |
| P50 latency | 3.11 s | 3.72 s |

*v2 changed nothing that affects false alarms, so I read this drop as run-to-run variance, not an improvement.

**What the data showed:** v1 caught every bug that's *written* in the YAML (privileged, hostNetwork, plaintext secrets) but missed bugs that are about something *missing* (no probes, no resources, bare Pods), and it missed them inconsistently between runs. v2 adds deterministic rules for exactly those, so they're caught every time.

**Re-run on Oct 19** (`v2-lint-ab1d8f76`): catch_rate 1.00, correct_route 1.00, roast_tone 1.00, false_alarms 1.67, P50 4.10 s. Both non-manifests were rejected with 0 tokens in 0.01 s.

### Online: evaluators on production traces

| Evaluator | Type | Checks |
|---|---|---|
| `roast_quality` | LLM-as-judge | Every joke has a correct fix; roasts the YAML, not the person; refusals pass |
| Prompt Injection | Prebuilt LLM-as-judge | Pasted YAML trying to override the agent's instructions |

Both run on 100% of new traces and need the OpenAI key saved as a LangSmith workspace secret. Why `roast_quality` exists: in a live run, the roast dropped the fix after its last joke, even though `roast_tone` scored 1.00 on every offline run.

## Run it

Tested on WSL2 (Ubuntu 24.04) with Python 3.12.

```bash
git clone https://github.com/HeyNaNd0/langgraph-agent-evals.git
cd langgraph-agent-evals
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

On Ubuntu, `python3 -m venv` needs `sudo apt install python3-venv` first.

Create a `.env` file:

```
LANGSMITH_TRACING=true
LANGSMITH_PROJECT=langgraph-agent-evals
LANGSMITH_API_KEY=...
OPENAI_API_KEY=...
```

| Command | What it does |
|---|---|
| `python smoke_test.py` | Checks your LangSmith connection (no LLM) |
| `python llm_smoke_test.py` | Checks your OpenAI key |
| `python agent.py` | Roasts 3 sample inputs |
| `python create_dataset.py` | Uploads the test cases to LangSmith |
| `python run_eval.py` | Runs the experiment and prints what went wrong |
| `langgraph dev` | Opens the agent in LangGraph Studio (first run `pip install "langgraph-cli[inmem]"`) |

## What's next

- **Close the loop:** send traces that fail `roast_quality` to an annotation queue, and add confirmed failures to the dataset as new test cases.
- **v3:** a severity rubric in the review prompt to cut false alarms on clean manifests. One change at a time, measured.
- **Judge calibration:** test both judges against deliberately bad roasts to confirm they can fail.
- **Input hardening:** an empty input crashes `parse` with `KeyError` (fix: `state.get("manifest", "")`), and multi-document YAML (`---`) is rejected as invalid (fix: `yaml.safe_load_all`).
- **Roast repetition:** the roast prompt's "3 to 6 lines" forces padding when there's only one finding.
- **Dataset v2:** split `/livez` and `/readyz` in the clean manifest so it's unambiguously clean.
- **Containerize:** build an Agent Server image and deploy it to Kubernetes.

## Notes and feedback

- [`NOTES.md`](NOTES.md): what I learned and what surprised me
- [`FRICTION_LOG.md`](FRICTION_LOG.md): product feedback from a first-time user

## How I built this

This was my first time using LangGraph and LangSmith, and I leaned heavily on AI to get here. I used Claude as a pair programmer and tutor: it explained each concept and drafted most of the code step by step. I ran, tested, and debugged every step myself, and the decisions are mine: the agent idea, the test cases and answer key, how to grade them, and what the results meant.

My honest takeaway: a newcomer can't just pick these tools up and go. The core ideas (state, nodes, edges, datasets, evaluators) clicked once I built something with them. The steep part was everything around them: setting up the environment, keeping API keys in two places, and finding things in the LangSmith UI. The specifics are in [`FRICTION_LOG.md`](FRICTION_LOG.md).

The learning curve was steep, but it was fun, and I'd enjoy helping other developers climb it.