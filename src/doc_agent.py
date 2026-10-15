"""Detect documentation likely affected by source-code changes.

The first pass is deterministic and works offline. An optional Claude CLI pass can
add richer reasoning, but its output is always treated as a proposal for review.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

SOURCE_SUFFIXES = {".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".java", ".cs", ".yaml", ".yml", ".toml"}
DOC_SUFFIXES = {".md", ".mdx", ".rst", ".adoc"}
IGNORE_PARTS = {".git", ".venv", "venv", "node_modules", "dist", "build", "__pycache__"}


@dataclass
class ChangedFile:
    status: str
    path: str


@dataclass
class Finding:
    changed_file: str
    candidate_docs: list[str]
    confidence: str
    reason: str
    suggested_action: str


def run_git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=repo, text=True, capture_output=True, check=False
    )
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or "unknown git error"
        raise RuntimeError(f"git {' '.join(args)} failed: {message}")
    return result.stdout


def changed_files(repo: Path, base: str, head: str) -> list[ChangedFile]:
    """Return files changed between two git refs, including renames where possible."""
    raw = run_git(repo, "diff", "--name-status", "--find-renames", f"{base}...{head}")
    changes: list[ChangedFile] = []
    for line in raw.splitlines():
        parts = line.split("\t")
        if len(parts) >= 3 and parts[0].startswith("R"):
            changes.append(ChangedFile(parts[0], parts[2]))
        elif len(parts) >= 2:
            changes.append(ChangedFile(parts[0], parts[1]))
    return changes


def iter_docs(repo: Path) -> list[Path]:
    docs: list[Path] = []
    for path in repo.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in DOC_SUFFIXES:
            continue
        if any(part in IGNORE_PARTS for part in path.parts):
            continue
        # Do not inspect generated output or the agent's own report.
        if ".agent" in path.parts:
            continue
        docs.append(path)
    return sorted(docs)


def tokens(path: str) -> set[str]:
    words = re.findall(r"[a-z0-9]+", path.lower())
    stop = {"src", "lib", "app", "index", "main", "test", "tests", "docs", "doc", "the", "and"}
    return {w for w in words if w not in stop and len(w) > 1}


def suggest_docs(repo: Path, changes: Iterable[ChangedFile]) -> list[Finding]:
    """Map changed code to relevant docs using paths, references, and content overlap."""
    docs = iter_docs(repo)
    doc_text: dict[Path, str] = {}
    for doc in docs:
        try:
            doc_text[doc] = doc.read_text(encoding="utf-8", errors="replace")
        except OSError:
            doc_text[doc] = ""

    findings: list[Finding] = []
    for change in changes:
        changed_path = Path(change.path)
        if changed_path.suffix.lower() in DOC_SUFFIXES:
            findings.append(Finding(
                change.path, [change.path], "high",
                "A documentation file itself changed.",
                "Review the edited page for consistency with the related code and examples.",
            ))
            continue
        if changed_path.suffix.lower() not in SOURCE_SUFFIXES:
            continue

        source_tokens = tokens(change.path)
        basename = changed_path.stem.lower()
        candidates: list[tuple[int, Path, list[str]]] = []
        for doc, content in doc_text.items():
            doc_tokens = tokens(str(doc.relative_to(repo)))
            content_lower = content.lower()
            score = 0
            reasons: list[str] = []
            if basename not in {"main", "index", "app"} and basename in doc_tokens:
                score += 4
                reasons.append("filename matches documentation topic")
            overlap = source_tokens & doc_tokens
            if overlap:
                score += min(3, len(overlap))
                reasons.append("path terms overlap: " + ", ".join(sorted(overlap)[:4]))
            rel_source = change.path.replace("\\", "/")
            if rel_source.lower() in content_lower:
                score += 5
                reasons.append("documentation explicitly references the changed path")
            # A function/class name in the diff can be included by callers in future versions.
            if score > 0:
                candidates.append((score, doc, reasons))

        candidates.sort(key=lambda item: (-item[0], str(item[1])))
        selected = candidates[:3]
        if selected:
            best_score = selected[0][0]
            confidence = "high" if best_score >= 5 else "medium" if best_score >= 3 else "low"
            candidate_paths = [str(doc.relative_to(repo)) for _, doc, _ in selected]
            reason = "; ".join(selected[0][2])
        else:
            confidence = "low"
            candidate_paths = [str(doc.relative_to(repo)) for doc in docs if doc.name.lower() in {"readme.md", "contributing.md"}][:2]
            reason = "No strong topic match found; general project documentation may still need review."
        findings.append(Finding(
            change.path, candidate_paths, confidence, reason,
            "Check API/CLI behavior, configuration names, and code examples; update docs only when the change alters user-visible behavior.",
        ))
    return findings


def git_diff(repo: Path, base: str, head: str, max_chars: int = 16000) -> str:
    try:
        return run_git(repo, "diff", "--no-ext-diff", "--unified=3", f"{base}...{head}")[:max_chars]
    except RuntimeError:
        return "Diff unavailable. Review the changed paths and current files manually."


def claude_review(repo: Path, base: str, head: str, findings: list[Finding]) -> str:
    """Ask the installed Claude CLI for a proposed review; never applies edits."""
    if not os.environ.get("CLAUDE_KEY"):
        raise RuntimeError("CLAUDE_KEY is not set; use --mode heuristic or configure Claude CLI.")
    prompt = (
        "You are reviewing whether developer documentation is stale after code changes. "
        "Use only the supplied diff and file excerpts. Do not invent behavior. "
        "Return concise Markdown with: affected docs, evidence from diff, proposed edits, "
        "uncertainties, and tests a human should run. Do not claim edits were applied.\n\n"
        f"Candidate findings:\n{json.dumps([asdict(f) for f in findings], indent=2)}\n\n"
        f"Diff:\n{git_diff(repo, base, head)}\n"
    )
    result = subprocess.run(["claude", "-p", prompt], cwd=repo, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        raise RuntimeError("Claude CLI failed: " + (result.stderr.strip() or "unknown error"))
    return result.stdout.strip()


def render_report(repo: Path, base: str, head: str, changes: list[ChangedFile], findings: list[Finding], ai_review: str | None = None) -> str:
    lines = [
        "# Documentation Impact Report", "",
        f"- **Repository:** `{repo}`", f"- **Comparison:** `{base}...{head}`",
        f"- **Changed files:** {len(changes)}", f"- **Potential documentation findings:** {len(findings)}", "",
        "> This is a review aid, not proof that documentation is wrong. Validate each suggestion against the code and tests before merging.", "",
        "## Changed files", "",
    ]
    if changes:
        lines.extend(f"- `{c.status}` `{c.path}`" for c in changes)
    else:
        lines.append("No changes found for this comparison.")
    lines.extend(["", "## Findings", ""])
    if findings:
        for finding in findings:
            lines.extend([
                f"### `{finding.changed_file}` — {finding.confidence} confidence", "",
                f"- **Candidate docs:** {', '.join(f'`{p}`' for p in finding.candidate_docs) if finding.candidate_docs else 'No candidate found'}",
                f"- **Why flagged:** {finding.reason}", f"- **Suggested action:** {finding.suggested_action}", "",
            ])
    else:
        lines.append("No source or documentation changes were found that need review.")
    if ai_review:
        lines.extend(["## AI-assisted review (proposal only)", "", ai_review, ""])
    lines.extend([
        "## Human review checklist", "",
        "- [ ] Confirm each finding corresponds to an actual user-visible change.",
        "- [ ] Run relevant tests and verify examples against current code.",
        "- [ ] Check links, CLI flags, configuration names, and defaults.",
        "- [ ] Edit docs manually or open a reviewed pull request; do not merge generated changes without review.", "",
    ])
    return "\n".join(lines)


def demo_report(repo: Path) -> tuple[list[ChangedFile], list[Finding]]:
    changes = [
        ChangedFile("M", "src/client.py"),
        ChangedFile("M", "src/auth.py"),
    ]
    return changes, suggest_docs(repo, changes)
