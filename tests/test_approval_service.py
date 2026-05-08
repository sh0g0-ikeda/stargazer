import unittest

from app.approvals.models import ApprovalDecision
from app.approvals.models import ApprovalGate
from app.approvals.repository import InMemoryApprovalRepository
from app.approvals.service import ApprovalService
from app.core.errors import PhaseConflictAppError
from app.projects.models import ProjectPhase
from app.projects.repository import InMemoryProjectRepository
from app.projects.service import ProjectService


class ApprovalServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_approved_requirement_gate_records_history_and_advances_phase(self) -> None:
        project_service = ProjectService(repository=InMemoryProjectRepository())
        approval_repository = InMemoryApprovalRepository()
        service = ApprovalService(
            repository=approval_repository,
            project_service=project_service,
        )
        project = await project_service.create_project(
            owner_uid="demo-user",
            name="Support Desk",
            idea="問い合わせ管理アプリ",
        )
        await project_service.transition_project(
            project_id=project.id,
            next_phase=ProjectPhase.REQUIREMENT_DRAFT,
        )

        approval = await service.decide(
            project_id=project.id,
            gate=ApprovalGate.REQUIREMENTS,
            decision=ApprovalDecision.APPROVED,
            decided_by="demo-user",
            rationale="Looks good",
            snapshot={"document_id": "doc-1"},
        )

        payloads = await service.list_payloads(project.id)
        updated_project = await project_service.get_project_payload(project.id)

        self.assertEqual(approval.decision, ApprovalDecision.APPROVED)
        self.assertEqual(updated_project["phase"], "REQUIREMENT_APPROVED")
        self.assertEqual(payloads[0]["snapshot"], {"document_id": "doc-1"})

    async def test_invalid_gate_phase_does_not_record_approval(self) -> None:
        project_service = ProjectService(repository=InMemoryProjectRepository())
        approval_repository = InMemoryApprovalRepository()
        service = ApprovalService(
            repository=approval_repository,
            project_service=project_service,
        )
        project = await project_service.create_project(
            owner_uid="demo-user",
            name="Support Desk",
            idea="問い合わせ管理アプリ",
        )

        with self.assertRaises(PhaseConflictAppError):
            await service.decide(
                project_id=project.id,
                gate=ApprovalGate.DESIGN,
                decision=ApprovalDecision.APPROVED,
                decided_by="demo-user",
            )

        self.assertEqual(await service.list_payloads(project.id), [])


if __name__ == "__main__":
    unittest.main()
