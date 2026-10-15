import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from doc_agent import ChangedFile, changed_files, render_report, suggest_docs  # noqa: E402


class DocumentationAgentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.repo = Path(self.temp.name)
        (self.repo / "src").mkdir()
        (self.repo / "docs").mkdir()
        (self.repo / "src" / "client.py").write_text("def create_client():\n    pass\n", encoding="utf-8")
        (self.repo / "docs" / "client.md").write_text("# Client\n\nSee src/client.py for client setup.\n", encoding="utf-8")
        (self.repo / "README.md").write_text("# Example\n", encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def test_source_change_maps_to_relevant_doc(self):
        findings = suggest_docs(self.repo, [ChangedFile("M", "src/client.py")])
        self.assertEqual(len(findings), 1)
        self.assertIn("docs/client.md", findings[0].candidate_docs)
        self.assertIn("references", findings[0].reason)

    def test_unrelated_source_change_still_flags_general_docs(self):
        findings = suggest_docs(self.repo, [ChangedFile("M", "src/unknown_component.py")])
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].confidence, "low")
        self.assertIn("README.md", findings[0].candidate_docs)

    def test_docs_change_is_reported_as_high_confidence(self):
        finding = suggest_docs(self.repo, [ChangedFile("M", "docs/client.md")])[0]
        self.assertEqual(finding.confidence, "high")
        self.assertEqual(finding.candidate_docs, ["docs/client.md"])

    def test_non_source_non_doc_change_is_ignored(self):
        self.assertEqual(suggest_docs(self.repo, [ChangedFile("M", "images/logo.png")]), [])

    def test_report_contains_review_guardrail(self):
        changes = [ChangedFile("M", "src/client.py")]
        findings = suggest_docs(self.repo, changes)
        report = render_report(self.repo, "base", "head", changes, findings)
        self.assertIn("review aid", report)
        self.assertIn("Human review checklist", report)

    def test_git_change_detection(self):
        import subprocess
        def git(*args):
            subprocess.run(["git", *args], cwd=self.repo, check=True, capture_output=True)
        git("init", "-q")
        git("config", "user.email", "test@example.com")
        git("config", "user.name", "Test User")
        git("add", ".")
        git("commit", "-m", "initial", "-q")
        (self.repo / "src" / "client.py").write_text("def create_client(timeout=5):\n    pass\n", encoding="utf-8")
        git("add", ".")
        git("commit", "-m", "change client", "-q")
        found = changed_files(self.repo, "HEAD~1", "HEAD")
        self.assertEqual([item.path for item in found], ["src/client.py"])


if __name__ == "__main__":
    unittest.main()
