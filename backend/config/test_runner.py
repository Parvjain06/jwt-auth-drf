"""
Test runner that records each test's outcome and writes a Markdown results
table to test_results/latest.md, ready to paste into the final report.

The first line of each test's docstring is used as its description, so every
test states the scenario and the expected result there.
"""
import platform
import unittest
from datetime import datetime, timezone
from pathlib import Path

import django
from django.conf import settings
from django.test.runner import DiscoverRunner


class RecordingResult(unittest.TextTestResult):
    records: list = []

    def _record(self, test, outcome, note=""):
        RecordingResult.records.append(
            {
                "id": test.id(),
                "description": test.shortDescription() or "",
                "outcome": outcome,
                "note": note,
            }
        )

    def addSuccess(self, test):
        super().addSuccess(test)
        self._record(test, "PASS")

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self._record(test, "FAIL", str(err[1]).splitlines()[0] if err[1] else "")

    def addError(self, test, err):
        super().addError(test, err)
        self._record(test, "ERROR", f"{err[0].__name__}: {err[1]}".splitlines()[0])

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self._record(test, "SKIP", reason)


class RecordingTestRunner(DiscoverRunner):
    def get_resultclass(self):
        # Keep Django's special result classes when --debug-sql / --pdb are used.
        return super().get_resultclass() or RecordingResult

    def run_suite(self, suite, **kwargs):
        RecordingResult.records = []
        result = super().run_suite(suite, **kwargs)
        if RecordingResult.records:
            self._write_report(result)
        return result

    def _write_report(self, result):
        records = RecordingResult.records
        passed = sum(r["outcome"] == "PASS" for r in records)
        out_dir = Path(settings.BASE_DIR) / "test_results"
        out_dir.mkdir(exist_ok=True)
        jwt = settings.SIMPLE_JWT
        lines = [
            "# Automated test results",
            "",
            f"- Run at: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
            f"- Python {platform.python_version()}, Django {django.get_version()}",
            f"- Access token lifetime: {jwt['ACCESS_TOKEN_LIFETIME']}, "
            f"refresh token lifetime: {jwt['REFRESH_TOKEN_LIFETIME']}, algorithm: {jwt['ALGORITHM']}",
            f"- Login throttle: {settings.LOGIN_THROTTLE_RATE} per client IP",
            f"- **{passed} of {len(records)} tests passed**",
            "",
            "| # | Test | Scenario and expected result | Outcome |",
            "|---|------|------------------------------|---------|",
        ]
        for i, r in enumerate(records, 1):
            name = r["id"].split(".")[-1]
            group = r["id"].split(".")[-2]
            outcome = r["outcome"] + (f" ({r['note']})" if r["note"] else "")
            desc = r["description"].replace("|", "\\|")
            lines.append(f"| {i} | `{group}.{name}` | {desc} | {outcome.replace('|', '/')} |")
        (out_dir / "latest.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"\nResults table written to {out_dir / 'latest.md'}")
