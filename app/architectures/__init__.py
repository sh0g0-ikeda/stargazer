"""Architecture proposal domain."""

from app.architectures.models import ArchitectureEdge
from app.architectures.models import ArchitectureNode
from app.architectures.models import ArchitectureProposal
from app.architectures.models import ArchitectureSpec
from app.architectures.repository import InMemoryArchitectureRepository
from app.architectures.service import ArchitectureService

__all__ = [
    "ArchitectureEdge",
    "ArchitectureNode",
    "ArchitectureProposal",
    "ArchitectureService",
    "ArchitectureSpec",
    "InMemoryArchitectureRepository",
]
