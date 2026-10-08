
# Notes: what I learned or found surprising

- **YAML accepts almost anything.** My first `parse` step only checked "is this valid YAML?", and a cookie recipe passed, because YAML reads plain text as a single string. Fix: check for `apiVersion` and `kind`. Lesson: validate the shape you expect, not just the format.

- **Roast repeats itself when there's only one problem.** The review found 1 problem (`nginx:latest`), but the roast wrote 3 jokes about it and repeated the same fix 3 times. Cause: the prompt asks for "3 to 6 lines" and "after each joke, give the fix," so with one finding the LLM padded. Change to try: one joke per finding, with no minimum length.
