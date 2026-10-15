#!/usr/bin/env python3
"""CLI entry point for the GitHub Documentation Agent."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from doc_agent import ChangedFile, Finding, changed_files, claude_review, demo_report, render_report, suggest_docs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Flag documentation that may be outdated after Git changes. Generates reviewable reports; never silently edits docs.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--repo", default=".", help="Path to a Git repository (or sample repo for --demo)")
    parser.add_argument("--base", default="HEAD~1", help="Base Git ref for comparison")
    parser.add_argument("--head", default="HEAD", help="Head Git ref for comparison")
    parser.add_argument("--output", default="docs/agent-report.md", help="Report output path, relative to current directory unless absolute")
    parser.add_argument("--mode", choices=["heuristic", "claude"], default="heuristic", help="Deterministic offline mode or optional Claude CLI review")
    parser.add_argument("--demo", action="store_true", help="Run a deterministic example without needing Git history")
    parser.add_argument("--json", action="store_true", help="Also print machine-readable findings to stdout")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo = Path(args.repo).resolve()
    if not repo.is_dir():
        print(f"error: repository path does not exist: {repo}", file=sys.stderr)
        return 2
    try:
        if args.demo:
            changes, findings = demo_report(repo)
            base, head = "demo-base", "demo-head"
        else:
            changes = changed_files(repo, args.base, args.head)
            findings = suggest_docs(repo, changes)
            base, head = args.base, args.head
        ai_review = None
        if args.mode == "claude":
            if args.demo:
                raise RuntimeError("--mode claude is only supported with a Git comparison, not --demo")
            ai_review = claude_review(repo, args.base, args.head, findings)
        report = render_report(repo, base, head, changes, findings, ai_review)
        output = Path(args.output)
        if not output.is_absolute():
            output = Path.cwd() / output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(report, encoding="utf-8")
        print(f"Report written to: {output}")
        print(f"Changed files: {len(changes)}; findings: {len(findings)}")
        if args.json:
            print(json.dumps({"changes": [c.__dict__ for c in changes], "findings": [f.__dict__ for f in findings]}, indent=2))
        return 0
    except (RuntimeError, OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
