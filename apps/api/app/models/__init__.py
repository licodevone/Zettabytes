"""Importa todos os models para registrá-los no `Base.metadata` (necessário ao Alembic)."""

from app.db.base import Base
from app.models.ai import AIAgent, KnowledgeBase, KnowledgeChunk, KnowledgeDocument
from app.models.billing import BillingEvent, Plan, Subscription, UsageCounter
from app.models.chat import ChatSession, Message
from app.models.company import Company
from app.models.contact import Contact
from app.models.flow import Edge, Flow, Node
from app.models.user import Membership, RefreshToken, User
from app.models.whatsapp import WhatsAppConnection

__all__ = [
    "AIAgent",
    "Base",
    "BillingEvent",
    "ChatSession",
    "Company",
    "Contact",
    "Edge",
    "Flow",
    "KnowledgeBase",
    "KnowledgeChunk",
    "KnowledgeDocument",
    "Membership",
    "Message",
    "Node",
    "Plan",
    "RefreshToken",
    "Subscription",
    "UsageCounter",
    "User",
    "WhatsAppConnection",
]
