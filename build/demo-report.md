# Documentation Impact Report

- **Repository:** `/mnt/data/github-documentation-agent/examples/sample_repo`
- **Comparison:** `demo-base...demo-head`
- **Changed files:** 2
- **Potential documentation findings:** 2

> This is a review aid, not proof that documentation is wrong. Validate each suggestion against the code and tests before merging.

## Changed files

- `M` `src/client.py`
- `M` `src/auth.py`

## Findings

### `src/client.py` — high confidence

- **Candidate docs:** `docs/client.md`
- **Why flagged:** filename matches documentation topic; path terms overlap: client; documentation explicitly references the changed path
- **Suggested action:** Check API/CLI behavior, configuration names, and code examples; update docs only when the change alters user-visible behavior.

### `src/auth.py` — high confidence

- **Candidate docs:** `docs/auth.md`
- **Why flagged:** filename matches documentation topic; path terms overlap: auth; documentation explicitly references the changed path
- **Suggested action:** Check API/CLI behavior, configuration names, and code examples; update docs only when the change alters user-visible behavior.

## Human review checklist

- [ ] Confirm each finding corresponds to an actual user-visible change.
- [ ] Run relevant tests and verify examples against current code.
- [ ] Check links, CLI flags, configuration names, and defaults.
- [ ] Edit docs manually or open a reviewed pull request; do not merge generated changes without review.
