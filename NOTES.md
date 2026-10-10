
# Notes: what I learned or found surprising

- **YAML accepts almost anything.** My first `parse` step only checked "is this valid YAML?", and a cookie recipe passed, because YAML reads plain text as a single string. Fix: check for `apiVersion` and `kind`. Lesson: validate the shape you expect, not just the format.

- **Roast repeats itself when there's only one problem.** The review found 1 problem (`nginx:latest`), but the roast wrote 3 jokes about it and repeated the same fix 3 times. Cause: the prompt asks for "3 to 6 lines" and "after each joke, give the fix," so with one finding the LLM padded. Change to try: one joke per finding, with no minimum length.
- **v1 baseline (2 experiments, 3 repetitions each).** The second run caught 35 of 42 planted bugs (83%). Every miss was a bug about something missing: no-probes missed 3/3, no-resources 3/6, bare-pod 1/3. Bugs with a visible field (privileged, hostNetwork, plaintext secrets, hostPath, runAsUser, latest tag) were caught every time. Variance: file 02's no-probes was caught 3/3 in run 1 and 0/3 in run 2.
- **False alarms on the clean manifest are mostly severity inflation.** "No startupProbe", "probe timings not set", "not pinned by digest", and "no imagePullPolicy" are nitpicks labeled as warnings (noise). "Same endpoint for liveness and readiness" is debatable; in a future dataset version I'd split /livez and /readyz so the clean file is unambiguous.
- **Improvement plan, one change at a time.** v2 adds a rule-based lint step for missing resources, missing probes, and bare Pods (targets recall). A v3 would add a severity rubric to the review prompt (targets false alarms).
