import unittest

from app.agents.orchestrator import PhaseConflictError
from app.agents.orchestrator import ProjectOrchestrator


class ProjectOrchestratorTests(unittest.TestCase):
    def test_valid_transition_is_allowed(self) -> None:
        orchestrator = ProjectOrchestrator()

        orchestrator.validate_transition("DRAFT", "REQUIREMENT_DRAFT")

    def test_invalid_transition_is_rejected(self) -> None:
        orchestrator = ProjectOrchestrator()

        with self.assertRaises(PhaseConflictError):
            orchestrator.validate_transition("DRAFT", "DEPLOYED")


if __name__ == "__main__":
    unittest.main()
