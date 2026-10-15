# GitHub Documentation Agent — design notes

## Problem
Code changes often land without corresponding updates to READMEs, API guides, examples, or configuration references. This tool compares two Git refs and flags documentation that is likely to need review. It aims to make documentation easier to navigate by connecting code changes to the pages developers actually use.

## Workflow
1. Read the changed paths from `git diff --name-status`.
2. Ignore generated folders and unrelated file types.
3. Match changed source paths against documentation filenames, path terms, and explicit references inside docs.
4. Produce a Markdown impact report with confidence, evidence, candidate pages, and a human checklist.
5. Optionally call the installed `claude -p` CLI (`--mode claude`) to suggest edits grounded in the diff. AI output is advisory; it is not applied to repository files.
6. A CI workflow can publish the report as an artifact for review. A team can later add a protected pull-request step after evaluating false positives.

## Run it

```bash
python -m unittest discover -s tests -v
python src/main.py --help
python src/main.py --demo --repo examples/sample_repo --output build/demo-report.md
python src/main.py --repo . --base origin/main --head HEAD --output build/docs-impact.md
```

For optional Claude review, install/configure the Claude CLI and set `CLAUDE_KEY` as required by your environment, then add `--mode claude` to a Git comparison. The tool fails clearly if Claude is unavailable; heuristic mode requires no external dependencies or network access.

## Design decisions
- **Deterministic baseline first:** path matching is transparent and cheap. It provides a useful result even with no model credentials.
- **Review, not silent mutation:** automatic edits can introduce incorrect API guidance. The agent creates a report and AI suggestions for a person to verify.
- **Confidence is a triage signal:** high/medium/low reflects matching evidence, not a calibrated probability.
- **No hard-coded repository names:** matching works from paths and content in any Git repository.
- **Small interfaces:** the CLI can be called from local development, GitHub Actions, or another CI system.

## Evaluation plan
Measure precision and recall on a labelled set of changes where a reviewer marks the docs that truly needed updates. Track false-positive rate, report runtime, and percentage of recommendations accepted by maintainers. Initial target: 80%+ precision on a small manually labelled fixture set; treat this as a goal to validate, not a result already achieved. Also test empty diffs, deleted/renamed files, docs-only changes, and repositories without topic-specific documentation.

## Security and guardrails
- The default mode is offline and read-only except for the explicitly chosen report output.
- AI receives a bounded diff and candidate list, not secrets or environment variables.
- Never run commands suggested by model output.
- Do not auto-merge generated changes. Review suggestions, run tests, and verify links/examples before opening or merging a PR.
- Use least-privilege GitHub token permissions if adding PR creation to CI.

## Limitations
The heuristic uses filenames and textual references; it can miss semantic changes and may flag broad docs. Large diffs are truncated for optional model review. The current version proposes what to inspect; it does not claim that generated documentation is factually correct. Stronger future versions could parse public symbols, inspect test changes, use embeddings for topic mapping, and run documentation examples in CI.
