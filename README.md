# Problem 2.12: GitHub Documentation Agent

A small CLI that flags docs likely affected by code changes. It runs without external services in heuristic mode and can optionally use the Claude CLI to produce a review proposal. It does not silently rewrite or merge documentation.

## Quick start

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python src/main.py --help
python src/main.py --demo --repo examples/sample_repo --output build/demo-report.md
```

For a real Git comparison:

```bash
python src/main.py --repo /path/to/repo --base origin/main --head HEAD --output build/docs-impact.md
```

Optional AI review (requires a configured `claude` CLI and `CLAUDE_KEY`):

```bash
python src/main.py --repo . --base origin/main --head HEAD --mode claude --output build/docs-impact.md
```

See [`docs/README.md`](docs/README.md) for architecture, evaluation plan, and guardrails.
