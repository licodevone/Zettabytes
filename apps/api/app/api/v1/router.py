from fastapi import APIRouter

from app.api.v1.endpoints import auth, companies, health, meta_webhook, site_chat, users

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(companies.router)
api_router.include_router(site_chat.router)
api_router.include_router(meta_webhook.router)

# Próximos prompts:
#   Prompt 2 -> WhatsApp multi-tenant (embedded signup), fluxos e mídia
#   Prompt 3 -> agents, knowledge (RAG), usage enforcement
#   Prompt 4 -> flows (CRUD do builder), inbox/live chat (WebSocket), analytics
