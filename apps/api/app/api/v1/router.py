from fastapi import APIRouter

from app.api.v1.endpoints import auth, companies, health, users

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(companies.router)

# Próximos prompts:
#   Prompt 2 -> whatsapp (embedded signup), webhooks/meta, messages
#   Prompt 3 -> agents, knowledge (RAG), usage enforcement
#   Prompt 4 -> flows (CRUD do builder), inbox/live chat (WebSocket), analytics
