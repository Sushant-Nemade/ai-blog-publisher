import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class OfflineCliTests(unittest.TestCase):
    def invoke(self, *arguments):
        environment = {key: value for key, value in os.environ.items()
                       if not any(term in key.upper() for term in ("KEY", "TOKEN", "SENTRY", "OPIK"))}
        environment["PYTHONPATH"] = str(ROOT)
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        script = """import runpy, socket, sys
def forbidden(*arguments, **kwargs):
    raise AssertionError('network forbidden in offline CLI')
socket.socket = forbidden
socket.create_connection = forbidden
sys.argv = ['blogboard.run', *sys.argv[1:]]
runpy.run_module('blogboard.run', run_name='__main__')
"""
        with tempfile.TemporaryDirectory() as folder:
            result = subprocess.run([sys.executable, "-c", script, *arguments],
                                    cwd=folder, env=environment, capture_output=True, text=True, timeout=10)
            self.assertEqual(list(Path(folder).iterdir()), [])
        return result

    def test_help_without_credentials(self):
        result = self.invoke("--help")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_dry_run_without_credentials(self):
        for arguments in (("--dry-run",), ("--ainews", "--dry-run")):
            with self.subTest(arguments=arguments):
                result = self.invoke(*arguments)
                self.assertEqual(result.returncode, 0, result.stderr)
                document = json.loads(result.stdout)
                self.assertEqual(document["network_calls"], 0)
                self.assertFalse(document["published"])

    def test_invalid_date_is_rejected(self):
        result = self.invoke("--dry-run", "--date", "2026-02-30")
        self.assertEqual(result.returncode, 2)

    def test_approval_requires_draft(self):
        result = self.invoke("--approve", "wrong")
        self.assertEqual(result.returncode, 2)


if __name__ == "__main__":
    unittest.main()