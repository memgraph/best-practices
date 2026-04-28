---
name: add-best-practice
description: Use this skill when adding a new best practice example to the Memgraph best-practices repository. Walks through categorization, code documentation, dependencies, and README updates so the contribution matches the repo's conventions.
---

# Add a Memgraph best practice

Follow this checklist when adding a new best practice to this repo. Work through each item — do not skip steps.

## General checklist

- [ ] **Categorize the best practice** inside one of the existing top-level directories (e.g. `import/`, `querying/`, `graphrag/`, `ha/`, `debugging/`, `k8s/`, `python/`, `java/`, `use_cases/`, etc.). If no directory fits, ask the user before creating a new top-level category.
- [ ] **Provide the code** for the best practice in its own subdirectory under the chosen category.
- [ ] **Document the code thoroughly** — inline comments where intent is non-obvious, plus a `README.md` in the example directory explaining what it does and why.
- [ ] **Add a `requirements.txt`** (or equivalent dependency manifest for non-Python examples) so users can install dependencies with one command.
- [ ] **Add the example to the main [`README.md`](../../README.md)** under the appropriate section in the "List of best practices".

## Example `README.md` checklist

The `README.md` inside the new best-practice directory must include:

- [ ] **Steps to run Memgraph** — the exact `docker run` / `docker compose` / install command needed for this example. Include any non-default flags (e.g. `--schema-info-enabled`, `--storage-mode`).
- [ ] **Tested Memgraph version** — pin the version you verified the example against (e.g. "Tested on Memgraph 2.18.1").
- [ ] **Edition** — state explicitly whether this is a **Community** or **Enterprise** capability. If Enterprise, mention the license requirement.

## Workflow

1. Ask the user which category the best practice belongs to (if not obvious).
2. Create the example directory and code.
3. Write the example `README.md` with all required sections above.
4. Add `requirements.txt` (or equivalent).
5. Update the root `README.md` "List of best practices" with a link to the new example.
6. Run through both checklists above and confirm every item before reporting the task complete.
