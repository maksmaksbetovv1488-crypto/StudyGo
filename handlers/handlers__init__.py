from aiogram import Router
from handlers.admin import router as admin_router
from handlers.start import router as start_router
from handlers.shop import router as shop_router
from handlers.social import router as social_router
from handlers.ai import router as ai_router


def setup_routers() -> Router:
    root = Router()
    root.include_router(admin_router)
    root.include_router(start_router)
    root.include_router(shop_router)
    root.include_router(social_router)
    root.include_router(ai_router)
    return root
