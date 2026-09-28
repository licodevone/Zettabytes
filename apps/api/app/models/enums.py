from enum import StrEnum


class MemberRole(StrEnum):
    OWNER = "owner"
    ADMIN = "admin"
    AGENT = "agent"  # atendente humano do Live Chat
    VIEWER = "viewer"


# ─── Billing ─────────────────────────────────────────────────


class BillingProvider(StrEnum):
    STRIPE = "stripe"
    ASAAS = "asaas"


class SubscriptionStatus(StrEnum):
    TRIALING = "trialing"
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    INCOMPLETE = "incomplete"
    PAUSED = "paused"


class BillingInterval(StrEnum):
    MONTH = "month"
    YEAR = "year"


# ─── WhatsApp ────────────────────────────────────────────────


class ConnectionStatus(StrEnum):
    PENDING = "pending"  # Embedded Signup iniciado, aguardando troca do code por token
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    BANNED = "banned"
    ERROR = "error"


# ─── Flows ───────────────────────────────────────────────────


class FlowStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class FlowTriggerType(StrEnum):
    KEYWORD = "keyword"
    DEFAULT_REPLY = "default_reply"  # nenhum outro gatilho casou
    WELCOME = "welcome"  # primeira mensagem do contato
    AD_CLICK = "ad_click"  # Click-to-WhatsApp Ads (referral)
    API = "api"  # disparado por integração externa
    MANUAL = "manual"


class NodeType(StrEnum):
    START = "start"
    SEND_MESSAGE = "send_message"
    ASK_QUESTION = "ask_question"
    BUTTONS = "buttons"
    LIST = "list"
    CONDITION = "condition"
    AI_AGENT = "ai_agent"
    ACTION = "action"  # tags, atributos, webhooks externos
    DELAY = "delay"
    HANDOFF = "handoff"  # transfere para humano
    END = "end"


# ─── Conversas ───────────────────────────────────────────────


class SessionStatus(StrEnum):
    OPEN = "open"
    PENDING = "pending"  # aguardando atendente humano
    CLOSED = "closed"


class SessionMode(StrEnum):
    FLOW = "flow"  # executando um fluxo determinístico
    AI = "ai"  # agente de IA respondendo
    HUMAN = "human"  # IA pausada, atendente no controle


class MessageDirection(StrEnum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"


class SenderType(StrEnum):
    CONTACT = "contact"
    FLOW = "flow"
    AI = "ai"
    AGENT = "agent"
    SYSTEM = "system"


class MessageType(StrEnum):
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    DOCUMENT = "document"
    STICKER = "sticker"
    LOCATION = "location"
    CONTACTS = "contacts"
    INTERACTIVE = "interactive"
    TEMPLATE = "template"
    REACTION = "reaction"
    UNSUPPORTED = "unsupported"


class MessageStatus(StrEnum):
    RECEIVED = "received"
    QUEUED = "queued"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"


# ─── IA / RAG ────────────────────────────────────────────────


class AgentKind(StrEnum):
    ROUTER = "router"
    SALES = "sales"
    SUPPORT = "support"
    SCHEDULING = "scheduling"
    QUALIFIER = "qualifier"
    CUSTOM = "custom"


class DocumentStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class DocumentSourceType(StrEnum):
    FILE = "file"
    URL = "url"
    TEXT = "text"
    FAQ = "faq"
