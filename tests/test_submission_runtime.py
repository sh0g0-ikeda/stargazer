import os
from pathlib import Path
from unittest import mock
import unittest

from scripts.serve_demo import _default_port


REPO_ROOT = Path(__file__).resolve().parents[1]


class SubmissionRuntimeTests(unittest.TestCase):
    def test_default_port_reads_cloud_run_port_env(self) -> None:
        with mock.patch.dict(os.environ, {"PORT": "9090"}):
            self.assertEqual(_default_port(), 9090)

    def test_default_port_rejects_invalid_value(self) -> None:
        with mock.patch.dict(os.environ, {"PORT": "invalid"}):
            with self.assertRaises(SystemExit):
                _default_port()

    def test_self_deploy_files_are_present(self) -> None:
        self.assertTrue((REPO_ROOT / "Dockerfile").is_file())
        self.assertTrue((REPO_ROOT / "pipelines" / "deploy-self.cloudbuild.yaml").is_file())
        self.assertTrue((REPO_ROOT / ".github" / "workflows" / "ci.yml").is_file())
        self.assertTrue((REPO_ROOT / "LICENSE").is_file())
        self.assertTrue((REPO_ROOT / "NOTICE").is_file())

    def test_self_deploy_cloudbuild_runs_tests_and_deploys_cloud_run(self) -> None:
        cloudbuild = (REPO_ROOT / "pipelines" / "deploy-self.cloudbuild.yaml").read_text(encoding="utf-8")

        self.assertIn("unittest", cloudbuild)
        self.assertIn("docker", cloudbuild)
        self.assertIn("run", cloudbuild)
        self.assertIn("deploy", cloudbuild)
        self.assertIn("--set-env-vars=TARGET_PROJECT_ID=${_TARGET_PROJECT_ID}", cloudbuild)


if __name__ == "__main__":
    unittest.main()
