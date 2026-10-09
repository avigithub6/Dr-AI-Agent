from fastapi import APIRouter, Depends

from app.api.auth import router as auth_router
from app.api.chat import router as chat_router
from app.api.conversation import router as conversation_router
from app.api.health import router as health_router
from app.api.knowledge import router as knowledge_router
from app.api.patient import router as patient_router
from app.api.voice import router as voice_router
from app.core.security import require_roles


api_router = APIRouter()

# Health endpoint remains public.
api_router.include_router(health_router)

# Login and one-time bootstrap routes are public.
# /auth/me and /auth/users enforce their own authorization.
api_router.include_router(auth_router)

# Only authenticated clinical staff can use these routes.
clinical_access = Depends(require_roles("admin", "clinician"))

api_router.include_router(
    chat_router,
    dependencies=[clinical_access],
)
api_router.include_router(
    conversation_router,
    dependencies=[clinical_access],
)
api_router.include_router(
    patient_router,
    dependencies=[clinical_access],
)
api_router.include_router(
    voice_router,
    dependencies=[clinical_access],
)

# Knowledge administration is limited to admins.
api_router.include_router(
    knowledge_router,
    dependencies=[Depends(require_roles("admin"))],
)