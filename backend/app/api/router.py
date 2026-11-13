from fastapi import APIRouter

from app.api.routes.analytics import router as analytics_router
from app.api.routes.citizen_content import router as citizen_content_router
from app.api.routes.health import router as health_router
from app.api.routes.legislation import router as legislation_router
from app.api.routes.parliamentarians import router as parliamentarians_router

router = APIRouter()
router.include_router(health_router)
router.include_router(parliamentarians_router)
router.include_router(legislation_router)

router.include_router(analytics_router)
router.include_router(citizen_content_router)
