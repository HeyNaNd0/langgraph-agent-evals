
# Notes: what I learned or found surprising

- **YAML accepts almost anything.** My first `parse` step only checked "is this valid YAML?", and a cookie recipe passed, because YAML reads plain text as a single string. Fix: check for `apiVersion` and `kind`. Lesson: validate the shape you expect, not just the format.
